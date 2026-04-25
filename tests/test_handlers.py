# tests/test_handlers.py
import os
import sys
import time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.handlers import handle_message, handle_command, HELP_TEXT


class MockServices:
    """Test için mock services nesnesi."""

    def __init__(self):
        self.security = MagicMock()
        self.security.is_authorized = MagicMock(return_value=True)
        self.security.check_rate_limit = AsyncMock(return_value=True)

        self.session = MagicMock()
        self.session.get = AsyncMock(return_value=None)
        self.session.set = AsyncMock()
        self.session.clear = AsyncMock()

        self.parser = MagicMock()
        self.parser.parse = AsyncMock(return_value={
            "intent": "count",
            "filters": [{"field": "dava_var_mi", "operator": "=", "value": True}],
            "limit": 100,
            "offset": 0,
        })
        self.parser.parse_with_history = AsyncMock()

        self.validator = MagicMock()
        self.validator.validate = MagicMock()

        self.cache = MagicMock()
        self.cache.get_data = AsyncMock(return_value=[])
        self.cache.invalidate = AsyncMock()

        self.engine = MagicMock()
        self.engine.execute = MagicMock()

        self.formatter = MagicMock()
        self.formatter.format = MagicMock(return_value="formatted response")

        self.bot = MagicMock()


class MockUpdate:
    """Test için mock Telegram Update nesnesi."""

    def __init__(self, text="test query", chat_id=123456):
        self.effective_chat = MagicMock()
        self.effective_chat.id = chat_id
        self.message = MagicMock()
        self.message.text = text
        self.message.reply_text = AsyncMock()


# ─── Authorization Testleri ───


@pytest.mark.asyncio
async def test_unauthorized_user_rejected():
    services = MockServices()
    services.security.is_authorized.return_value = False
    update = MockUpdate()

    await handle_message(update, None, services)

    update.message.reply_text.assert_not_called()
    services.parser.parse.assert_not_called()


@pytest.mark.asyncio
async def test_authorized_user_accepted():
    services = MockServices()
    update = MockUpdate(text="dava olan müşteri sayısı")

    from engine.execution_engine import ExecutionResult
    services.engine.execute.return_value = ExecutionResult(
        data=[{"sayi": 5}], count=5
    )

    await handle_message(update, None, services)

    services.parser.parse.assert_called_once()


# ─── Rate Limiting Testleri ───


@pytest.mark.asyncio
async def test_rate_limited_user():
    services = MockServices()
    services.security.check_rate_limit.return_value = False
    update = MockUpdate()

    await handle_message(update, None, services)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "fazla istek" in call_args[0][0]


# ─── Boş Mesaj Testleri ───


@pytest.mark.asyncio
async def test_empty_message_ignored():
    services = MockServices()
    update = MockUpdate(text="")

    await handle_message(update, None, services)

    services.parser.parse.assert_not_called()


@pytest.mark.asyncio
async def test_none_text_ignored():
    services = MockServices()
    update = MockUpdate()
    update.message.text = None

    await handle_message(update, None, services)

    services.parser.parse.assert_not_called()


# ─── Clarification Testleri ───


@pytest.mark.asyncio
async def test_clarification_needed():
    services = MockServices()
    services.parser.parse.return_value = {
        "intent": "clarification_needed",
        "filters": [],
        "clarification_question": "Ne öğrenmek istiyorsunuz?",
        "limit": 100,
        "offset": 0,
    }
    update = MockUpdate(text="ahmet")

    await handle_message(update, None, services)

    services.session.set.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "Ne öğrenmek istiyorsunuz?" in call_args[0][0]


@pytest.mark.asyncio
async def test_clarification_refinement():
    services = MockServices()
    services.session.get.return_value = {
        "state": "awaiting_clarification",
        "original_query": "ahmet",
        "clarification_question": "Borç mu?",
        "timestamp": time.time(),
    }
    services.parser.parse_with_history.return_value = {
        "intent": "list",
        "filters": [{"field": "musteri_adi", "operator": "contains", "value": "ahmet"}],
        "limit": 100,
        "offset": 0,
    }

    from engine.execution_engine import ExecutionResult
    services.engine.execute.return_value = ExecutionResult(
        data=[{"musteri_adi": "Ahmet Yılmaz"}], count=1
    )

    update = MockUpdate(text="borç durumu")

    await handle_message(update, None, services)

    services.parser.parse_with_history.assert_called_once()
    services.session.clear.assert_called_once()


# ─── Parse Hatası Testleri ───


@pytest.mark.asyncio
async def test_parse_error_sends_friendly_message():
    services = MockServices()
    services.parser.parse.side_effect = Exception("LLM error")
    update = MockUpdate(text="test sorgu")

    await handle_message(update, None, services)

    call_args = update.message.reply_text.call_args
    assert "işlenemedi" in call_args[0][0]


# ─── Validation Hatası Testleri ───


@pytest.mark.asyncio
async def test_validation_error_sends_friendly_message():
    from validation.query_validator import ValidationError

    services = MockServices()
    error = ValidationError("test", error_code="invalid_intent")
    services.validator.validate.side_effect = error
    update = MockUpdate(text="test sorgu")

    await handle_message(update, None, services)

    update.message.reply_text.assert_called_once()


# ─── Execution Hatası Testleri ───


@pytest.mark.asyncio
async def test_execution_error_sends_friendly_message():
    services = MockServices()
    services.engine.execute.side_effect = Exception("DB error")
    update = MockUpdate(text="test sorgu")

    await handle_message(update, None, services)

    update.message.reply_text.assert_called_once()


# ─── Başarılı Akış Testi ───


@pytest.mark.asyncio
async def test_successful_flow():
    from engine.execution_engine import ExecutionResult

    services = MockServices()
    services.engine.execute.return_value = ExecutionResult(
        data=[{"sayi": 10}], count=10
    )

    update = MockUpdate(text="dava olan müşteri sayısı")

    await handle_message(update, None, services)

    services.parser.parse.assert_called_once()
    services.validator.validate.assert_called_once()
    services.engine.execute.assert_called_once()
    services.formatter.format.assert_called_once()
    update.message.reply_text.assert_called_once()


# ─── Komut Testleri ───


@pytest.mark.asyncio
async def test_command_rapor():
    from engine.execution_engine import ExecutionResult

    services = MockServices()
    services.engine.execute.return_value = ExecutionResult(
        sections={"toplam_kayit": 100}
    )

    update = MockUpdate(text="/rapor")
    chat_hash = "test_hash"

    await handle_command("/rapor", 123456, update, services, chat_hash)

    services.cache.get_data.assert_called_once()
    services.engine.execute.assert_called_once()
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_command_yenile_admin():
    services = MockServices()
    update = MockUpdate(text="/yenile")

    with patch("bot.handlers.settings") as mock_settings:
        mock_settings.admin_chat_ids = [123456]
        await handle_command("/yenile", 123456, update, services, "hash")

    services.cache.invalidate.assert_called_once()
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_command_yenile_non_admin():
    services = MockServices()
    update = MockUpdate(text="/yenile")

    with patch("bot.handlers.settings") as mock_settings:
        mock_settings.admin_chat_ids = [999999]
        await handle_command("/yenile", 123456, update, services, "hash")

    services.cache.invalidate.assert_not_called()


@pytest.mark.asyncio
async def test_command_iptal():
    services = MockServices()
    update = MockUpdate(text="/iptal")

    await handle_command("/iptal", 123456, update, services, "hash")

    services.session.clear.assert_called_once()
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_command_yardim():
    services = MockServices()
    update = MockUpdate(text="/yardim")

    await handle_command("/yardim", 123456, update, services, "hash")

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert call_args[0][0] == HELP_TEXT


@pytest.mark.asyncio
async def test_command_routing():
    services = MockServices()
    update = MockUpdate(text="/yardim")

    await handle_message(update, None, services)

    # Yardım mesajı gönderilmiş olmalı
    update.message.reply_text.assert_called_once()
