# core/security.py
from fastapi import Request, HTTPException
from core.config import settings
from core.logger import log


async def verify_telegram_secret(request: Request) -> None:
    """Webhook secret token doğrulama - 2 zorunlu güvenlik katmanından biri."""
    token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not token or token != settings.telegram_secret_token:
        log.warning("unauthorized_access", reason="invalid_secret_token")
        raise HTTPException(status_code=403, detail="Forbidden")


# Telegram IP aralıkları - Nginx/reverse proxy yoksa kullanılabilir
# X-Forwarded-For manipülasyon riski taşır
TELEGRAM_IP_RANGES = ["149.154.160.0/20", "91.108.4.0/22"]


class SecurityManager:
    """Whitelist ve rate limiting yönetimi."""

    def __init__(self, redis_client, settings):
        self.redis = redis_client
        self.settings = settings

    def is_authorized(self, chat_id: int) -> bool:
        """Chat ID whitelist kontrolü."""
        return chat_id in self.settings.allowed_chat_ids

    async def check_rate_limit(self, chat_id: int) -> bool:
        """Redis tabanlı sliding window rate limiting - dakikada max istek."""
        key = f"rate:{chat_id}"
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, 60)
        return count <= self.settings.max_requests_per_minute
