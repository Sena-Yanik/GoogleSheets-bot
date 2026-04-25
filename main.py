from contextlib import asynccontextmanager
from dataclasses import dataclass
from fastapi import FastAPI, Request, Depends
import redis.asyncio as aioredis
from telegram import Update
from telegram.ext import Application

from core.config import settings
from core.logger import configure_logging, log
from core.security import SecurityManager, verify_telegram_secret
from data.sheets_client import SheetsClient
from data.cache import CacheManager
from session.session_manager import SessionManager
from parser.llm_parser import LLMParser
from validation.query_validator import QueryValidator
from engine.execution_engine import ExecutionEngine
from bot.handlers import handle_message
from bot.formatter import ResponseFormatter


@dataclass
class Services:
    """Tüm servisler - Singleton, lifespan'da oluşturulur."""
    redis: object
    sheets: SheetsClient
    cache: CacheManager
    session: SessionManager
    security: SecurityManager
    parser: LLMParser
    validator: QueryValidator
    engine: ExecutionEngine
    formatter: ResponseFormatter
    bot: Application


_services: Services = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama yaşam döngüsü - startup/shutdown sırası önemli."""
    global _services
    configure_logging(settings.log_level)
    log.info("Uygulama başlatılıyor")

    # Servis oluşturma
    redis_client = aioredis.from_url(settings.redis_url)
    sheets_client = SheetsClient()
    cache_manager = CacheManager(redis_client, sheets_client)
    session_manager = SessionManager(redis_client)
    security_manager = SecurityManager(redis_client, settings)
    llm_parser = LLMParser()
    validator = QueryValidator()
    engine = ExecutionEngine()
    formatter = ResponseFormatter()

    # İlk veri çekimi (cache ısıtma)
    try:
        await cache_manager.get_data()
        log.info("cache_warmed")
    except Exception as e:
        log.warning("cache_warm_failed", error=str(e))

    # Telegram bot başlatma
    bot_app = Application.builder().token(
        settings.telegram_bot_token
    ).build()
    await bot_app.initialize()
    await bot_app.bot.set_webhook(
        url=f"{settings.telegram_webhook_url}{settings.webhook_path}",
        secret_token=settings.telegram_secret_token,
    )

    _services = Services(
        redis=redis_client,
        sheets=sheets_client,
        cache=cache_manager,
        session=session_manager,
        security=security_manager,
        parser=llm_parser,
        validator=validator,
        engine=engine,
        formatter=formatter,
        bot=bot_app,
    )

    log.info("Uygulama hazır")
    yield

    # Graceful shutdown - sıra önemli
    log.info("Uygulama kapatılıyor")
    await bot_app.bot.delete_webhook()
    await bot_app.shutdown()
    await redis_client.aclose()
    log.info("Uygulama kapatıldı")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    """Sağlık kontrolü - Docker healthcheck ve monitoring için."""
    status = {"status": "ok"}
    if _services and _services.redis:
        try:
            await _services.redis.ping()
            status["redis"] = "connected"
        except Exception:
            status["redis"] = "disconnected"
            status["status"] = "degraded"
    return status


def get_services() -> Services:
    """Dependency injection - Singleton servisleri döndür."""
    return _services


@app.post(
    "/{webhook_path:path}",
    dependencies=[Depends(verify_telegram_secret)],
)
async def webhook(
    request: Request,
    services: Services = Depends(get_services),
):
    """Telegram webhook endpoint'i."""
    # Webhook path doğrulama
    if request.url.path != settings.webhook_path:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not Found")

    data = await request.json()
    update = Update.de_json(data, services.bot.bot)

    if update and update.message:
        await handle_message(update, None, services)

    return {"ok": True}
