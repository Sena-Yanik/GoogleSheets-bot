# session/session_manager.py
import json
from core.config import settings

SESSION_TTL = 300


class SessionManager:
    """Redis tabanlı session yönetimi - clarification akışı için."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def get(self, chat_id: int) -> dict | None:
        """Session verisini oku."""
        raw = await self.redis.get(f"session:{chat_id}")
        return json.loads(raw) if raw else None

    async def set(self, chat_id: int, data: dict) -> None:
        """Session verisini TTL ile kaydet."""
        await self.redis.setex(
            f"session:{chat_id}",
            SESSION_TTL,
            json.dumps(data),
        )

    async def clear(self, chat_id: int) -> None:
        """Session verisini sil."""
        await self.redis.delete(f"session:{chat_id}")


# Session verisi yapısı:
# {
#   "state": "awaiting_clarification",
#   "original_query": "...",
#   "clarification_question": "...",
#   "timestamp": 1234567890
# }
