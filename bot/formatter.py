# bot/formatter.py
from decimal import Decimal
from engine.execution_engine import ExecutionResult


def _escape_md(text: str) -> str:
    """MarkdownV2 için özel karakterleri escape et."""
    special_chars = r"_*[]()~`>#+-=|{}.!"
    result = []
    for char in str(text):
        if char in special_chars:
            result.append(f"\\{char}")
        else:
            result.append(char)
    return "".join(result)


def _format_decimal(value: Decimal) -> str:
    """Decimal değeri Türkçe formatla: 10.000,50"""
    if value is None:
        return "0"
    # Ondalık kısım
    str_val = str(value.quantize(Decimal("0.01")))
    parts = str_val.split(".")
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else "00"

    # Negatif sayı kontrolü
    negative = integer_part.startswith("-")
    if negative:
        integer_part = integer_part[1:]

    # Binlik ayracı
    groups = []
    while len(integer_part) > 3:
        groups.insert(0, integer_part[-3:])
        integer_part = integer_part[:-3]
    groups.insert(0, integer_part)
    formatted = ".".join(groups)

    if negative:
        formatted = "-" + formatted
    return f"{formatted},{decimal_part}"


class ResponseFormatter:
    """Telegram MarkdownV2 formatında yanıt üretici."""

    def format(self, result: ExecutionResult, query=None) -> str:
        """ExecutionResult'ı MarkdownV2 formatına dönüştür."""
        if result.sections:
            return self._format_report(result)
        if not result.data:
            return _escape_md("Sonuç bulunamadı.")
        return self._format_data(result, query)

    def _format_report(self, result: ExecutionResult) -> str:
        """Rapor sonuçlarını formatla."""
        lines = [f"*📊 Rapor*\n"]
        for key, value in result.sections.items():
            label = _escape_md(key.replace("_", " ").title())
            if isinstance(value, Decimal):
                formatted = _escape_md(_format_decimal(value))
                lines.append(f"▪️ {label}: *{formatted}*")
            elif isinstance(value, list):
                lines.append(f"\n*{label}:*")
                for item in value:
                    if isinstance(item, dict):
                        parts = []
                        for k, v in item.items():
                            if isinstance(v, Decimal):
                                parts.append(
                                    f"{_escape_md(k)}: {_escape_md(_format_decimal(v))}"
                                )
                            else:
                                parts.append(
                                    f"{_escape_md(k)}: {_escape_md(str(v))}"
                                )
                        separator = r" \| "
                        lines.append(f"  • {separator.join(parts)}")
            elif isinstance(value, dict):
                lines.append(f"\n*{label}:*")
                for sub_key, sub_val in value.items():
                    if isinstance(sub_val, dict):
                        lines.append(f"  📁 *{_escape_md(sub_key)}*")
                        for sk, sv in sub_val.items():
                            sl = _escape_md(sk.replace("_", " ").title())
                            if isinstance(sv, Decimal):
                                lines.append(
                                    f"    ▪️ {sl}: {_escape_md(_format_decimal(sv))}"
                                )
                            else:
                                lines.append(
                                    f"    ▪️ {sl}: {_escape_md(str(sv))}"
                                )
                    else:
                        lines.append(
                            f"  ▪️ {_escape_md(sub_key)}: {_escape_md(str(sub_val))}"
                        )
            else:
                lines.append(f"▪️ {label}: *{_escape_md(str(value))}*")
        return "\n".join(lines)

    def _format_data(self, result: ExecutionResult, query=None) -> str:
        """Veri listesini formatla."""
        lines = []

        # Tek sonuç - aggregation sonucu
        if len(result.data) == 1 and len(result.data[0]) <= 2:
            for key, value in result.data[0].items():
                label = _escape_md(key.replace("_", " ").title())
                if isinstance(value, Decimal):
                    formatted = _escape_md(_format_decimal(value))
                    lines.append(f"*{label}*: {formatted}")
                else:
                    lines.append(f"*{label}*: {_escape_md(str(value))}")
            return "\n".join(lines)

        # Çoklu sonuç - liste
        lines.append(
            f"*📋 Sonuçlar* \\({_escape_md(str(result.count))} kayıt\\)\n"
        )
        for i, row in enumerate(result.data, 1):
            row_lines = [f"*{_escape_md(str(i))}\\.*"]
            for key, value in row.items():
                label = _escape_md(key.replace("_", " ").title())
                if isinstance(value, Decimal):
                    formatted = _escape_md(_format_decimal(value))
                    row_lines.append(f"  {label}: {formatted}")
                elif isinstance(value, bool):
                    row_lines.append(
                        f"  {label}: {_escape_md('Evet' if value else 'Hayır')}"
                    )
                elif value is not None:
                    row_lines.append(
                        f"  {label}: {_escape_md(str(value))}"
                    )
            lines.append("\n".join(row_lines))

        if result.has_more:
            lines.append(
                f"\n_{_escape_md('Daha fazla sonuç var...')}_"
            )

        return "\n\n".join(lines)
