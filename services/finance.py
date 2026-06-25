import re
from datetime import datetime


def parse_money(value):
    if not value:
        return 0

    normalized = value.replace(" ", "").replace("\u00a0", "").replace(",", ".")
    match = re.search(r"-?\d+(?:\.\d+)?", normalized)
    if not match:
        return 0

    return int(float(match.group(0)))


def _find_money(text, label):
    pattern = rf"-\s*{re.escape(label)}\s*-\s*([^\n]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    return parse_money(match.group(1)) if match else 0


def _find_text(text, label):
    pattern = rf"{re.escape(label)}:\s*([^\n]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def parse_finance_report(text):
    if "Итого за смену" not in text:
        return None

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return None

    date_match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})\s+(День|Ночь)", text)
    if not date_match:
        return None

    day, month, year, shift_type = date_match.groups()
    report_date = datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")

    return {
        "employees": lines[0],
        "report_date": report_date,
        "shift_type": shift_type,
        "total": _find_money(text, "Итого за смену"),
        "total_lg": _find_money(text, "C учетом заказов с LG"),
        "cashless": _find_money(text, "Безнал"),
        "cash": _find_money(text, "Общий нал"),
        "acquiring": _find_money(text, "Эквайринг"),
        "sbp": _find_money(text, "СБП"),
        "bar_total": _find_money(text, "Общий бар"),
        "ps_total": _find_money(text, "Пополнение счета/PS"),
        "hookah_total": _find_money(text, "Кальяны"),
        "cork_total": _find_money(text, "Пробковый сбор"),
        "refunds": _find_money(text, "Возвраты"),
        "cashbox_change": _find_money(text, "Размен в кассе"),
        "bonuses": _find_money(text, "Бонусы/компенсация"),
        "expenses_text": re.search(r"-\s*Расходы\s*-\s*([^\n]*)", text).group(1).strip()
        if re.search(r"-\s*Расходы\s*-\s*([^\n]*)", text)
        else "",
        "closed_by": _find_text(text, "Смену закрыл"),
        "accepted_by": _find_text(text, "Смену приняли"),
        "raw_text": text,
    }


def money(value):
    return f"{value:,}".replace(",", " ")
