# tests/test_engine.py
import os
import sys
from decimal import Decimal
from datetime import date
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import SAMPLE_DATA
from engine.execution_engine import ExecutionEngine, ExecutionResult


class MockQuery:
    """Test için minimal sorgu nesnesi."""

    def __init__(self, **kwargs):
        self.intent = kwargs.get("intent", "list")
        self.filters = kwargs.get("filters", [])
        self.sort = kwargs.get("sort", None)
        self.limit = kwargs.get("limit", 100)
        self.offset = kwargs.get("offset", 0)
        self.aggregation = kwargs.get("aggregation", None)
        self.report_type = kwargs.get("report_type", None)
        self.fields = kwargs.get("fields", [])

    class _Agg:
        def __init__(self, field):
            self.field = field
            self.type = "sum"


def test_and_filter():
    engine = ExecutionEngine()
    filters = [
        {"field": "toplam_borc", "operator": ">", "value": "5000"},
        {"field": "musteri_turu", "operator": "=", "value": "bireysel"},
    ]
    result = list(engine._apply_filters(SAMPLE_DATA, filters))
    assert len(result) == 1
    assert result[0]["musteri_adi"] == "Ali Veli"


def test_decimal_equality_tolerance():
    engine = ExecutionEngine()
    f = {"field": "toplam_borc", "operator": "=", "value": "10000.005"}
    assert engine._match(SAMPLE_DATA[0], f) is True


def test_zero_division_protection():
    engine = ExecutionEngine()
    row = {**SAMPLE_DATA[0], "toplam_borc": Decimal("0")}
    query = MockQuery(limit=100, offset=0)
    result = engine._ratio([row], query)
    assert result.data[0]["odeme_orani"] == Decimal("0")


def test_date_defensive_cast():
    engine = ExecutionEngine()
    row = {**SAMPLE_DATA[0], "kayit_tarihi": "2024-01-15"}
    f = {"field": "kayit_tarihi", "operator": ">", "value": "2024-01-01"}
    assert engine._match(row, f) is True


def test_date_comparison_operators():
    engine = ExecutionEngine()
    row = {**SAMPLE_DATA[0], "kayit_tarihi": date(2024, 6, 15)}

    assert engine._match(row, {"field": "kayit_tarihi", "operator": "=", "value": "2024-06-15"}) is True
    assert engine._match(row, {"field": "kayit_tarihi", "operator": "!=", "value": "2024-01-01"}) is True
    assert engine._match(row, {"field": "kayit_tarihi", "operator": "<", "value": "2024-12-31"}) is True
    assert engine._match(row, {"field": "kayit_tarihi", "operator": ">=", "value": "2024-06-15"}) is True
    assert engine._match(row, {"field": "kayit_tarihi", "operator": "<=", "value": "2024-06-15"}) is True


def test_categorical_fuzzy_match():
    engine = ExecutionEngine()
    f = {"field": "kategori", "operator": "=", "value": "konutlar"}
    # "konut" in "konutlar" → True (fuzzy match)
    assert engine._match(SAMPLE_DATA[0], f) is True


def test_categorical_contains():
    engine = ExecutionEngine()
    f = {"field": "kategori", "operator": "contains", "value": "kon"}
    assert engine._match(SAMPLE_DATA[0], f) is True


def test_categorical_not_equal():
    engine = ExecutionEngine()
    f = {"field": "kategori", "operator": "!=", "value": "ticari"}
    assert engine._match(SAMPLE_DATA[0], f) is True


def test_string_exact_match():
    engine = ExecutionEngine()
    f = {"field": "musteri_adi", "operator": "=", "value": "Ali Veli"}
    assert engine._match(SAMPLE_DATA[0], f) is True
    f2 = {"field": "musteri_adi", "operator": "=", "value": "Ali"}
    assert engine._match(SAMPLE_DATA[0], f2) is False


def test_string_contains():
    engine = ExecutionEngine()
    f = {"field": "musteri_adi", "operator": "contains", "value": "ali"}
    assert engine._match(SAMPLE_DATA[0], f) is True


def test_bool_match():
    engine = ExecutionEngine()
    f = {"field": "dava_var_mi", "operator": "=", "value": True}
    assert engine._match(SAMPLE_DATA[0], f) is False
    assert engine._match(SAMPLE_DATA[1], f) is True


def test_pagination():
    engine = ExecutionEngine()
    query = MockQuery(intent="list", limit=2, offset=0)
    result = engine._list(SAMPLE_DATA, query)
    assert len(result.data) == 2
    assert result.count == 3
    assert result.has_more is True


def test_pagination_offset():
    engine = ExecutionEngine()
    query = MockQuery(intent="list", limit=2, offset=2)
    result = engine._list(SAMPLE_DATA, query)
    assert len(result.data) == 1
    assert result.count == 3
    assert result.has_more is False


def test_count():
    engine = ExecutionEngine()
    result = engine._count(SAMPLE_DATA)
    assert result.data[0]["sayi"] == 3
    assert result.count == 3


def test_sum():
    engine = ExecutionEngine()
    result = engine._sum(SAMPLE_DATA, "toplam_borc")
    assert result.data[0]["toplam"] == Decimal("65000.00")


def test_average():
    engine = ExecutionEngine()
    result = engine._average(SAMPLE_DATA, "toplam_borc")
    expected = (Decimal("65000.00") / 3).quantize(Decimal("0.01"))
    assert result.data[0]["ortalama"] == expected


def test_average_empty():
    engine = ExecutionEngine()
    result = engine._average([], "toplam_borc")
    assert result.data[0]["ortalama"] == Decimal("0")
    assert result.count == 0


def test_ratio():
    engine = ExecutionEngine()
    query = MockQuery(limit=100, offset=0)
    result = engine._ratio(SAMPLE_DATA, query)
    # Ali Veli: 7000/10000 * 100 = 70.00
    assert result.data[0]["odeme_orani"] == Decimal("70.00")
    # Mehmet Er: 5000/5000 * 100 = 100.00
    assert result.data[2]["odeme_orani"] == Decimal("100.00")


def test_general_report():
    engine = ExecutionEngine()
    query = MockQuery(
        intent="report", report_type="general",
        filters=[], limit=100, offset=0,
    )
    result = engine.execute(query, SAMPLE_DATA)
    assert result.sections["toplam_kayit"] == 3
    assert result.sections["dava_sayisi"] == 1
    assert result.sections["toplam_borc"] == Decimal("65000.00")


def test_performance_report():
    engine = ExecutionEngine()
    query = MockQuery(
        intent="report", report_type="performance",
        filters=[], limit=100, offset=0,
    )
    result = engine.execute(query, SAMPLE_DATA)
    assert "dusuk_0_30" in result.sections
    assert "en_iyi_5" in result.sections
    assert len(result.sections["en_iyi_5"]) <= 5


def test_risk_report():
    engine = ExecutionEngine()
    query = MockQuery(
        intent="report", report_type="risk",
        filters=[], limit=100, offset=0,
    )
    result = engine.execute(query, SAMPLE_DATA)
    assert result.sections["dava_sayisi"] == 1
    # Ayşe Kaya: 50000 - 10000 = 40000
    assert result.sections["toplam_risk_tutari"] == Decimal("40000.00")


def test_category_report():
    engine = ExecutionEngine()
    query = MockQuery(
        intent="report", report_type="category",
        filters=[], limit=100, offset=0,
    )
    result = engine.execute(query, SAMPLE_DATA)
    assert "konut" in result.sections
    assert "ticari" in result.sections
    assert result.sections["konut"]["kayit_sayisi"] == 2


def test_none_row_value_no_match():
    engine = ExecutionEngine()
    row = {**SAMPLE_DATA[0], "toplam_borc": None}
    f = {"field": "toplam_borc", "operator": ">", "value": "0"}
    assert engine._match(row, f) is False


def test_decimal_operators():
    engine = ExecutionEngine()
    row = SAMPLE_DATA[0]  # toplam_borc = 10000.00

    assert engine._match(row, {"field": "toplam_borc", "operator": "<", "value": "20000"}) is True
    assert engine._match(row, {"field": "toplam_borc", "operator": ">", "value": "5000"}) is True
    assert engine._match(row, {"field": "toplam_borc", "operator": "<=", "value": "10000"}) is True
    assert engine._match(row, {"field": "toplam_borc", "operator": ">=", "value": "10000"}) is True
    assert engine._match(row, {"field": "toplam_borc", "operator": "!=", "value": "5000"}) is True
