# Quick Start Guide (QUICKGUIDE.md)

Follow these steps to get Cerno running locally.

## Prerequisites

- Docker and Docker Compose
- Node.js
- Python 3.12+
- `uv`

## 1. Environment Setup

Copy the example environment file and fill in your keys:
\`\`\`bash
cp .env.example .env

# Edit .env with your OpenRouter API key, Telegram Bot token, etc.

\`\`\`

## 2. Start Services

Run the entire stack using Docker Compose:
\`\`\`bash
docker compose up --build -d
\`\`\`

This will start:

- Frontend (Port 3000)
- Backend (Port 8000)
- Redis (Port 6379)
- Qdrant (Port 6333)
- Postgres (Port 5432)
- Langfuse (Port 3000)

## 3. Verify Setup

- Web UI: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Langfuse: http://localhost:3000 (Make sure to check port mappings if running locally)

## 4. Run Mocks (Optional)

If you don't have API keys, ensure \`MOCK_MODE=true\` in your \`.env\` file.
