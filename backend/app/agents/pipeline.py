import asyncio
import structlog
from typing import TypedDict

from langgraph.graph import StateGraph, END
from app.db import get_session_factory
from app.models.database import Incident, Ticket
from app.models.schemas import IncidentState, TriageResult
from app.services.state_machine import StateMachine
from app.services.integrations import get_ticketing, get_notification
from app.security.llm_guard import scan_input, scan_llm_output
from app.security.presidio import redact_pii
from app.agents.nodes import (
    code_analyst_node,
    log_parser_node,
    severity_scorer_node,
    instructor_fallback
)

logger = structlog.get_logger()

class TriageState(TypedDict):
    incident_id: int
    description: str
    service: str
    retry_count: int
    code_analysis: dict | None
    log_analysis: dict | None
    reasoning_steps: list[dict]
    triage_result: TriageResult | None

def should_retry(state: TriageState):
    result = state.get("triage_result")
    if result and result.confidence >= 0.7:
        return "end"
    if state.get("retry_count", 0) >= 1:
        return "end"
    return "retry"

def increment_retry(state: TriageState):
    return {**state, "retry_count": state.get("retry_count", 0) + 1}

async def run_pipeline(incident_id: int) -> None:
    logger.info("pipeline.start", incident_id=incident_id, mode="langgraph")
    sm = await StateMachine.create(incident_id)

    factory = get_session_factory()
    async with factory() as db:
        from sqlalchemy import select
        row = await db.execute(select(Incident).where(Incident.id == incident_id))
        incident = row.scalar_one()
        
        # Apply Security Layer 2 & 3 before pipeline execution
        try:
            safe_description = scan_input(incident.description)
            description = redact_pii(safe_description)
            logger.info("pipeline.security.passed", incident_id=incident_id)
        except Exception as e:
            logger.warning("pipeline.security.blocked", incident_id=incident_id, error=str(e))
            # Fallback to redact only if LLM Guard fails or blocks
            description = redact_pii(incident.description)

        service = incident.service

    await sm.transition(IncidentState.SUBMITTED, IncidentState.TRIAGING, {"agent": "langgraph"})

    workflow = StateGraph(TriageState)
    workflow.add_node("code_analyst", code_analyst_node)
    workflow.add_node("log_parser", log_parser_node)
    workflow.add_node("severity_scorer", severity_scorer_node)
    workflow.add_node("retry_node", increment_retry)

    workflow.set_entry_point("code_analyst")
    workflow.add_edge("code_analyst", "log_parser")
    workflow.add_edge("log_parser", "severity_scorer")
    
    workflow.add_conditional_edges(
        "severity_scorer",
        should_retry,
        {
            "end": END,
            "retry": "retry_node"
        }
    )
    workflow.add_edge("retry_node", "severity_scorer")

    app = workflow.compile()

    state = {
        "incident_id": incident_id,
        "description": description,
        "service": service,
        "retry_count": 0,
        "reasoning_steps": [],
    }

    try:
        final_state = await app.ainvoke(state)
        result = final_state.get("triage_result")
        if not result:
            raise ValueError("Pipeline completed without generating TriageResult")
    except Exception as e:
        logger.exception("pipeline.error", error=str(e), incident_id=incident_id)
        result = await instructor_fallback(incident_id, description, service)

    await sm.transition(IncidentState.TRIAGING, IncidentState.TRIAGED, {"severity": result.severity.value})

    async with factory() as db:
        row = await db.execute(select(Incident).where(Incident.id == incident_id))
        incident = row.scalar_one()
        incident.triage_severity = result.severity
        incident.triage_summary = result.summary
        incident.triage_runbook = result.runbook
        incident.confidence = result.confidence
        incident.needs_human_review = result.needs_human_review
        incident.state = IncidentState.TRIAGED
        incident.reasoning_steps = [s.model_dump() for s in result.reasoning_steps]
        if result.code_analysis:
            incident.evidence_paths = result.code_analysis.relevant_files
        await db.commit()

    ticketing = get_ticketing()
    ticket_data = await ticketing.create_ticket(incident_id, result)

    async with factory() as db:
        ticket = Ticket(
            incident_id=incident_id,
            external_id=ticket_data["external_id"],
            external_url=ticket_data["external_url"],
            provider=ticket_data["provider"],
        )
        db.add(ticket)
        row = await db.execute(select(Incident).where(Incident.id == incident_id))
        incident = row.scalar_one()
        incident.state = IncidentState.TICKETED
        await db.commit()

    await sm.transition(IncidentState.TRIAGED, IncidentState.TICKETED, ticket_data)

    notification = get_notification()
    await notification.notify(incident_id, result, "sse")

    async with factory() as db:
        row = await db.execute(select(Incident).where(Incident.id == incident_id))
        incident = row.scalar_one()
        incident.state = IncidentState.NOTIFIED
        await db.commit()

    await sm.transition(IncidentState.TICKETED, IncidentState.NOTIFIED, {"channel": "sse"})

    logger.info("pipeline.complete", incident_id=incident_id, severity=result.severity.value)
