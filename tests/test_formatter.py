# tests/test_formatter.py
import os
import sys
from decimal import Decimal
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.formatter import ResponseFormatter, _escape_md, _format_decimal
from engine.execution_engine import ExecutionResult


class TestEscapeMd:

    def test_special_characters(self):
        assert _escape_md("test_value") == "test\\_value"
        assert _escape_md("test*bold*") == "test\\*bold\\*"
        assert _escape_md("100.00") == "100\\.00"

    def test_plain_text(self):
        assert _escape_md("hello") == "hello"

    def test_empty_string(self):
        assert _escape_md("") == ""

    def test_multiple_special_chars(self):
        result = _escape_md("[test](link)")
        assert "\\[" in result
        assert "\\]" in result
        assert "\\(" in result
        assert "\\)" in result


class TestFormatDecimal:

    def test_simple_number(self):
        result = _format_decimal(Decimal("1000"))
        assert result == "1.000,00"

    def test_large_number(self):
        result = _format_decimal(Decimal("1250000.75"))
        assert result == "1.250.000,75"

    def test_zero(self):
        result = _format_decimal(Decimal("0"))
        assert result == "0,00"

    def test_small_number(self):
        result = _format_decimal(Decimal("50.5"))
        assert result == "50,50"

    def test_negative_number(self):
        result = _format_decimal(Decimal("-1500"))
        assert result == "-1.500,00"

    def test_none_value(self):
        result = _format_decimal(None)
        assert result == "0"


class TestResponseFormatter:

    def setup_method(self):
        self.formatter = ResponseFormatter()

    def test_empty_result(self):
        result = ExecutionResult(data=[], count=0)
        output = self.formatter.format(result)
        assert "Sonuç bulunamadı" in output

    def test_single_aggregation(self):
        result = ExecutionResult(
            data=[{"sayi": 42}],
            count=42,
        )
        output = self.formatter.format(result)
        assert "42" in output
        assert "Sayi" in output

    def test_decimal_aggregation(self):
        result = ExecutionResult(
            data=[{"toplam": Decimal("65000.00")}],
            count=3,
        )
        output = self.formatter.format(result)
        assert "65\\.000,00" in output

    def test_list_result(self):
        result = ExecutionResult(
            data=[
                {"musteri_adi": "Ali Veli", "toplam_borc": Decimal("10000")},
                {"musteri_adi": "Ayşe Kaya", "toplam_borc": Decimal("50000")},
            ],
            count=2,
            has_more=False,
        )
        output = self.formatter.format(result)
        assert "Sonuçlar" in output
        assert "2 kayıt" in output
        assert "Ali Veli" in output

    def test_list_with_has_more(self):
        result = ExecutionResult(
            data=[
                {"musteri_adi": "Ali", "toplam_borc": Decimal("10000"), "kategori": "konut"},
            ],
            count=5,
            has_more=True,
        )
        output = self.formatter.format(result)
        assert "Daha fazla" in output

    def test_boolean_formatting(self):
        result = ExecutionResult(
            data=[
                {"musteri_adi": "Test", "dava_var_mi": True, "aktif": False},
            ],
            count=1,
            has_more=False,
        )
        output = self.formatter.format(result)
        assert "Evet" in output
        assert "Hayır" in output

    def test_report_format(self):
        result = ExecutionResult(
            sections={
                "toplam_kayit": 100,
                "toplam_borc": Decimal("500000.00"),
                "dava_sayisi": 5,
            }
        )
        output = self.formatter.format(result)
        assert "Rapor" in output
        assert "100" in output
        assert "500\\.000,00" in output

    def test_report_with_list_section(self):
        result = ExecutionResult(
            sections={
                "en_iyi_5": [
                    {"musteri_adi": "Ali", "odeme_orani": Decimal("95.00")},
                    {"musteri_adi": "Veli", "odeme_orani": Decimal("90.00")},
                ],
            }
        )
        output = self.formatter.format(result)
        assert "Ali" in output
        assert "Veli" in output

    def test_report_with_nested_dict(self):
        result = ExecutionResult(
            sections={
                "konut": {
                    "kayit_sayisi": 2,
                    "toplam_borc": Decimal("15000.00"),
                },
            }
        )
        output = self.formatter.format(result)
        # Formatter title-cases and escapes the key
        assert "Konut" in output
        assert "15000" in output

    def test_none_values_skipped(self):
        result = ExecutionResult(
            data=[
                {"musteri_adi": "Test", "kayit_tarihi": None, "kategori": "konut"},
            ],
            count=1,
            has_more=False,
        )
        output = self.formatter.format(result)
        assert "Test" in output
        assert "konut" in output
