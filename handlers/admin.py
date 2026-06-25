from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_ID
from database import conn, cursor, get_plan, set_plan
from keyboards import main_menu, request_access_menu
from utils import has_access

router = Router()


# ── helpers ──────────────────────────────────────────────────────────────────

def _money(v: int) -> str:
    return f"{v:,}".replace(",", "\u202f") + " ₽"


def _cur_month() -> str:
    return datetime.now().strftime("%Y-%m")


def _month_label(m: str) -> str:
    """'2026-06' → 'Июнь 2026'"""
    months_ru = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
    ]
    y, mo = m.split("-")
    return f"{months_ru[int(mo) - 1]} {y}"


def _plan_text(month: str) -> str:
    plan = get_plan(month)

    cursor.execute(
        """
        SELECT COALESCE(SUM(total), 0), COALESCE(SUM(bar_total), 0)
        FROM finance_reports
        WHERE substr(report_date, 1, 7) = ?
        """,
        (month,),
    )
    row = cursor.fetchone()
    total, bar = row[0], row[1]

    label = _month_label(month)
    lines = [f"📆 {label}\n"]
    lines.append(f"💰 Итого: {_money(total)}")
    lines.append(f"🍺 Бар:   {_money(bar)}")

    if plan:
        pct = round(total / plan * 100) if plan else 0
        bar_blocks = round(pct / 10)
        progress = "█" * bar_blocks + "░" * (10 - bar_blocks)
        lines.append(f"\n🎯 План: {_money(plan)}")
        lines.append(f"[{progress}] {pct}%")
        left = plan - total
        if left > 0:
            lines.append(f"До плана: {_money(left)}")
        else:
            lines.append("✅ План выполнен!")
    else:
        lines.append("\nПлан на месяц не установлен.")
        lines.append("Установи: /setplan 500000")

    return "\n".join(lines)


def _top_text(month: str) -> str:
    """Топ сотрудников по общей выручке и по бару за месяц."""
    label = _month_label(month)

    # Разбиваем поле employees (строка вида "Имя1, Имя2") на отдельных людей.
    # Считаем каждую запись как вклад КАЖДОГО упомянутого сотрудника
    # (делим выручку поровну между ними в смене).
    cursor.execute(
        """
        SELECT employees, total, bar_total
        FROM finance_reports
        WHERE substr(report_date, 1, 7) = ?
        """,
        (month,),
    )
    rows = cursor.fetchall()

    if not rows:
        return f"📊 Топ сотрудников — {label}\n\nОтчётов за этот месяц нет."

    totals: dict[str, int] = {}
    bars: dict[str, int] = {}

    for employees_str, total, bar in rows:
        names = [n.strip() for n in (employees_str or "").split(",") if n.strip()]
        if not names:
            continue
        share_total = (total or 0) // len(names)
        share_bar = (bar or 0) // len(names)
        for name in names:
            # Убираем эмодзи-префиксы вроде "😋 Михаил" → "Михаил"
            clean = name.strip()
            if clean and not clean[0].isalpha():
                parts = clean.split(maxsplit=1)
                clean = parts[1] if len(parts) > 1 else clean
            totals[clean] = totals.get(clean, 0) + share_total
            bars[clean] = bars.get(clean, 0) + share_bar

    medals = ["🥇", "🥈", "🥉"]

    def rank_block(title: str, data: dict[str, int]) -> str:
        ranked = sorted(data.items(), key=lambda x: x[1], reverse=True)
        lines = [title]
        for i, (name, val) in enumerate(ranked):
            icon = medals[i] if i < 3 else f"{i+1}."
            lines.append(f"{icon} {name} — {_money(val)}")
        return "\n".join(lines)

    return (
        f"📊 Топ сотрудников — {label}\n\n"
        + rank_block("💰 По общей выручке:", totals)
        + "\n\n"
        + rank_block("🍺 По бару:", bars)
    )


# ── handlers ─────────────────────────────────────────────────────────────────

@router.message(F.text.in_({"/start", "/menu"}))
async def start(message: Message, state: FSMContext):
    await state.clear()
    if not has_access(message.from_user.id):
        await message.answer(
            "Доступа к боту пока нет. Отправь заявку администратору.",
            reply_markup=request_access_menu(),
        )
        return
    await message.answer("Hookah CRM", reply_markup=main_menu())


@router.message(F.text == "/requests")
async def requests_cmd(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute(
        "SELECT id, tg_id, name FROM employee_requests WHERE status='pending'"
    )
    rows = cursor.fetchall()

    if not rows:
        await message.answer("Нет заявок", reply_markup=main_menu())
        return

    for req_id, tg_id, name in rows:
        await message.answer(
            f"{name} ({tg_id})",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{req_id}"),
                        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{req_id}"),
                    ],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
                ]
            ),
        )


@router.message(lambda m: m.text and m.text.startswith("/topic_id"))
async def topic_id(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer(
            f"Команда доступна только админу.\n"
            f"Твой TG ID: {message.from_user.id}\n"
            f"ADMIN_ID в настройках: {ADMIN_ID}"
        )
        return
    await message.answer(
        f"chat_id: {message.chat.id}\n"
        f"message_thread_id: {message.message_thread_id or 0}"
    )


@router.message(lambda m: m.text and m.text.startswith("/setplan"))
async def setplan(message: Message):
    """
    /setplan 500000          — план на текущий месяц
    /setplan 2026-07 500000  — план на конкретный месяц
    """
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.strip().split()
    # parts[0] = "/setplan"
    try:
        if len(parts) == 2:
            # /setplan 500000
            month = _cur_month()
            plan = int(parts[1])
        elif len(parts) == 3:
            # /setplan 2026-07 500000
            month = parts[1]
            datetime.strptime(month, "%Y-%m")  # валидация
            plan = int(parts[2])
        else:
            raise ValueError
        if plan <= 0:
            raise ValueError
    except (ValueError, IndexError):
        await message.answer(
            "Неверный формат.\n"
            "Примеры:\n"
            "/setplan 500000\n"
            "/setplan 2026-07 500000"
        )
        return

    set_plan(month, plan, message.from_user.id)
    await message.answer(
        f"✅ План на {_month_label(month)} установлен: {_money(plan)}"
    )


@router.message(lambda m: m.text and m.text.startswith("/plan"))
async def plan_cmd(message: Message):
    """Показывает прогресс плана за текущий (или указанный) месяц."""
    if not has_access(message.from_user.id):
        return

    parts = message.text.strip().split()
    month = parts[1] if len(parts) == 2 else _cur_month()
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        await message.answer("Формат месяца: YYYY-MM, например 2026-06")
        return

    await message.answer(_plan_text(month), reply_markup=main_menu())


@router.message(lambda m: m.text and m.text.startswith("/top"))
async def top_cmd(message: Message):
    """
    /top          — топ за текущий месяц
    /top 2026-06  — топ за конкретный месяц
    """
    if not has_access(message.from_user.id):
        return

    parts = message.text.strip().split()
    month = parts[1] if len(parts) == 2 else _cur_month()
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        await message.answer("Формат месяца: YYYY-MM, например 2026-06")
        return

    await message.answer(_top_text(month), reply_markup=main_menu())


# ── callbacks ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("approve_"))
async def approve(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Доступно только админу", show_alert=True)
        return

    req_id = int(call.data.split("_", 1)[1])
    cursor.execute("SELECT tg_id, name FROM employee_requests WHERE id=?", (req_id,))
    request = cursor.fetchone()

    if not request:
        await call.answer("Заявка не найдена", show_alert=True)
        return

    tg_id, name = request
    cursor.execute("SELECT id FROM employees WHERE tg_id=?", (tg_id,))
    if cursor.fetchone():
        cursor.execute("UPDATE employee_requests SET status='approved' WHERE id=?", (req_id,))
        conn.commit()
        await call.answer("Уже одобрен", show_alert=True)
        return

    cursor.execute(
        "INSERT INTO employees (tg_id, name, active) VALUES (?, ?, 1)",
        (tg_id, name),
    )
    cursor.execute("UPDATE employee_requests SET status='approved' WHERE id=?", (req_id,))
    conn.commit()
    await call.answer("Одобрено", show_alert=True)


@router.callback_query(F.data.startswith("reject_"))
async def reject(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Доступно только админу", show_alert=True)
        return

    req_id = int(call.data.split("_", 1)[1])
    cursor.execute("UPDATE employee_requests SET status='rejected' WHERE id=?", (req_id,))
    conn.commit()
    await call.answer("Отклонено", show_alert=True)
