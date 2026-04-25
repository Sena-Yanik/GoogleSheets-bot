# tests/conftest.py
import sys
import os
from decimal import Decimal
import pytest

# Proje kök dizinini sys.path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SAMPLE_DATA = [
    {
        "id": "1",
        "musteri_adi": "Ali Veli",
        "musteri_turu": "bireysel",
        "toplam_borc": Decimal("10000.00"),
        "odenen_tutar": Decimal("7000.00"),
        "dava_var_mi": False,
        "kayit_tarihi": None,
        "kategori": "konut",
    },
    {
        "id": "2",
        "musteri_adi": "Ayşe Kaya",
        "musteri_turu": "kurumsal",
        "toplam_borc": Decimal("50000.00"),
        "odenen_tutar": Decimal("10000.00"),
        "dava_var_mi": True,
        "kayit_tarihi": None,
        "kategori": "ticari",
    },
    {
        "id": "3",
        "musteri_adi": "Mehmet Er",
        "musteri_turu": "bireysel",
        "toplam_borc": Decimal("5000.00"),
        "odenen_tutar": Decimal("5000.00"),
        "dava_var_mi": False,
        "kayit_tarihi": None,
        "kategori": "konut",
    },
]
