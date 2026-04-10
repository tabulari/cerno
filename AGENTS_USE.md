# Agent Behaviors & Safety (AGENTS_USE.md)

## Agent Pipeline Overview
The Cerno system uses a LangGraph-orchestrated sequence of sub-agents to process incidents:

1. **Intake / Guardrails Layer:**
   - All user inputs are scanned using **LLM-Guard** for prompt injections, toxicity, and PII before reaching the core agents. (NeMo Guardrails is a stretch goal).

2. **CodeAnalyst Agent:**
   - **Role:** Queries the Qdrant vector database (indexed with Reaction Commerce codebase) to find relevant code snippets related to the incident.
   - **Safety:** Read-only access to the indexed RAG data.

3. **LogParser Agent:**
   - **Role:** Analyzes text logs or error traces to find stack traces, exception messages, and affected services.
   - **Safety:** Strictly limited to parsing tasks. Does not execute code.

4. **SeverityScorer Agent:**
   - **Role:** Synthesizes the outputs from CodeAnalyst and LogParser along with the user report to assign a final severity score and suggest a runbook.

## Safety Measures
- **MOCK_MODE:** Configurable fallback to mocked data and LLM responses to ensure the demo functions even if external APIs fail.
- **Data Sanitization:** PII filtering is applied before sending logs to OpenRouter models.
- **Rate Limiting:** Managed via FastAPI and Redis to prevent abuse.
