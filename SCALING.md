# System Scaling & Architecture Decisions

This document outlines how the Cerno architecture scales to handle extreme burst traffic (e.g., 1000+ concurrent incidents during a major system outage), along with the performance assumptions and technical trade-offs made during the system's design.

---

## 1. Executive Summary

Major outages trigger "incident storms" where hundreds of users report the same underlying issue simultaneously. Cerno is designed around a **decoupled, asynchronous architecture**. The ingestion layer is built to absorb massive bursts and respond in milliseconds, while the heavy LLM triage pipeline processes reports asynchronously from a queue, protecting the system from rate limits and timeouts.

---

## 2. Component-Level Scaling Strategies

### 2.1 Intake Layer

- **Next.js Frontend:** Designed to be deployed on serverless edge infrastructure (e.g., Vercel or AWS Amplify), providing infinite horizontal scalability for the web UI.
- **Telegram Bot:** The current hackathon implementation uses long-polling for simplicity. In production, this transitions to **Telegram Webhooks** sitting behind an API Gateway/Load Balancer, allowing horizontal scaling of bot worker nodes.

### 2.2 API & Security Layer

- **FastAPI Backend:** Horizontally scalable via Kubernetes or ECS. Gunicorn/Uvicorn workers can handle thousands of concurrent connections using `asyncio`.
- **Compute-Bound Security:** The Security Layer (Layer 2 & 3) runs CPU-heavy local tasks (Presidio PII redaction, local LLM-Guard scanners). These specific nodes require compute-optimized instances and horizontal scaling to prevent ingest backpressure.

### 2.3 Data & State Layer

- **Redis (State Machine & Queue):** Handles high-throughput state transitions (`SUBMITTED -> TRIAGING`), rate limiting, and Pub/Sub for SSE. Scales via **Redis Cluster** to shard the queue and state keys across multiple nodes.
- **PostgreSQL:** The primary relational store. To prevent horizontally scaled FastAPI workers from exhausting database connections, **PgBouncer** (or AWS RDS Proxy) connection pooling is mandatory in production.
- **Qdrant (Vector DB):** Supports distributed deployment with Raft-based replication. Read replicas can scale horizontally to handle high volumes of concurrent RAG queries from the `CodeAnalyst` agent.

---

## 3. Mitigating the LLM Bottleneck (1000+ Concurrent Incidents)

Even with infinite infrastructure, 1000+ concurrent incidents will immediately hit the Token-Per-Minute (TPM) or Request-Per-Minute (RPM) limits of any external LLM provider. Cerno mitigates this through four specific strategies:

### 3.1 Asynchronous Processing (Fast Ingest, Slow Triage)

When an incident is submitted, FastAPI writes the raw payload to Postgres, pushes the ID to Redis, updates the state to `SUBMITTED`, and returns a `202 Accepted` to the client in **< 100ms**. The client subscribes to SSE updates. Background workers pull from Redis to execute the 10-20 second LangGraph pipeline, ensuring the UI never blocks.

### 3.2 Semantic Deduplication (The "Storm Shield")

Before querying the LLM pipeline, the system embeds the incident description and queries Qdrant against incidents reported in the last 60 minutes.

- **Trade-off:** We incur a ~50ms latency penalty on every ingest to generate the embedding and search.
- **Benefit:** If a 95%+ semantic match is found (e.g., 500 users reporting "checkout is 500ing"), Cerno instantly links the new report to the existing parent ticket. This skips the LangGraph pipeline entirely, saving ~15 seconds and thousands of LLM tokens per duplicate.

### 3.3 Automated Provider Fallbacks

Cerno uses OpenRouter as a unified API gateway. If Gemini 2.5 Flash hits a `429 Too Many Requests` error, OpenRouter automatically falls back to secondary models (e.g., Claude 3.5 Haiku → GPT-4o-mini) transparently, ensuring the pipeline continues processing the queue without manual intervention.

### 3.4 Degraded Triage Mode (Pipeline Fallback)

If the multi-agent LangGraph pipeline fails entirely (due to extreme timeouts or consecutive malformed outputs), the system degrades to a single, zero-shot `instructor.from_openai()` call. This fallback guarantees a structured `TriageResult` is generated, prioritizing system availability over depth of analysis.

---

## 4. Key Performance Assumptions & Technical Decisions

### 4.1 Architectural Assumptions

| #   | Assumption                                                                                                                                     | Implication if Wrong                                                                                                                                  |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| A   | **Fast ingest, slow triage.** Users tolerate 10-20s for a triage result as long as they get immediate acknowledgement (<100ms `202 Accepted`). | If users expect synchronous results, the entire async queue architecture must be replaced with streaming partial results.                             |
| B   | **Single-tenant deployment.** One organization owns the entire stack.                                                                          | Multi-tenant SaaS would require Postgres Row-Level Security (RLS), Qdrant payload partitioning by `tenant_id`, and per-tenant rate limiting in Redis. |
| C   | **Codebase embeddings are immutable between deployments.** The pre-chunked `chunks.json` does not change at runtime.                           | If the target codebase changes frequently, a CI/CD pipeline must regenerate `chunks.json` and trigger an indexer re-run on each deploy.               |
| D   | **Observability overhead is acceptable.** Langfuse tracing + structlog JSON logging add ~5-10ms latency per request.                           | If sub-millisecond ingest is required, tracing must move to async export (OpenTelemetry Collector) and log writes must be buffered.                   |
| E   | **Incident storms are bursty, not sustained.** 1000+ incidents arrive in a 5-10 minute window, then taper off.                                 | If sustained high throughput is needed (e.g., continuous monitoring), the Redis queue requires dedicated consumer scaling and backpressure signaling. |

### 4.2 Scaling-Critical Technical Decisions

| #   | Decision                                                                                     | Alternative Considered                        | Why This Scales Better                                                                                                                                                                                                                         |
| --- | -------------------------------------------------------------------------------------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A   | **OpenRouter as LLM gateway** over direct Gemini SDK                                         | Direct API calls to each provider             | Enables automatic fallback chain (Flash -> Pro -> Haiku -> GPT-4o-mini) under rate limiting without code changes. Unified TPM/RPM management across providers.                                                                                 |
| B   | **Redis state machine** over Postgres status columns                                         | `UPDATE incidents SET status = 'TRIAGING'`    | Redis handles 100k+ ops/sec for state transitions vs. Postgres row-level locks. Pub/Sub enables real-time SSE without polling. Rate limiting co-located with state management.                                                                 |
| C   | **Pre-chunked offline RAG** over runtime indexing                                            | Clone repo and embed on boot                  | Init container loads pre-embedded `chunks.json` into Qdrant in seconds (with named volume for instant restarts on subsequent boots). Runtime indexing would add 3-5 min cold start per container, breaking auto-scaling.                       |
| D   | **Semantic dedup before LLM** (50ms penalty per ingest)                                      | Skip dedup, triage every incident             | During incident storms, 90%+ of reports describe the same issue. The 50ms embedding + Qdrant search saves ~15s and thousands of tokens per duplicate by linking to the parent ticket instead of running the pipeline.                          |
| E   | **Rate limiting as backpressure control** (30 req/min per IP, 5 submissions/hr per reporter) | No rate limiting, rely on LLM provider limits | Prevents a single reporter from flooding the queue. Without this, one automated script could exhaust the entire LLM budget in minutes.                                                                                                         |
| F   | **MOCK_MODE Protocol interfaces** for all external I/O                                       | Real integrations only                        | Allows load-testing the Redis state machine and Postgres ingestion at 10k+ RPS without LLM API costs. Every integration (OpenRouter, Linear, Slack, SendGrid) implements a `Protocol` with real and mock backends toggled by a single env var. |
| G   | **Qdrant named volumes** for persistent vector storage                                       | Ephemeral volumes, re-index on every boot     | Prevents the 3-5 minute re-embedding cold start on container restarts. Auto-scaling nodes can start serving RAG queries immediately by mounting the existing volume.                                                                           |
