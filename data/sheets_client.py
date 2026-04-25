# data/sheets_client.py
import asyncio
import json
import base64
import gspread
from decimal import Decimal
from datetime import datetime, date
from google.oauth2.service_account import Credentials
from core.config import (
    settings, FIELD_MAP, FIELD_TYPE_MAP, REQUIRED_FIELDS,
)
from core.logger import log


class DecimalEncoder(json.JSONEncoder):
    """Decimal ve date tiplerini JSON'a serileştirmek için özel encoder."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


class SheetsClient:
    """Google Sheets istemcisi - lazy init, executor içinde çalışır."""

    def __init__(self):
        # __init__ içinde ağ çağrısı yok, sadece credential yükleme
        self._client = None
        self._creds = self._load_creds()

    def _load_creds(self) -> Credentials:
        """Base64-encoded service account JSON'dan credential oluştur."""
        info = json.loads(
            base64.b64decode(settings.google_credentials_json)
        )
        return Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )

    async def _get_client(self):
        """Lazy init: ilk fetch anında oluşturulur, executor içinde."""
        if self._client is None:
            loop = asyncio.get_running_loop()
            self._client = await loop.run_in_executor(
                None,
                lambda: gspread.authorize(self._creds),
            )
        return self._client

    async def fetch_all(self) -> list[dict]:
        """Tüm satırları çek, dönüştür ve temizle."""
        client = await self._get_client()
        loop = asyncio.get_running_loop()
        raw = await loop.run_in_executor(
            None,
            lambda: client.open_by_key(
                settings.google_sheets_id
            ).get_worksheet(0).get_all_records(numericise_ignore=["all"]),
        )
        return self._transform(raw)

    def _transform(self, raw: list[dict]) -> list[dict]:
        """Ham Sheet verisini sistem alan adlarına ve tiplerine dönüştür."""
        result = []
        skipped = 0
        for row in raw:
            transformed = {}
            for sheet_col, system_name in FIELD_MAP.items():
                val = row.get(sheet_col, "")
                transformed[system_name] = self._cast(system_name, val)
            if self._is_valid_row(transformed):
                result.append(transformed)
            else:
                skipped += 1
        if skipped:
            log.warning(
                "data_cleaning",
                skipped_rows=skipped,
                reason="missing_required_fields",
            )
        return result

    def _is_valid_row(self, row: dict) -> bool:
        """Zorunlu alanları kontrol et - boş veya sıfır satırları atla."""
        for field in REQUIRED_FIELDS:
            val = row.get(field)
            if val is None or val == "":
                return False
            if isinstance(val, Decimal) and val == Decimal("0"):
                return False
        return True

    def _cast(self, field: str, value):
        """String değeri FIELD_TYPE_MAP'e göre doğru tipe dönüştür."""
        field_type = FIELD_TYPE_MAP.get(field)
        try:
            if field_type == Decimal:
                if not value:
                    return Decimal("0")
                if isinstance(value, (int, float)):
                    return Decimal(str(value))
                
                # Sadece string ise Türkçe/İngilizce format ayrımı yap
                val_str = str(value).strip()
                # Eğer hem virgül hem nokta varsa:
                if "." in val_str and "," in val_str:
                    if val_str.rfind(",") > val_str.rfind("."): 
                        # Türkçe: 12.000,50 -> 12000.50
                        cleaned = val_str.replace(".", "").replace(",", ".")
                    else:
                        # İngilizce: 12,000.50 -> 12000.50
                        cleaned = val_str.replace(",", "")
                elif "," in val_str:
                    # Sadece virgül var: Düz Türkçe ondalık veya İngilizce binlik olabilir.
                    # Basit heuristic: virgülden sonra 3 rakam varsa binliktir, 2 rakam varsa ondalıktır.
                    # Veya en kolayı, sayıyı önce float çevirmeyi denemektir.
                    if len(val_str) - val_str.rfind(",") == 3: # X,00 (Turkish decimal format with 2 places)
                        cleaned = val_str.replace(",", ".")
                    else:
                        cleaned = val_str.replace(",", "") # English thousands
                elif "." in val_str:
                    parts = val_str.split(".")
                    # Eğer noktadan sonra tam 3 basamak varsa bu muhtemelen Türkçe binlik ayracıdır (Örn: "2.000")
                    if len(parts) > 1 and len(parts[-1]) == 3:
                        cleaned = val_str.replace(".", "")
                    else:
                        cleaned = val_str
                else:
                    # Hiçbiri yok
                    cleaned = val_str
                
                return Decimal(cleaned)
            elif field_type == bool:
                return str(value).lower() in ("evet", "true", "1", "yes")
            elif field_type == "date":
                if not value:
                    return None
                return datetime.strptime(
                    str(value), "%d.%m.%Y"
                ).date()
            else:
                return str(value).strip() if value else ""
        except Exception:
            return None
