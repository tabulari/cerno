# Cerno - SRE Incident Intake & Triage Agent

## Project Summary

**Cerno** *(Latin: "I sift, I separate, I decide")* is an AI-powered SRE agent that automates the ingestion, analysis, and initial triage of incident reports. When an incident hits -- a checkout crash, a payments timeout, an error screenshot from a panicked on-call engineer -- Cerno takes the raw, messy signal and turns it into a structured, triaged, actionable ticket in seconds.

It accepts multimodal incident reports (free-text descriptions, error screenshots, log files) through two intake channels: a **guided web wizard** and a **Telegram bot**. A LangGraph pipeline of three specialized sub-agents analyzes the evidence, assigns a severity score (P1-P5), and suggests a runbook -- with every step of the agent's reasoning visible to the operator.

### Demo Mode

For demonstrations, auth is bypassed. A "guest" user is automatically created on first incident submission. No login or registration required:
- Open http://localhost:3000
- Click "Report Incident"
- Complete the wizard
- View the incident detail with timeline and reasoning accordion

### Use Cases

**Web Wizard Intake** -- An engineer uses the Next.js guided form to submit a structured incident report with attached server logs. The report passes through the security layers, the three-agent pipeline triages it, and the result appears on the dashboard with a severity score, summary, and suggested runbook.

**Telegram Bot Intake** -- A panicked on-call engineer drops a screenshot of an error page into the Telegram bot with "checkout is broken". The bot guides them through a structured flow (mirroring the web wizard), the LogParser extracts error text from the screenshot via vision models, and the bot replies with the triaged severity and a link to the web dashboard.

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            INTAKE LAYER                                         │
│                                                                                 │
│   ┌──────────────────┐              ┌──────────────────┐                        │
│   │   Next.js UI     │              │   Telegram Bot   │                        │
│   │   :3000          │              │   (long-poll)    │                        │
│   │                  │              │                  │                        │
│   │  Guided Wizard:  │              │  Guided Flow:    │                        │
│   │  text → location │              │  /start → text   │                        │
│   │  → evidence      │              │  → location      │                        │
│   │  → severity      │              │  → screenshot    │                        │
│   │  → review        │              │  → confirm       │                        │
│   └────────┬─────────┘              └────────┬─────────┘                        │
│            │           IncidentReport        │                                  │
│            └──────────────┬──────────────────┘                                  │
│                           ▼                                                     │
└───────────────────────────┼─────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────────────────────┐
│                        SECURITY LAYER                                           │
│                                                                                 │
│   ┌─────────────┐   ┌──────────────┐   ┌────────────┐   ┌─────────────┐         │
│   │  Layer 1:   │──►│   Layer 2:   │──►│  Layer 3:  │──►│   FastAPI   │         │
│   │  Static     │   │  LLM-Guard   │   │  Presidio  │   │  /api/v1/   │         │
│   │  Validation │   │  Input Scan  │   │  PII       │   │  + JWT Auth │         │
│   │             │   │              │   │  Redaction │   │             │         │
│   │ MIME check  │   │ Injection    │   │            │   │ Rate Limit  │         │
│   │ Size cap    │   │ Jailbreak    │   │ Emails     │   │ 30 req/min  │         │
│   │ SVG block   │   │ Toxicity     │   │ Phones     │   │ 5 sub/hr    │         │
│   └─────────────┘   └──────────────┘   └────────────┘   └──────┬──────┘         │
│                                                                 │               │
└─────────────────────────────────────────────────────────────────┼───────────────┘
                                                                  │
┌─────────────────────────────────────────────────────────────────▼───────────────┐
│                     AGENT PIPELINE (LangGraph StateGraph)                       │
│                                                                                 │
│   ┌───────────┐    ┌───────────────┐    ┌────────────┐    ┌────────────────┐    │
│   │           │    │               │    │            │    │                │    │
│   │   START   │───►│  CodeAnalyst  │───►│  LogParser │───►│ SeverityScorer │    │
│   │           │    │               │    │            │    │                │    │
│   └───────────┘    │  Gemini Flash │    │ Gemini     │    │  Gemini Pro    │    │
│                    │  + Qdrant RAG │    │ Flash      │    │  + Instructor  │    │
│                    │               │    │ Multimodal │    │                │    │
│                    │  Finds code   │    │ + Instruct │    │  P1-P5 score   │    │
│                    │  context      │    │            │    │  + runbook     │    │
│                    │  via semantic  │    │ Extracts  │    │  + confidence  │    │
│                    │  search       │    │ errors &   │    │                │    │
│                    │               │    │ anomalies  │    │                │    │
│                    └───────┬───────┘    └─────┬──────┘    └───────┬────────┘    │
│                            │                  │                   │             │
│                            ▼                  ▼                   ▼             │
│                    ┌─────────────────────────────────────────────────────┐      │
│                    │              Synthesizer + ConfidenceCheck          │      │
│                    │                                                     │      │
│                    │  confidence >= 0.7? ──Yes──► TriageResult (END)     │      │
│                    │        │                                            │      │
│                    │        No                                           │      │
│                    │        ▼                                            │      │
│                    │  Retry (max 1) ──────────► TriageResult (END)       │      │
│                    └─────────────────────────────────────────────────────┘      │
│                                                                                 │
│   ┌──────────────────────────────────────────────────────────────────────┐      │
│   │  FALLBACK: If pipeline fails → single instructor.from_openai()       │      │
│   │  call producing the same TriageResult Pydantic model                 │      │
│   └──────────────────────────────────────────────────────────────────────┘      │
│                                                                                 │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────────────┐
│                       OUTPUT & NOTIFICATION LAYER                               │
│                                                                                 │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                      │
│   │  LLM-Guard   │    │   Ticketing  │    │  Notify      │                      │
│   │  Output Scan │    │   (Linear)   │    │  Reporter    │                      │
│   │  Layer 4     │    │   real/mock  │    │  (SSE/TG)    │                      │
│   └──────┬───────┘    └──────────────┘    └──────────────┘                      │
│          │                                                                      │
└──────────┼──────────────────────────────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────────────────────────┐
│                        DATA & OBSERVABILITY LAYER                               │
│                                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────────────┐      │
│   │  Redis   │    │  Qdrant  │    │ Postgres │    │  Langfuse :3001      │      │
│   │  :6379   │    │  :6333   │    │  :5432   │    │  (self-hosted)       │      │
│   │          │    │          │    │          │    │                      │      │
│   │ State    │    │ Codebase │    │ Incidents│    │ LLM traces, prompts  │      │
│   │ machine  │    │ vectors  │    │ Users    │    │ tokens, latency      │      │
│   │ Pub/Sub  │    │ Incident │    │ Tickets  │    │ cost per triage      │      │
│   │ Rate     │    │ dedup    │    │ Langfuse │    │                      │      │
│   │ limits   │    │ vectors  │    │ data     │    │ + structlog JSON     │      │
│   └──────────┘    └──────────┘    └──────────┘    └──────────────────────┘      │
│                        ▲                                                        │
│                   ┌────┴─────┐                                                  │
│                   │  Indexer │  (init container, runs once on first boot)       │
│                   │  chunks  │  all-MiniLM-L6-v2 embeddings (384d)              │
│                   │  .json   │  Reaction Commerce → Qdrant                      │
│                   └──────────┘                                                  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Incident State Machine (Redis):**
```
SUBMITTED ──► TRIAGING ──► TRIAGED ──► TICKETED ──► NOTIFIED ──► RESOLVED
                 │
                 └──► FAILED (retry metadata)
```

### Agent Pipeline

Cerno uses a sequential supervisor pattern implemented via LangGraph's `StateGraph`. Each agent enriches a shared state dictionary before passing it to the next node.

**CodeAnalyst** -- Queries the Qdrant vector database to find relevant codebase context via semantic search over the Reaction Commerce codebase. Uses `all-MiniLM-L6-v2` embeddings (384 dims) with `top-k=5` retrieval.
LLM: Gemini 2.5 Flash | Tool: Qdrant Vector Search

**LogParser** -- Extracts structured data, stack traces, and key anomalies from unstructured logs or error screenshots. Supports multimodal input (text logs + images).
LLM: Gemini 2.5 Flash (Multimodal) | Tool: Instructor (Pydantic JSON extraction)

**SeverityScorer** -- Synthesizes all gathered context to assign a final severity score (P1-P5), generate an incident summary, and suggest an actionable runbook.
LLM: Gemini 2.5 Pro | Tool: Instructor (Pydantic JSON output)

**Fallback** -- If the pipeline fails or confidence < 0.7 after retry, the system degrades to a single `instructor.from_openai()` call producing the same `TriageResult` Pydantic model.

### Security & Guardrails

Six-layer defense-in-depth strategy:

| Layer | Component | Purpose |
|---|---|---|
| 1 | Static Validation | MIME check, file size caps (5MB images, 20MB video), SVG blocking, filename sanitization, Redis rate limiting (30 req/min, 5 submissions/hr) |
| 2 | LLM-Guard Input | Prompt injection, jailbreak, toxicity, and invisible character detection |
| 3 | Presidio PII Redaction | Auto-redacts emails, phone numbers, SSNs, credit cards before LLM processing |
| 4 | LLM-Guard Output | Sensitive data leak detection and response relevance validation |
| 5 | Frontend Sanitization | DOMPurify on triage_summary, triage_runbook, and reasoning steps; CSP headers |
| 6 | Infrastructure | (Demo: auth bypassed) JWT auth (HS256), secrets via Docker env vars, `uv audit` in build, agent has read-only access |

> **Demo Mode Note:** For demonstrations, authentication is bypassed and a guest user is auto-created. Set `MOCK_MODE=true` to run without external API keys.

### Observability

| Channel | Details |
|---|---|
| **Logging** | `structlog` JSON-formatted logs from every layer, queryable via `docker compose logs backend` |
| **Tracing** | Self-hosted Langfuse v3 captures every LangGraph node, prompt, tool call, and token count as traces and spans |
| **Metrics** | Langfuse tracks latency per sub-agent, tokens per triage, cost per incident. Redis state machine records transition durations for the SSE timeline |
| **Dashboards** | Langfuse (`localhost:3001`) for LLM observability, Next.js (`localhost:3000/dashboard`) for incident tracking, FastAPI Swagger (`localhost:8000/docs`) for API exploration |

## Setup Instructions

### Prerequisites
- Docker and Docker Compose
- Node.js
- Python 3.12+
- `uv`

### 1. Environment Setup
```bash
cp .env.example .env
# Edit .env with your OpenRouter API key, Telegram Bot token, etc.
```

### 2. Start Services
```bash
docker compose up --build -d
```

This starts 7 services:

| Service | Port |
|---|---|
| Frontend (Next.js) | 3000 |
| Backend (FastAPI) | 8000 |
| Redis | 6379 |
| Qdrant | 6333 |
| PostgreSQL | 5432 |
| Langfuse | 3001 |
| Telegram Bot | -- |

The Qdrant indexer runs as an init container on first boot, embedding the pre-chunked `chunks.json` into the vector database (~3-5 min). Subsequent restarts are instant via a named Qdrant volume.

### 3. Verify
- **Web UI:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs
- **Langfuse:** http://localhost:3001

### 4. Mock Mode
Set `MOCK_MODE=true` in `.env` to run without API keys. Every external integration (OpenRouter, Linear, Slack, SendGrid) implements a Protocol interface with both real and mock implementations.

## License

See [LICENSE](LICENSE).
