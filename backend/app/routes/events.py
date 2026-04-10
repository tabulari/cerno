import asyncio
import json
import structlog
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.redis import get_redis
from app.models.schemas import StateTransition
from app.services.state_machine import StateMachine

logger = structlog.get_logger()
router = APIRouter(prefix="/incidents", tags=["events"])


@router.get("/{incident_id}/transitions", response_model=list[StateTransition])
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
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    await asyncio.sleep(2)
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
