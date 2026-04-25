# validation/query_validator.py
from decimal import Decimal, InvalidOperation
from datetime import date
from core.config import (
    FIELD_TYPE_MAP, VALID_INTENTS, VALID_OPERATORS,
    VALID_REPORT_TYPES,
)


class ValidationError(Exception):
    """Doğrulama hatası - error_code ile kullanıcıya friendly mesaj eşleştirilir."""

    def __init__(self, message: str, error_code: str):
        super().__init__(message)
        self.error_code = error_code


class QueryValidator:
    """LLM çıktısını doğrula ve ParsedQuery'ye dönüştür."""

    def validate(self, parsed: dict):
        """Tüm doğrulamaları çalıştır, ParsedQuery döndür."""
        self._check_intent(parsed)
        self._check_filters(parsed.get("filters", []))
        self._check_aggregation(parsed)
        self._check_report_type(parsed)
        from parser.schemas import ParsedQuery
        return ParsedQuery(**parsed)

    def _check_intent(self, parsed: dict) -> None:
        """Intent geçerli mi kontrol et."""
        intent = parsed.get("intent")
        if intent not in VALID_INTENTS:
            raise ValidationError(
                f"Geçersiz intent: '{intent}'",
                error_code="invalid_intent",
            )

    def _check_filters(self, filters: list) -> None:
        """Filtrelerdeki alan, operatör ve değer tiplerini doğrula."""
        for f in filters:
            field = f.get("field")
            operator = f.get("operator")
            value = f.get("value")

            if field not in FIELD_TYPE_MAP:
                raise ValidationError(
                    f"Bilinmeyen alan: '{field}'",
                    error_code="invalid_field",
                )
            if operator not in VALID_OPERATORS:
                raise ValidationError(
                    f"Geçersiz operatör: '{operator}'",
                    error_code="invalid_operator",
                )
            self._check_value_type(field, operator, value)

        self._check_conflicting_filters(filters)

    def _check_value_type(self, field: str, operator: str, value) -> None:
        """Değer tipinin alan tipiyle uyumlu olup olmadığını kontrol et."""
        expected = FIELD_TYPE_MAP.get(field)
        if expected == Decimal:
            try:
                Decimal(str(value))
            except InvalidOperation:
                raise ValidationError(
                    f"'{field}' sayısal değer gerektirir",
                    error_code="type_mismatch",
                )
        elif expected == bool:
            if not isinstance(value, bool):
                raise ValidationError(
                    f"'{field}' true/false değer gerektirir",
                    error_code="type_mismatch",
                )

    def _check_conflicting_filters(self, filters: list) -> None:
        """Aynı alan için çelişkili aralık filtrelerini tespit et."""
        field_ranges: dict[str, dict] = {}
        for f in filters:
            field = f["field"]
            op = f["operator"]
            if FIELD_TYPE_MAP.get(field) != Decimal:
                continue
            if field not in field_ranges:
                field_ranges[field] = {}
            try:
                field_ranges[field][op] = Decimal(str(f["value"]))
            except InvalidOperation:
                continue

        for field, ops in field_ranges.items():
            lower = ops.get(">") or ops.get(">=")
            upper = ops.get("<") or ops.get("<=")
            if lower and upper and lower >= upper:
                raise ValidationError(
                    f"'{field}' için çelişkili filtre",
                    error_code="conflicting_filters",
                )

    def _check_aggregation(self, parsed: dict) -> None:
        """Aggregation alanının geçerliliğini kontrol et."""
        agg = parsed.get("aggregation")
        if not agg:
            return
        if agg.get("field") and agg["field"] not in FIELD_TYPE_MAP:
            raise ValidationError(
                f"Bilinmeyen aggregation alanı: '{agg['field']}'",
                error_code="invalid_field",
            )

    def _check_report_type(self, parsed: dict) -> None:
        """Report intent'inde rapor tipinin belirtildiğini kontrol et."""
        if parsed.get("intent") == "report":
            if parsed.get("report_type") not in VALID_REPORT_TYPES:
                raise ValidationError(
                    "Rapor tipi belirtilmeli",
                    error_code="missing_report_type",
                )
