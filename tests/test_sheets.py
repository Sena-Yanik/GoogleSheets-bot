# tests/test_sheets.py
import os
import sys
from decimal import Decimal
from datetime import date
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.sheets_client import SheetsClient, DecimalEncoder


class TestSheetsClientCasting:

    def _make_client(self):
        """Ağ bağlantısı olmadan SheetsClient oluştur."""
        client = SheetsClient.__new__(SheetsClient)
        return client

    def test_decimal_cast_turkish_format(self):
        client = self._make_client()
        result = client._cast("toplam_borc", "10.000,50")
        assert result == Decimal("10000.50")

    def test_decimal_cast_simple(self):
        client = self._make_client()
        result = client._cast("toplam_borc", "5000")
        assert result == Decimal("5000")

    def test_decimal_cast_empty(self):
        client = self._make_client()
        result = client._cast("toplam_borc", "")
        assert result == Decimal("0")

    def test_decimal_cast_zero(self):
        client = self._make_client()
        result = client._cast("toplam_borc", "0")
        assert result == Decimal("0")

    def test_decimal_cast_large_number(self):
        client = self._make_client()
        result = client._cast("toplam_borc", "1.250.000,75")
        assert result == Decimal("1250000.75")

    def test_bool_cast_evet(self):
        client = self._make_client()
        assert client._cast("dava_var_mi", "evet") is True

    def test_bool_cast_hayir(self):
        client = self._make_client()
        assert client._cast("dava_var_mi", "hayır") is False

    def test_bool_cast_true(self):
        client = self._make_client()
        assert client._cast("dava_var_mi", "true") is True

    def test_bool_cast_false(self):
        client = self._make_client()
        assert client._cast("dava_var_mi", "false") is False

    def test_bool_cast_yes(self):
        client = self._make_client()
        assert client._cast("dava_var_mi", "yes") is True

    def test_bool_cast_one(self):
        client = self._make_client()
        assert client._cast("dava_var_mi", "1") is True

    def test_date_cast(self):
        client = self._make_client()
        result = client._cast("kayit_tarihi", "15.01.2024")
        assert result == date(2024, 1, 15)

    def test_date_cast_empty(self):
        client = self._make_client()
        result = client._cast("kayit_tarihi", "")
        assert result is None

    def test_date_cast_invalid(self):
        client = self._make_client()
        result = client._cast("kayit_tarihi", "geçersiz")
        assert result is None

    def test_string_cast(self):
        client = self._make_client()
        result = client._cast("musteri_adi", "  Ali Veli  ")
        assert result == "Ali Veli"

    def test_string_cast_empty(self):
        client = self._make_client()
        result = client._cast("musteri_adi", "")
        assert result == ""

    def test_string_cast_none(self):
        client = self._make_client()
        result = client._cast("musteri_adi", None)
        assert result == ""


class TestSheetsClientValidation:

    def _make_client(self):
        client = SheetsClient.__new__(SheetsClient)
        return client

    def test_valid_row(self):
        client = self._make_client()
        row = {
            "musteri_adi": "Ali Veli",
            "toplam_borc": Decimal("10000"),
            "odenen_tutar": Decimal("5000"),
        }
        assert client._is_valid_row(row) is True

    def test_empty_name_rejected(self):
        client = self._make_client()
        row = {
            "musteri_adi": "",
            "toplam_borc": Decimal("10000"),
            "odenen_tutar": Decimal("5000"),
        }
        assert client._is_valid_row(row) is False

    def test_zero_borc_rejected(self):
        client = self._make_client()
        row = {
            "musteri_adi": "Test",
            "toplam_borc": Decimal("0"),
            "odenen_tutar": Decimal("5000"),
        }
        assert client._is_valid_row(row) is False

    def test_none_field_rejected(self):
        client = self._make_client()
        row = {
            "musteri_adi": "Test",
            "toplam_borc": None,
            "odenen_tutar": Decimal("5000"),
        }
        assert client._is_valid_row(row) is False


class TestDecimalEncoder:

    def test_decimal_encoding(self):
        import json
        data = {"amount": Decimal("1234.56")}
        result = json.dumps(data, cls=DecimalEncoder)
        assert '"1234.56"' in result

    def test_date_encoding(self):
        import json
        data = {"date": date(2024, 1, 15)}
        result = json.dumps(data, cls=DecimalEncoder)
        assert '"2024-01-15"' in result
