import structlog

logger = structlog.get_logger()


async def run_pipeline(incident_id: int) -> None:
    """Real LangGraph pipeline — delegates to mock for now, will be implemented with LangGraph StateGraph."""
    logger.info("pipeline.start", incident_id=incident_id, mode="langgraph")
    from app.agents.mock_pipeline import run_mock_pipeline
    await run_mock_pipeline(incident_id)
