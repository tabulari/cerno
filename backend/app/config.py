from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM
    openrouter_api_key: str = ""
    openrouter_model_fast: str = "google/gemini-2.5-flash"
    openrouter_model_strong: str = "google/gemini-2.5-pro"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/cerno"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_codebase_collection: str = "codebase"
    qdrant_incidents_collection: str = "incidents"

    # JWT
    jwt_secret: str = "CHANGE_ME_TO_A_RANDOM_STRING"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # Rate Limiting
    rate_limit_rpm: int = 30
    rate_limit_submissions_per_hour: int = 5

    # Langfuse
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://langfuse:3000"

    # App
    mock_mode: bool = False
    environment: str = "development"
    log_level: str = "info"
    backend_workers: int = 1

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
