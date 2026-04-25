# engine/report_engine.py
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from engine.execution_engine import ExecutionResult


class ReportEngine:
    """Rapor üretim motoru - genel, performans, risk, kategori raporları."""

    def generate(self, report_type: str, data: list[dict]) -> ExecutionResult:
        """Rapor tipine göre uygun raporu üret."""
        match report_type:
            case "general":
                return self._general(data)
            case "performance":
                return self._performance(data)
            case "risk":
                return self._risk(data)
            case "category":
                return self._category(data)
            case _:
                return ExecutionResult()

    def _calc_ratio(self, row: dict) -> Decimal:
        """Tek bir satır için ödeme oranı hesapla."""
        borc = row.get("toplam_borc") or Decimal("0")
        odenen = row.get("odenen_tutar") or Decimal("0")
        if borc <= Decimal("0"):
            return Decimal("0")
        return (odenen / borc * 100).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )

    def _general(self, data: list[dict]) -> ExecutionResult:
        """Genel rapor - özet istatistikler."""
        total = len(data)
        toplam_borc = sum(
            r.get("toplam_borc") or Decimal("0") for r in data
        )
        odenen = sum(
            r.get("odenen_tutar") or Decimal("0") for r in data
        )
        dava = sum(1 for r in data if r.get("dava_var_mi"))
        oranlar = [self._calc_ratio(r) for r in data]
        avg_oran = (
            (sum(oranlar) / len(oranlar)).quantize(
                Decimal("0.01"), ROUND_HALF_UP
            )
            if oranlar
            else Decimal("0")
        )

        return ExecutionResult(sections={
            "toplam_kayit": total,
            "toplam_borc": toplam_borc.quantize(
                Decimal("0.01"), ROUND_HALF_UP
            ),
            "toplam_odenen": odenen.quantize(
                Decimal("0.01"), ROUND_HALF_UP
            ),
            "ortalama_odeme_orani": avg_oran,
            "dava_sayisi": dava,
            "yuzde_30_alti": sum(
                1 for o in oranlar if o < Decimal("30")
            ),
            "yuzde_70_ustu": sum(
                1 for o in oranlar if o >= Decimal("70")
            ),
        })

    def _performance(self, data: list[dict]) -> ExecutionResult:
        """Performans raporu - ödeme oranı dağılımı ve en iyi 5."""
        with_ratio = [
            {**r, "odeme_orani": self._calc_ratio(r)} for r in data
        ]
        return ExecutionResult(sections={
            "dusuk_0_30": sum(
                1 for r in with_ratio
                if r["odeme_orani"] < Decimal("30")
            ),
            "orta_30_70": sum(
                1 for r in with_ratio
                if Decimal("30") <= r["odeme_orani"] < Decimal("70")
            ),
            "iyi_70_100": sum(
                1 for r in with_ratio
                if r["odeme_orani"] >= Decimal("70")
            ),
            "en_iyi_5": [
                {
                    "musteri_adi": r["musteri_adi"],
                    "odeme_orani": r["odeme_orani"],
                }
                for r in sorted(
                    with_ratio,
                    key=lambda r: r["odeme_orani"],
                    reverse=True,
                )[:5]
            ],
        })

    def _risk(self, data: list[dict]) -> ExecutionResult:
        """Risk raporu - davalar ve düşük ödeme oranları."""
        dava = [r for r in data if r.get("dava_var_mi")]
        dusuk = [
            r for r in data if self._calc_ratio(r) < Decimal("30")
        ]
        risk_tutari = sum(
            (r.get("toplam_borc") or Decimal("0"))
            - (r.get("odenen_tutar") or Decimal("0"))
            for r in dava
        )
        return ExecutionResult(sections={
            "dava_sayisi": len(dava),
            "dusuk_odeme_sayisi": len(dusuk),
            "toplam_risk_tutari": risk_tutari.quantize(
                Decimal("0.01"), ROUND_HALF_UP
            ),
        })

    def _category(self, data: list[dict]) -> ExecutionResult:
        """Kategori raporu - kategoriye göre gruplandırılmış istatistikler."""
        groups: dict[str, list] = defaultdict(list)
        for r in data:
            groups[r.get("kategori") or "Belirtilmemiş"].append(r)
        result = {}
        for cat, rows in groups.items():
            oranlar = [self._calc_ratio(r) for r in rows]
            result[cat] = {
                "kayit_sayisi": len(rows),
                "toplam_borc": sum(
                    r.get("toplam_borc") or Decimal("0") for r in rows
                ).quantize(Decimal("0.01"), ROUND_HALF_UP),
                "ortalama_odeme_orani": (
                    (sum(oranlar) / len(oranlar)).quantize(
                        Decimal("0.01"), ROUND_HALF_UP
                    )
                    if oranlar
                    else Decimal("0")
                ),
            }
        return ExecutionResult(sections=result)
