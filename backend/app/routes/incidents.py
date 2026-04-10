import structlog
from datetime import datetime, timezone
from typing import Optional, List
import magic

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.database import User, Incident
from app.models.schemas import (
    IncidentCreate,
    IncidentResponse,
    IncidentState,
    Severity,
)
from app.services.state_machine import StateMachine
from app.services.triage import trigger_triage

logger = structlog.get_logger()
router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("/test")
async def test():
    return {"test": "works"}


ALLOWED_MIMES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "video/mp4",
    "video/webm",
    "text/plain",
    "application/json",
}


def validate_file(file: UploadFile):
    if file.filename.endswith(".svg"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="SVG files are not allowed"
        )

    # Read a chunk to guess mime type
    header = file.file.read(2048)
    file.file.seek(0)

    mime = magic.from_buffer(header, mime=True)
    if mime not in ALLOWED_MIMES:
        # Some plain text files might not be recognized properly, let's do a fallback extension check
        if not (
            file.filename.endswith(".log")
            or file.filename.endswith(".txt")
            or file.filename.endswith(".json")
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {mime} not allowed",
            )

    # Check file size (approximate by seeking to end)
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    is_video = mime.startswith("video/")
    max_size = 20 * 1024 * 1024 if is_video else 5 * 1024 * 1024
    if size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large (Max {max_size / (1024 * 1024)}MB)",
        )


@router.post("/", response_model=IncidentResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_incident(
    title: str = Form(..., min_length=5, max_length=200),
    description: str = Form(..., min_length=10, max_length=5000),
    service: str = Form("unknown", max_length=100),
    reporter_severity: Optional[Severity] = Form(None),
    evidence: List[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
):
    # Demo mode: always use guest user
    from sqlalchemy import select
    from app.auth import hash_password

    result = await db.execute(select(User).where(User.username == "guest"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(username="guest", hashed_password=hash_password("guest-demo"))
        db.add(user)
        await db.commit()
        await db.refresh(user)
    evidence_paths = []
    if evidence:
        for file in evidence:
            validate_file(file)
            # In a real app we'd save to S3/Disk and store the path
            evidence_paths.append(file.filename)

    incident = Incident(
        title=title,
        description=description,
        service=service,
        reporter_id=user.id,
        reporter_severity=reporter_severity,
        state=IncidentState.SUBMITTED,
        evidence_paths=evidence_paths,
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    logger.info("incident.created", incident_id=incident.id, reporter=user.username)

    state_machine = await StateMachine.create(incident.id)
    await state_machine.transition(IncidentState.SUBMITTED, IncidentState.SUBMITTED, {})

    await trigger_triage(incident.id)

    return incident


@router.get("/", response_model=list[IncidentResponse])
async def list_incidents(
    state: Optional[IncidentState] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Incident)
        .order_by(Incident.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if state:
        query = query.where(Incident.state == state)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found"
        )
    return incident


# ===== Events routes (merged to avoid prefix conflict) =====
import asyncio as _asyncio
from fastapi import Request
from fastapi.responses import StreamingResponse
from app.redis import get_redis


@router.get("/{incident_id}/transitions")
async def get_transitions(incident_id: int):
    sm = await StateMachine.create(incident_id)
    return await sm.get_transitions()


@router.get("/{incident_id}/events")
async def stream_events(incident_id: int, request: Request):
    async def event_generator():
        redis = await get_redis()
        pubsub = redis.pubsub()
        channel = f"incident:{incident_id}:events"
        await pubsub.subscribe(channel)

        try:
            while True:
                if await request.is_disconnected():
                    break
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "message":
                    yield f"data: {message['data']}\n\n"
                else:
                    import json

                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    await _asyncio.sleep(2)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
