import asyncio
import structlog

from app.db import get_session_factory
from app.models.database import Incident, Ticket
from app.models.schemas import (
    IncidentState, Severity, TriageResult,
    CodeAnalysisResult, LogParseResult, ReasoningStep,
)
from app.services.state_machine import StateMachine
from app.services.integrations import get_ticketing, get_notification

logger = structlog.get_logger()


async def run_mock_pipeline(incident_id: int) -> None:
    sm = await StateMachine.create(incident_id)

    await sm.transition(IncidentState.SUBMITTED, IncidentState.TRIAGING, {"agent": "mock"})
    await asyncio.sleep(1.5)

    result = TriageResult(
        severity=Severity.P2,
        summary="Mock triage: Potential service degradation detected in checkout flow. "
                "Error patterns suggest a database connection timeout under load.",
        runbook="1. Check database connection pool utilization\n"
                "2. Review recent deployments to checkout service\n"
                "3. Monitor error rates for the next 15 minutes\n"
                "4. If persists, scale up database read replicas",
        confidence=0.85,
        needs_human_review=False,
        reasoning_steps=[
            ReasoningStep(
                agent="CodeAnalyst",
                duration_ms=450,
                tool_calls=[{"name": "qdrant_search", "input": "checkout error", "output": "3 files found"}],
                finding="Found relevant code in checkout/cart.js and db/pool.js",
            ),
            ReasoningStep(
                agent="LogParser",
                duration_ms=320,
                tool_calls=[{"name": "instructor_extract", "input": "log_text", "output": "structured"}],
                finding="Detected ETIMEDOUT errors with database connection strings",
            ),
            ReasoningStep(
                agent="SeverityScorer",
                duration_ms=600,
                tool_calls=[{"name": "instructor_score", "input": "combined_context", "output": "P2"}],
                finding="P2: Service degradation affecting checkout, not full outage",
            ),
        ],
        code_analysis=CodeAnalysisResult(
            relevant_files=["src/checkout/cart.js", "src/db/pool.js"],
            code_snippets=["const pool = new Pool({ max: 10, connectionTimeoutMillis: 3000 })"],
            module="checkout",
            summary="Database pool configuration may be undersized for current load",
        ),
        log_analysis=LogParseResult(
            error_types=["ETIMEDOUT", "ConnectionError"],
            affected_services=["checkout-api", "postgres"],
            stack_traces=["Error: connect ETIMEDOUT at Pool.connect (db/pool.js:42)"],
            anomalies=["Connection pool exhaustion spike at 14:32 UTC"],
            summary="Database connection timeouts correlating with traffic spike",
        ),
    )

    await sm.transition(IncidentState.TRIAGING, IncidentState.TRIAGED, {"severity": result.severity.value})

    factory = get_session_factory()
    async with factory() as db:
        from sqlalchemy import select
        row = await db.execute(select(Incident).where(Incident.id == incident_id))
        incident = row.scalar_one()
        incident.triage_severity = result.severity
        incident.triage_summary = result.summary
        incident.triage_runbook = result.runbook
        incident.confidence = result.confidence
        incident.needs_human_review = result.needs_human_review
        incident.state = IncidentState.TRIAGED
        incident.reasoning_steps = [s.model_dump() for s in result.reasoning_steps]
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

    logger.info("mock.pipeline.complete", incident_id=incident_id, severity=result.severity.value)
