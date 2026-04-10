# Cerno - SRE Incident Intake & Triage Agent

Cerno (Latin for "I sift, I separate, I decide") is an AI-powered SRE Incident Intake & Triage Agent built for a 24-hour hackathon. It automates the ingestion, analysis, and initial triage of incident reports.

## Architecture

*   **Frontend:** Next.js (guided wizard form)
*   **Backend:** FastAPI (Python 3.9+)
*   **Bot:** Telegram Bot for alternative intake
*   **State Management:** Redis
*   **Vector Database:** Qdrant
*   **Database:** Postgres (for relational data)
*   **Observability:** Langfuse
*   **AI Stack:** OpenRouter + Instructor + LangGraph

## Agent Architecture
Cerno uses a sequential LangGraph agent pipeline:
1.  **CodeAnalyst:** Analyzes code contexts using a pre-chunked RAG database of the target codebase (Reaction Commerce).
2.  **LogParser:** Extracts structured data and anomalies from attached logs.
3.  **SeverityScorer:** Evaluates the incident to assign a severity level (P1-P5).

## Setup
Please refer to \`QUICKGUIDE.md\` for rapid deployment instructions.
