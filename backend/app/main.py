from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.logging import setup_logging
from app.redis import close_redis
from app.routes import health, auth, incidents, events
from app.security.middleware import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = structlog.get_logger()
    settings = get_settings()

    logger.info("startup", mock_mode=settings.mock_mode, environment=settings.environment)
    await init_db()
    logger.info("database.initialized")

    yield

    await close_redis()
    logger.info("shutdown")


app = FastAPI(
    title="Cerno — SRE Triage Agent API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")

