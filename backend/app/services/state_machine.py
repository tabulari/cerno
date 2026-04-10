import json
import time
import structlog
from datetime import datetime, timezone

from app.redis import get_redis
from app.models.schemas import IncidentState, StateTransition

logger = structlog.get_logger()

VALID_TRANSITIONS = {
    IncidentState.SUBMITTED: [IncidentState.TRIAGING, IncidentState.FAILED],
    IncidentState.TRIAGING: [IncidentState.TRIAGED, IncidentState.FAILED],
    IncidentState.TRIAGED: [IncidentState.TICKETED, IncidentState.FAILED],
    IncidentState.TICKETED: [IncidentState.NOTIFIED, IncidentState.FAILED],
    IncidentState.NOTIFIED: [IncidentState.RESOLVED],
    IncidentState.FAILED: [IncidentState.TRIAGING],
    IncidentState.RESOLVED: [],
}


class StateMachine:
    def __init__(self, incident_id: int, redis):
        self.incident_id = incident_id
        self.redis = redis
        self._key = f"incident:{incident_id}:state"
        self._transitions_key = f"incident:{incident_id}:transitions"
        self._start_time = time.monotonic()

    @classmethod
    async def create(cls, incident_id: int) -> "StateMachine":
        redis = await get_redis()
        return cls(incident_id, redis)

    async def get_state(self) -> IncidentState:
        state = await self.redis.get(self._key)
        if state is None:
            return IncidentState.SUBMITTED
        return IncidentState(state)

    async def transition(
        self, from_state: IncidentState, to_state: IncidentState, metadata: dict
    ) -> StateTransition:
        if from_state != IncidentState.SUBMITTED:
            current = await self.get_state()
            if current != from_state:
                raise ValueError(f"Expected state {from_state}, got {current}")

            if to_state not in VALID_TRANSITIONS.get(from_state, []):
                raise ValueError(f"Invalid transition: {from_state} -> {to_state}")

        now = datetime.now(timezone.utc)
        elapsed = int((time.monotonic() - self._start_time) * 1000)

        transition = StateTransition(
            incident_id=self.incident_id,
            from_state=from_state,
            to_state=to_state,
            timestamp=now,
            duration_ms=elapsed,
            metadata=metadata,
        )

        await self.redis.set(self._key, to_state.value)
        await self.redis.rpush(self._transitions_key, transition.model_dump_json())

        await self.redis.publish(
            f"incident:{self.incident_id}:events",
            json.dumps({"type": "state_change", "state": to_state.value, "timestamp": now.isoformat()}),
        )

        logger.info(
            "state.transition",
            incident_id=self.incident_id,
            from_state=from_state.value,
            to_state=to_state.value,
            duration_ms=elapsed,
        )

        self._start_time = time.monotonic()
        return transition

    async def get_transitions(self) -> list[StateTransition]:
        raw = await self.redis.lrange(self._transitions_key, 0, -1)
        return [StateTransition.model_validate_json(r) for r in raw]
