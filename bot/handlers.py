# bot/handlers.py
import time
from parser.prompt_builder import build_system_prompt, build_refinement_messages
from parser.schemas import ParsedQuery
from core.config import USER_FRIENDLY_ERRORS, settings
from core.logger import log, hash_chat_id, mask_query

HELP_TEXT = (
    "*📖 Yardım*\n\n"
    "Doğal dilde sorgular yazarak verilerinizi sorgulayabilirsiniz\\.\n\n"
    "*Örnek sorgular:*\n"
    "▪️ _50 binden fazla borcu olan müşteriler_\n"
    "▪️ _dava olan müşteri sayısı_\n"
    "▪️ _konut kategorisindeki toplam borç_\n"
    "▪️ _genel rapor_\n\n"
    "*Komutlar:*\n"
    "/rapor \\- Genel rapor\n"
    "/yenile \\- Cache temizle \\(admin\\)\n"
    "/iptal \\- İşlemi iptal et\n"
    "/yardim \\- Bu mesaj"
)


async def handle_message(update, context, services) -> None:
    """Ana mesaj handler - tüm akış burada yönetilir."""
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()
    chat_hash = hash_chat_id(chat_id, settings.log_salt)

    log.info(
        "query_received",
        chat_id_hash=chat_hash,
        query_length=len(text),
    )

    # 1. Yetki kontrolü
    if not services.security.is_authorized(chat_id):
        log.warning(
            "unauthorized_access",
            chat_id_hash=chat_hash,
            reason="not_in_whitelist",
        )
        return

    # 2. Rate limiting
    if not await services.security.check_rate_limit(chat_id):
        log.info("rate_limited", chat_id_hash=chat_hash)
        await update.message.reply_text(
            "Çok fazla istek gönderdiniz\\. Lütfen bekleyin\\.",
            parse_mode="MarkdownV2",
        )
        return

    # 3. Boş mesaj kontrolü
    if not text:
        return

    # 4. Komut kontrolü
    if text.startswith("/"):
        await handle_command(text, chat_id, update, services, chat_hash)
        return

    # 5. Session kontrolü - clarification akışı
    session = await services.session.get(chat_id)
    system_prompt = build_system_prompt()

    if session and session.get("state") == "awaiting_clarification":
        # Clarification refinement: conversation history ile
        messages = build_refinement_messages(
            original_query=session["original_query"],
            clarification_question=session["clarification_question"],
            user_answer=text,
        )
        await services.session.clear(chat_id)
        try:
            start = time.monotonic()
            parsed_dict = await services.parser.parse_with_history(
                messages, system_prompt
            )
            duration_ms = int((time.monotonic() - start) * 1000)
            log.info(
                "parse_success",
                chat_id_hash=chat_hash,
                intent=parsed_dict.get("intent"),
                filter_count=len(parsed_dict.get("filters", [])),
                duration_ms=duration_ms,
            )
        except Exception as e:
            log.error(
                "parse_error",
                chat_id_hash=chat_hash,
                error=str(e),
                query_preview=mask_query(text),
            )
            await update.message.reply_text(
                "Sorgunuz işlenemedi\\. Lütfen tekrar deneyin\\.",
                parse_mode="MarkdownV2",
            )
            return
    else:
        # Normal sorgu akışı
        try:
            start = time.monotonic()
            parsed_dict = await services.parser.parse(text, system_prompt)
            duration_ms = int((time.monotonic() - start) * 1000)
            log.info(
                "parse_success",
                chat_id_hash=chat_hash,
                intent=parsed_dict.get("intent"),
                filter_count=len(parsed_dict.get("filters", [])),
                duration_ms=duration_ms,
            )
        except Exception as e:
            log.error(
                "parse_error",
                chat_id_hash=chat_hash,
                error=str(e),
                query_preview=mask_query(text),
            )
            await update.message.reply_text(
                "Sorgunuz işlenemedi\\. Lütfen tekrar deneyin\\.",
                parse_mode="MarkdownV2",
            )
            return

    # 6. Clarification needed kontrolü
    if parsed_dict.get("intent") == "clarification_needed":
        question = parsed_dict.get("clarification_question", "")
        await services.session.set(chat_id, {
            "state": "awaiting_clarification",
            "original_query": text,
            "clarification_question": question,
            "timestamp": time.time(),
        })
        await update.message.reply_text(question)
        return

    # 7. Validation
    try:
        query = services.validator.validate(parsed_dict)
    except Exception as e:
        error_code = getattr(e, "error_code", "default")
        user_msg = USER_FRIENDLY_ERRORS.get(
            error_code, USER_FRIENDLY_ERRORS["default"]
        )
        log.warning(
            "validation_error",
            chat_id_hash=chat_hash,
            error_code=error_code,
        )
        await update.message.reply_text(user_msg)
        return

    # 8. Execution
    try:
        start = time.monotonic()
        data = await services.cache.get_data()
        result = services.engine.execute(query, data)
        duration_ms = int((time.monotonic() - start) * 1000)
        log.info(
            "execution_success",
            chat_id_hash=chat_hash,
            intent=query.intent,
            result_count=result.count,
            duration_ms=duration_ms,
        )
    except Exception as e:
        log.error(
            "execution_error",
            chat_id_hash=chat_hash,
            intent=query.intent,
            error=str(e),
        )
        await update.message.reply_text(
            USER_FRIENDLY_ERRORS["default"]
        )
        return

    # 9. Formatlama ve yanıt
    response_text = services.formatter.format(result, query)
    await update.message.reply_text(
        response_text,
        parse_mode="MarkdownV2",
    )


async def handle_command(
    text: str,
    chat_id: int,
    update,
    services,
    chat_hash: str,
) -> None:
    """Slash komutlarını işle."""
    cmd = text.split()[0].lower()
    match cmd:
        case "/rapor":
            data = await services.cache.get_data()
            query = ParsedQuery(
                intent="report",
                report_type="general",
                filters=[],
                limit=100,
                offset=0,
            )
            result = services.engine.execute(query, data)
            response_text = services.formatter.format(result, None)
            await update.message.reply_text(
                response_text,
                parse_mode="MarkdownV2",
            )

        case "/yenile":
            if chat_id not in settings.admin_chat_ids:
                return
            await services.cache.invalidate()
            await update.message.reply_text(
                "Cache temizlendi\\.",
                parse_mode="MarkdownV2",
            )

        case "/iptal":
            await services.session.clear(chat_id)
            await update.message.reply_text(
                "İşlem iptal edildi\\.",
                parse_mode="MarkdownV2",
            )

        case "/yardim":
            await update.message.reply_text(
                HELP_TEXT,
                parse_mode="MarkdownV2",
            )
