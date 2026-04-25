# core/config.py
from pydantic_settings import BaseSettings
from pydantic import field_validator, ConfigDict
from decimal import Decimal


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")
    telegram_bot_token: str
    telegram_webhook_url: str
    telegram_secret_token: str
    webhook_path: str
    groq_api_key: str
    google_sheets_id: str
    google_credentials_json: str
    redis_url: str
    allowed_chat_ids: list[int]
    admin_chat_ids: list[int]
    log_salt: str
    max_requests_per_minute: int = 10
    cache_ttl_seconds: int = 300
    log_level: str = "INFO"
    ngrok_authtoken: str | None = None
    ngrok_domain: str | None = None
    @field_validator("allowed_chat_ids", "admin_chat_ids", mode="before")
    @classmethod
    def parse_comma_separated_ints(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v


settings = Settings()

# Ham Sheets sütunu → sistem adı eşleştirmesi
FIELD_MAP = {
    "id": "id",
    "entity_name": "musteri_adi",
    "entity_type": "musteri_turu",
    "numeric_value_1": "toplam_borc",
    "numeric_value_2": "odenen_tutar",
    "status_flag": "dava_var_mi",
    "date_field": "kayit_tarihi",
    "category": "kategori",
}

# Tip haritası - float YOK, Decimal var
FIELD_TYPE_MAP: dict[str, type | str] = {
    "id": str,
    "musteri_adi": str,
    "musteri_turu": str,
    "toplam_borc": Decimal,
    "odenen_tutar": Decimal,
    "dava_var_mi": bool,
    "kayit_tarihi": "date",
    "kategori": str,
}

# Sadece alan adları prompt'a girer, değerler girmez
# Değer eşleştirmesi Python'da fuzzy match ile yapılır
CATEGORICAL_FIELDS = ["kategori", "musteri_turu"]

# Zorunlu alanlar - boş satırlar temizlenir
REQUIRED_FIELDS = ["musteri_adi", "toplam_borc", "odenen_tutar"]

VALID_INTENTS = {
    "list", "count", "sum", "average",
    "ratio", "report", "clarification_needed",
}
VALID_OPERATORS = {"=", "!=", "<", ">", "<=", ">=", "contains"}
VALID_REPORT_TYPES = {"general", "performance", "risk", "category"}

# Kullanıcıya gösterilecek hata mesajları
# Pydantic/teknik detay kullanıcıya sızdırılmaz
USER_FRIENDLY_ERRORS = {
    "invalid_intent": "Sorgu tipi anlaşılamadı.",
    "invalid_field": "Geçersiz alan adı kullanıldı.",
    "invalid_operator": "Geçersiz karşılaştırma operatörü.",
    "type_mismatch": "Değer tipi uyumsuz.",
    "conflicting_filters": "Filtreler birbiriyle çelişiyor.",
    "missing_report_type": "Rapor tipi belirtilmeli.",
    "default": "Sorgunuz işlenemedi. Lütfen tekrar deneyin.",
}
