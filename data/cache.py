# data/cache.py
import json
import time
from decimal import Decimal
from datetime import date
from data.sheets_client import DecimalEncoder
from core.config import settings, FIELD_TYPE_MAP
from core.logger import log


class CacheManager:
    """Redis tabanlı cache - tip restorasyonu ile okuma/yazma."""

    def __init__(self, redis_client, sheets_client):
        self.redis = redis_client
        self.sheets = sheets_client

    async def get_data(self) -> list[dict]:
        """Cache'ten oku veya Sheets'ten çekip cache'le."""
        start = time.monotonic()
        cached = await self.redis.get("sheets:all_data")
        if cached:
            raw = json.loads(cached)
            duration_ms = int((time.monotonic() - start) * 1000)
            log.info("cache_hit", duration_ms=duration_ms)
            return self._restore_types(raw)

        data = await self.sheets.fetch_all()
        await self.redis.setex(
            "sheets:all_data",
            settings.cache_ttl_seconds,
            json.dumps(data, cls=DecimalEncoder),
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        log.info("cache_miss", duration_ms=duration_ms)
        return data

    def _restore_types(self, data: list[dict]) -> list[dict]:
        """
        Redis'ten string olarak gelen Decimal ve date
        alanlarını tekrar doğru tipe çevirir.
        """
        for row in data:
            for field, field_type in FIELD_TYPE_MAP.items():
                val = row.get(field)
                if val is None or val == "":
                    continue
                try:
                    if field_type == Decimal and isinstance(val, str):
                        row[field] = Decimal(val)
                    elif field_type == "date" and isinstance(val, str):
                        row[field] = date.fromisoformat(val)
                except Exception:
                    row[field] = None
        return data

    async def invalidate(self) -> None:
        """Cache'i temizle - admin komutu ile tetiklenir."""
        await self.redis.delete("sheets:all_data")

