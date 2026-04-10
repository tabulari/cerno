"""LangGraph node functions — CodeAnalyst, LogParser, SeverityScorer, Synthesizer."""
import time
import structlog

from app.config import get_settings
from app.models.schemas import (
    CodeAnalysisResult, LogParseResult, TriageResult,
    ReasoningStep, Severity,
)
from app.agents.llm_client import get_openai_client, get_instructor_client
from app.agents.rag import search_codebase

logger = structlog.get_logger()


async def code_analyst_node(state: dict) -> dict:
    start = time.monotonic()
    settings = get_settings()
    description = state["description"]
    service = state.get("service", "")

    module_filter = service if service and service != "unknown" else None
    chunks = search_codebase(description, top_k=5, module_filter=module_filter)

    if not chunks:
        chunks = search_codebase(description, top_k=5)

    rag_context = "\n\n".join(
        f"--- {c['file_path']} (module: {c['module']}, score: {c['score']:.2f}) ---\n{c['content']}"
        for c in chunks
    )

    client = get_openai_client()
    response = await client.chat.completions.create(
        model=settings.openrouter_model_fast,
        messages=[
            {"role": "system", "content": (
                "You are CodeAnalyst, an SRE agent. Given an incident description and relevant codebase "
                "snippets, identify which files and modules are most likely related to the incident. "
                "Be concise and specific. If no code is relevant, say so."
            )},
            {"role": "user", "content": (
                f"Incident: {description}\n\nRelevant codebase context:\n{rag_context}"
            )},
        ],
        max_tokens=1000,
    )

    analysis_text = response.choices[0].message.content or ""
    elapsed = int((time.monotonic() - start) * 1000)

    result = CodeAnalysisResult(
        relevant_files=[c["file_path"] for c in chunks],
        code_snippets=[c["content"][:300] for c in chunks[:3]],
        module=chunks[0]["module"] if chunks else None,
        summary=analysis_text,
    )

    step = ReasoningStep(
        agent="CodeAnalyst",
        duration_ms=elapsed,
        tool_calls=[{"name": "qdrant_search", "input": description[:80], "output": f"{len(chunks)} chunks"}],
        finding=analysis_text[:300],
    )

    logger.info("agent.code_analyst.done", duration_ms=elapsed, files_found=len(chunks))
    return {**state, "code_analysis": result, "reasoning_steps": state.get("reasoning_steps", []) + [step]}


async def log_parser_node(state: dict) -> dict:
    start = time.monotonic()
    settings = get_settings()
    description = state["description"]

    client = get_instructor_client()

    result = await client.chat.completions.create(
        model=settings.openrouter_model_fast,
        response_model=LogParseResult,
        messages=[
            {"role": "system", "content": (
                "You are LogParser, an SRE agent that extracts structured error data from incident "
                "descriptions and logs. Extract error types, affected services, stack traces, and anomalies. "
                "If the input contains no log data, infer what you can from the description."
            )},
            {"role": "user", "content": f"Incident description:\n{description}"},
        ],
        max_tokens=1000,
    )

    elapsed = int((time.monotonic() - start) * 1000)

    step = ReasoningStep(
        agent="LogParser",
        duration_ms=elapsed,
        tool_calls=[{"name": "instructor_extract", "input": "incident_text", "output": "structured_errors"}],
        finding=result.summary[:300] if result.summary else f"Extracted {len(result.error_types)} error types",
    )

    logger.info("agent.log_parser.done", duration_ms=elapsed, errors=len(result.error_types))
    return {**state, "log_analysis": result, "reasoning_steps": state.get("reasoning_steps", []) + [step]}


async def severity_scorer_node(state: dict) -> dict:
    start = time.monotonic()
    settings = get_settings()

    code_analysis: CodeAnalysisResult = state.get("code_analysis", CodeAnalysisResult())
    log_analysis: LogParseResult = state.get("log_analysis", LogParseResult())
    description = state["description"]

    context = (
        f"Original incident report:\n{description}\n\n"
        f"Code analysis:\n{code_analysis.summary}\n"
        f"Relevant files: {', '.join(code_analysis.relevant_files)}\n\n"
        f"Log analysis:\n{log_analysis.summary}\n"
        f"Error types: {', '.join(log_analysis.error_types)}\n"
        f"Affected services: {', '.join(log_analysis.affected_services)}\n"
        f"Anomalies: {', '.join(log_analysis.anomalies)}"
    )

    client = get_instructor_client()

    result = await client.chat.completions.create(
        model=settings.openrouter_model_strong,
        response_model=TriageResult,
        messages=[
            {"role": "system", "content": (
                "You are SeverityScorer, a senior SRE agent. Given an incident report with code analysis "
                "and log analysis from other agents, produce a final triage assessment.\n\n"
                "Rules:\n"
                "- Assign severity P1 (critical outage) through P5 (cosmetic/minor)\n"
                "- P1: Complete service down, data loss risk\n"
                "- P2: Major degradation, many users affected\n"
                "- P3: Partial impact, workaround exists\n"
                "- P4: Minor issue, low user impact\n"
                "- P5: Cosmetic, no functional impact\n"
                "- Cite specific file paths from the code analysis when relevant\n"
                "- If no codebase correlation exists, state 'No direct codebase correlation found'\n"
                "- Provide a concrete, actionable runbook with numbered steps\n"
                "- Set confidence between 0.0 and 1.0\n"
                "- Set needs_human_review=true if confidence < 0.7"
            )},
            {"role": "user", "content": context},
        ],
        max_tokens=2000,
    )

    elapsed = int((time.monotonic() - start) * 1000)

    result.code_analysis = code_analysis
    result.log_analysis = log_analysis
    result.reasoning_steps = state.get("reasoning_steps", []) + [
        ReasoningStep(
            agent="SeverityScorer",
            duration_ms=elapsed,
            tool_calls=[{"name": "instructor_score", "input": "combined_context", "output": result.severity.value}],
            finding=f"{result.severity.value}: {result.summary[:200]}",
        )
    ]

    if result.confidence < 0.7:
        result.needs_human_review = True

    logger.info(
        "agent.severity_scorer.done",
        duration_ms=elapsed,
        severity=result.severity.value,
        confidence=result.confidence,
    )
    return {**state, "triage_result": result}


async def instructor_fallback(incident_id: int, description: str, service: str) -> TriageResult:
    """Single-call fallback if LangGraph pipeline fails entirely."""
    start = time.monotonic()
    settings = get_settings()
    client = get_instructor_client()

    logger.warning("pipeline.fallback", incident_id=incident_id)

    result = await client.chat.completions.create(
        model=settings.openrouter_model_fast,
        response_model=TriageResult,
        messages=[
            {"role": "system", "content": (
                "You are Cerno, an SRE triage agent. Analyze this incident and produce a triage result "
                "with severity (P1-P5), summary, runbook, and confidence score. "
                "This is a fallback path — be concise but thorough."
            )},
            {"role": "user", "content": f"Service: {service}\nIncident: {description}"},
        ],
        max_tokens=1500,
    )

    elapsed = int((time.monotonic() - start) * 1000)
    result.reasoning_steps = [
        ReasoningStep(
            agent="InstructorFallback",
            duration_ms=elapsed,
            tool_calls=[{"name": "instructor_direct", "input": "incident", "output": result.severity.value}],
            finding=f"Fallback triage: {result.summary[:200]}",
        )
    ]

    if result.confidence < 0.7:
        result.needs_human_review = True

    return result
