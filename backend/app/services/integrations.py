from typing import Protocol, runtime_checkable
import structlog

from app.config import get_settings
from app.models.schemas import TriageResult

logger = structlog.get_logger()


@runtime_checkable
class TicketingProvider(Protocol):
    async def create_ticket(self, incident_id: int, result: TriageResult) -> dict: ...


@runtime_checkable
class NotificationProvider(Protocol):
    async def notify(self, incident_id: int, result: TriageResult, channel: str) -> bool: ...


class MockTicketing:
    async def create_ticket(self, incident_id: int, result: TriageResult) -> dict:
        logger.info("mock.ticket.created", incident_id=incident_id, severity=result.severity.value)
        return {
            "external_id": f"MOCK-{incident_id}",
            "external_url": f"https://mock-linear.example.com/issue/MOCK-{incident_id}",
            "provider": "mock",
        }


class MockNotification:
    async def notify(self, incident_id: int, result: TriageResult, channel: str) -> bool:
        logger.info(
            "mock.notification.sent",
            incident_id=incident_id,
            channel=channel,
            severity=result.severity.value,
        )
        return True


def get_ticketing() -> TicketingProvider:
    settings = get_settings()
    if settings.mock_mode:
        return MockTicketing()
    return MockTicketing()


def get_notification() -> NotificationProvider:
    settings = get_settings()
    if settings.mock_mode:
        return MockNotification()
    return MockNotification()
