import structlog
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.auth import get_current_user
from app.models.database import User, Incident
from app.models.schemas import (
    IncidentCreate, IncidentResponse, IncidentState, Severity,
)
from app.services.state_machine import StateMachine
from app.services.triage import trigger_triage

logger = structlog.get_logger()
router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("/", response_model=IncidentResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_incident(
    payload: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    incident = Incident(
        title=payload.title,
        description=payload.description,
        service=payload.service,
        reporter_id=user.id,
        reporter_severity=payload.reporter_severity,
        state=IncidentState.SUBMITTED,
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
    user: User = Depends(get_current_user),
):
    query = select(Incident).order_by(Incident.created_at.desc()).limit(limit).offset(offset)
    if state:
        query = query.where(Incident.state == state)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident
