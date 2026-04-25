# engine/execution_engine.py
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Any
from core.config import FIELD_TYPE_MAP, CATEGORICAL_FIELDS
from core.logger import log

DECIMAL_TOLERANCE = Decimal("0.01")


@dataclass
class ExecutionResult:
    """Sorgu çalıştırma sonucu."""
    data: list[dict] = field(default_factory=list)
    count: int = 0
    has_more: bool = False
    sections: dict[str, Any] | None = None


class ExecutionEngine:
    """Deterministik Python sorgu motoru - LLM hesaplama yapmaz."""

    def execute(self, query, data: list[dict]) -> ExecutionResult:
        """ParsedQuery'yi çalıştır ve ExecutionResult döndür."""
        filtered = list(self._apply_filters(data, query.filters))

        match query.intent:
            case "list":
                return self._list(filtered, query)
            case "count":
                return self._count(filtered)
            case "sum":
                return self._sum(filtered, query.aggregation.field)
            case "average":
                return self._average(filtered, query.aggregation.field)
            case "ratio":
                return self._ratio(filtered, query)
            case "report":
                return self._report(filtered, query.report_type)
            case _:
                return ExecutionResult()

    def _apply_filters(self, data: list[dict], filters: list):
        """
        AND mantığı ile filtreleme.
        OR desteği gerekirse sadece bu metod refactor edilir.
        """
        for row in data:
            if all(self._match(row, f) for f in filters):
                yield row

    def _match(self, row: dict, f) -> bool:
        """Tek bir filtreyi bir satıra uygula."""
        # FilterItem (Pydantic model) veya dict olabilir
        if hasattr(f, "field"):
            field_name = f.field
            operator = f.operator
            filter_value = f.value
        else:
            field_name = f["field"]
            operator = f["operator"]
            filter_value = f["value"]

        row_value = row.get(field_name)

        if row_value is None:
            return False

        field_type = FIELD_TYPE_MAP.get(field_name)

        if field_type == str:
            return self._match_string(
                row_value, operator, filter_value, field_name
            )
        elif field_type == Decimal:
            return self._match_decimal(row_value, operator, filter_value)
        elif field_type == bool:
            return row_value == filter_value
        elif field_type == "date":
            return self._match_date(row_value, operator, filter_value)

        return False

    def _match_string(
        self, row_value, operator: str, filter_value, field_name: str
    ) -> bool:
        """String eşleştirme - kategorik alanlarda fuzzy match."""
        rv = str(row_value).lower().strip()
        fv = str(filter_value).lower().strip()

        if field_name in CATEGORICAL_FIELDS:
            # Fuzzy match: kategorik alanlarda esnek eşleştirme
            # LLM değer listesi almıyor, Python eşleştirir
            if operator == "=":
                return rv == fv or fv in rv or rv in fv
            elif operator == "contains":
                return fv in rv
            elif operator == "!=":
                return rv != fv and fv not in rv
        else:
            match operator:
                case "=":
                    return rv == fv
                case "!=":
                    return rv != fv
                case "contains":
                    return fv in rv
        return False

    def _match_decimal(
        self, row_value, operator: str, filter_value
    ) -> bool:
        """Decimal karşılaştırma - tolerance ile eşitlik kontrolü."""
        # Defensive cast: Redis'ten string gelebilir
        if isinstance(row_value, str):
            try:
                row_value = Decimal(row_value)
            except Exception:
                return False
        rv = Decimal(str(row_value))
        fv = Decimal(str(filter_value))
        match operator:
            case "=":
                return abs(rv - fv) < DECIMAL_TOLERANCE
            case "!=":
                return abs(rv - fv) >= DECIMAL_TOLERANCE
            case "<":
                return rv < fv
            case ">":
                return rv > fv
            case "<=":
                return rv <= fv
            case ">=":
                return rv >= fv
        return False

    def _match_date(
        self, row_value, operator: str, filter_value
    ) -> bool:
        """Tarih karşılaştırma - defensive cast ile."""
        # Defensive cast: Redis'ten string gelebilir
        if isinstance(row_value, str):
            try:
                row_value = date.fromisoformat(row_value)
            except ValueError:
                return False
        if isinstance(filter_value, str):
            try:
                filter_value = date.fromisoformat(filter_value)
            except ValueError:
                return False
        match operator:
            case "=":
                return row_value == filter_value
            case "!=":
                return row_value != filter_value
            case "<":
                return row_value < filter_value
            case ">":
                return row_value > filter_value
            case "<=":
                return row_value <= filter_value
            case ">=":
                return row_value >= filter_value
        return False

    def _list(self, data: list[dict], query) -> ExecutionResult:
        """Kayıt listeleme - sıralama ve pagination ile."""
        limit = query.limit or 100
        offset = query.offset or 0
        if query.sort:
            data = sorted(
                data,
                key=lambda r: r.get(query.sort.field) or Decimal("0"),
                reverse=(query.sort.order == "desc"),
            )
        paginated = data[offset: offset + limit]
        return ExecutionResult(
            data=paginated,
            count=len(data),
            has_more=len(data) > offset + limit,
        )

    def _count(self, data: list[dict]) -> ExecutionResult:
        """Kayıt sayısı."""
        return ExecutionResult(
            data=[{"sayi": len(data)}],
            count=len(data),
        )

    def _sum(self, data: list[dict], field_name: str) -> ExecutionResult:
        """Toplam hesaplama - Decimal ile."""
        total = sum(
            (row.get(field_name) or Decimal("0")) for row in data
        )
        return ExecutionResult(
            data=[{
                "toplam": total.quantize(Decimal("0.01"), ROUND_HALF_UP)
            }],
            count=len(data),
        )

    def _average(self, data: list[dict], field_name: str) -> ExecutionResult:
        """Ortalama hesaplama - Decimal ile."""
        if not data:
            return ExecutionResult(
                data=[{"ortalama": Decimal("0")}], count=0
            )
        values = [row.get(field_name) or Decimal("0") for row in data]
        avg = sum(values) / len(values)
        return ExecutionResult(
            data=[{
                "ortalama": avg.quantize(Decimal("0.01"), ROUND_HALF_UP)
            }],
            count=len(data),
        )

    def _ratio(self, data: list[dict], query) -> ExecutionResult:
        """Ödeme oranı hesaplama - ZeroDivisionError koruması ile."""
        results = []
        for row in data:
            borc = row.get("toplam_borc") or Decimal("0")
            odenen = row.get("odenen_tutar") or Decimal("0")
            # ZeroDivisionError koruması
            oran = (
                (odenen / borc * 100).quantize(
                    Decimal("0.01"), ROUND_HALF_UP
                )
                if borc > Decimal("0")
                else Decimal("0")
            )
            results.append({**row, "odeme_orani": oran})

        limit = query.limit or 100
        offset = query.offset or 0
        paginated = results[offset: offset + limit]
        return ExecutionResult(
            data=paginated,
            count=len(results),
            has_more=len(results) > offset + limit,
        )

    def _report(self, data: list[dict], report_type: str) -> ExecutionResult:
        """Rapor üretimi - ReportEngine'e delege et."""
        from engine.report_engine import ReportEngine
        return ReportEngine().generate(report_type, data)
