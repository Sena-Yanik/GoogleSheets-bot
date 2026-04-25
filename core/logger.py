# core/logger.py
import hashlib
import logging
import structlog


def hash_chat_id(chat_id: int, salt: str) -> str:
    """SHA-256 + salt ile chat_id hash'leme. KVKK/GDPR uyumu."""
    return hashlib.sha256(
        f"{chat_id}{salt}".encode()
    ).hexdigest()[:16]


def mask_query(query: str) -> str:
    """Sorgu içeriğini maskeleyerek sadece uzunluk bilgisi döndür."""
    return f"[{len(query)} chars]"


def configure_logging(log_level: str) -> None:
    """structlog yapılandırması - JSON formatında, ISO timestamp ile."""
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
    )


log = structlog.get_logger()

# Zorunlu log event'leri ve alanları:
#
# query_received:      chat_id_hash, query_length, session_state
# parse_success:       chat_id_hash, intent, filter_count, duration_ms
# parse_error:         chat_id_hash, query_preview, error, attempt
# validation_error:    chat_id_hash, error_code
# execution_success:   chat_id_hash, intent, result_count, duration_ms
# execution_error:     chat_id_hash, intent, error
# unauthorized_access: chat_id_hash, reason
# rate_limited:        chat_id_hash
# cache_hit:           duration_ms
# cache_miss:          duration_ms
# sheets_fetch:        row_count, skipped_rows, duration_ms
# data_cleaning:       skipped_rows, reason
