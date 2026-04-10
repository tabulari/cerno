import asyncio
import structlog

from app.config import get_settings

logger = structlog.get_logger()


async def trigger_triage(incident_id: int) -> None:
    asyncio.create_task(_run_triage(incident_id))


async def _run_triage(incident_id: int) -> None:
    settings = get_settings()
    try:
        if settings.mock_mode:
            from app.agents.mock_pipeline import run_mock_pipeline
            await run_mock_pipeline(incident_id)
        else:
            from app.agents.pipeline import run_pipeline
            await run_pipeline(incident_id)
    except Exception:
        logger.exception("triage.failed", incident_id=incident_id)
        from app.services.state_machine import StateMachine
        from app.models.schemas import IncidentState
        sm = await StateMachine.create(incident_id)
        current = await sm.get_state()
        await sm.transition(current, IncidentState.FAILED, {"error": "pipeline_exception"})
