# System Scaling (SCALING.md)

This document outlines how the Cerno architecture scales to handle 1000+ concurrent incidents.

## 1. Horizontal Scaling
- **FastAPI Backend:** Can be scaled horizontally using tools like Kubernetes or Docker Swarm. Gunicorn/Uvicorn workers can handle multiple concurrent connections.
- **Next.js Frontend:** Can be deployed to Vercel or horizontally scaled behind a CDN/Load Balancer.
- **Telegram Bot:** Can use webhooks instead of polling to scale horizontally behind a load balancer.

## 2. LLM Bottleneck Mitigation
Handling 1000+ concurrent incidents will hit rate limits with any LLM provider.
- **Asynchronous Processing:** Incidents are pushed to a Redis queue. Background workers process the queue asynchronously.
- **LLM Caching:** Common or duplicate incidents can be caught by querying the Qdrant database for semantic similarity before hitting the LLM (Comparative Triage).
- **Fallback Models:** OpenRouter enables automatic fallbacks to secondary models if the primary model rate-limits.

## 3. Database & State
- **Redis:** Handles high-throughput state transitions and queuing. Can be clustered.
- **Postgres:** Connection pooling (e.g., PgBouncer) prevents connection exhaustion from FastAPI workers.
- **Qdrant:** Supports distributed deployment for high-availability vector search.
