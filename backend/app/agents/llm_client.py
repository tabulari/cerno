"""OpenRouter LLM client — wraps OpenAI SDK pointed at OpenRouter."""
from openai import AsyncOpenAI
import instructor
import structlog

from app.config import get_settings

logger = structlog.get_logger()

_client = None
_instructor_client = None


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            default_headers={"HTTP-Referer": "https://cerno-agentx.local", "X-Title": "Cerno SRE Agent"},
        )
    return _client


def get_instructor_client() -> instructor.AsyncInstructor:
    global _instructor_client
    if _instructor_client is None:
        _instructor_client = instructor.from_openai(get_openai_client())
    return _instructor_client
