from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from database import conn, cursor
from keyboards import finance_empty_kb, finance_report_kb, main_menu
from services.finance import money, parse_finance_report
from utils import check_employee, has_access

router = Router()


def _message_report_text(message: Message):
    return message.text or message.caption or ""


def _save_report(message: Message, data):
    cursor.execute(
        """
        INSERT OR REPLACE INTO finance_reports(
            chat_id, message_id, employees, report_date, shift_type,
            total, total_lg, cashless, cash, acquiring, sbp,
            bar_total, ps_total, hookah_total, cork_total,
            refunds, cashbox_change, bonuses, expenses_text,
            closed_by, accepted_by, raw_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            message.chat.id,
            message.message_id,
            data["employees"],
            data["report_date"],
            data["shift_type"],
            data["total"],
            data["total_lg"],
            data["cashless"],
            data["cash"],
            data["acquiring"],
            data["sbp"],
            data["bar_total"],
            data["ps_total"],
            data["hookah_total"],
            data["cork_total"],
            data["refunds"],
            data["cashbox_change"],
            data["bonuses"],
            data["expenses_text"],
            data["closed_by"],
            data["accepted_by"],
            data["raw_text"],
        ),
    )
    conn.commit()


def _report_row(report_id=None, direction=None):
    if report_id is None:
        cursor.execute(
            """
            SELECT id, report_date, shift_type, employees, total, cashless, cash,
                   acquiring, sbp, bar_total, ps_total, hookah_total, cork_total,
                   refunds, cashbox_change, bonuses, expenses_text, closed_by, accepted_by
            FROM finance_reports
            ORDER BY report_date DESC, id DESC
            LIMIT 1
            """
        )
        return cursor.fetchone()

    if direction == "prev":
        cursor.execute(
            """
            SELECT id, report_date, shift_type, employees, total, cashless, cash,
                   acquiring, sbp, bar_total, ps_total, hookah_total, cork_total,
                   refunds, cashbox_change, bonuses, expenses_text, closed_by, accepted_by
            FROM finance_reports
            WHERE id < ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (report_id,),
        )
        return cursor.fetchone()

    if direction == "next":
        cursor.execute(
            """
            SELECT id, report_date, shift_type, employees, total, cashless, cash,
                   acquiring, sbp, bar_total, ps_total, hookah_total, cork_total,
                   refunds, cashbox_change, bonuses, expenses_text, closed_by, accepted_by
            FROM finance_reports
            WHERE id > ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (report_id,),
        )
        return cursor.fetchone()

    return None


def _employee_shift_text():
    cursor.execute("SELECT id FROM shifts WHERE status='open' ORDER BY id DESC LIMIT 1")
    shift = cursor.fetchone()
    if not shift:
        return "Сейчас нет активной смены."

    cursor.execute("SELECT employee_id FROM shift_employees WHERE shift_id=?", (shift[0],))
    employees = cursor.fetchall()
    if not employees:
        return "В смене пока нет сотрудников."

    text = "Сотрудники в смене:\n"
    for (emp_id,) in employees:
        cursor.execute("SELECT name FROM employees WHERE id=?", (emp_id,))
        emp = cursor.fetchone()
        name = emp[0] if emp else f"ID {emp_id}"
        cursor.execute(
            "SELECT COUNT(*) FROM orders WHERE employee_id=? AND status='closed'",
            (emp_id,),
        )
        count = cursor.fetchone()[0]
        text += f"• {name}: {count} кальянов\n"

    return text


def _report_text(row):
    if not row:
        return "📊 Статистика смены\n\nФинансовых отчетов пока нет."

    (
        report_id,
        report_date,
        shift_type,
        employees,
        total,
        cashless,
        cash,
        acquiring,
        sbp,
        bar_total,
        ps_total,
        hookah_total,
        cork_total,
        refunds,
        cashbox_change,
        bonuses,
        expenses_text,
        closed_by,
        accepted_by,
    ) = row

    return (
        "📊 Статистика смены\n\n"
        f"{_employee_shift_text()}\n\n"
        "💰 Финансовый отчет\n"
        f"Дата: {report_date} {shift_type}\n"
        f"Сотрудники: {employees}\n"
        f"Итого: {money(total)}\n"
        f"Безнал: {money(cashless)} | Нал: {money(cash)}\n"
        f"Эквайринг: {money(acquiring)} | СБП: {money(sbp)}\n"
        f"Бар: {money(bar_total)}\n"
        f"Пополнение счета/PS: {money(ps_total)}\n"
        f"Кальяны: {money(hookah_total)}\n"
        f"Пробковый сбор: {money(cork_total)}\n"
        f"Возвраты: {money(refunds)}\n"
        f"Размен в кассе: {money(cashbox_change)}\n"
        f"Бонусы/компенсация: {money(bonuses)}\n"
        f"Расходы: {expenses_text or '-'}\n"
        f"Закрыл: {closed_by or '-'}\n"
        f"Приняли: {accepted_by or '-'}"
    )


def _month_text(month):
    cursor.execute(
        """
        SELECT COUNT(*), SUM(total), SUM(cashless), SUM(cash), SUM(acquiring),
               SUM(sbp), SUM(bar_total), SUM(ps_total), SUM(hookah_total),
               SUM(cork_total), SUM(refunds), SUM(bonuses)
        FROM finance_reports
        WHERE substr(report_date, 1, 7)=?
        """,
        (month,),
    )
    row = cursor.fetchone()

    if not row or not row[0]:
        return f"📆 Общая статистика за {month}\n\nОтчетов пока нет."

    (
        count,
        total,
        cashless,
        cash,
        acquiring,
        sbp,
        bar_total,
        ps_total,
        hookah_total,
        cork_total,
        refunds,
        bonuses,
    ) = row

    return (
        f"📆 Общая статистика за {month}\n\n"
        f"Отчетов: {count}\n"
        f"Итого: {money(total or 0)}\n"
        f"Безнал: {money(cashless or 0)} | Нал: {money(cash or 0)}\n"
        f"Эквайринг: {money(acquiring or 0)} | СБП: {money(sbp or 0)}\n"
        f"Бар: {money(bar_total or 0)}\n"
        f"Пополнение счета/PS: {money(ps_total or 0)}\n"
        f"Кальяны: {money(hookah_total or 0)}\n"
        f"Пробковый сбор: {money(cork_total or 0)}\n"
        f"Возвраты: {money(refunds or 0)}\n"
        f"Бонусы/компенсация: {money(bonuses or 0)}"
    )


def _report_markup(row):
    if not row:
        return finance_empty_kb()

    report_id = row[0]
    month = row[1][:7]
    return finance_report_kb(report_id, month)


@router.message(lambda m: (m.text or m.caption) and "Итого за смену" in (m.text or m.caption))
async def collect_finance_report(message: Message):
    data = parse_finance_report(_message_report_text(message))
    if not data:
        return

    _save_report(message, data)


@router.message(lambda m: m.text == "/parse_finance")
async def parse_finance_reply(message: Message):
    if not has_access(message.from_user.id):
        return

    if not message.reply_to_message:
        await message.answer("Ответь этой командой на сообщение с финансовым отчетом.")
        return

    report_text = _message_report_text(message.reply_to_message)
    data = parse_finance_report(report_text)
    if not data:
        await message.answer("Не смог распознать финансовый отчет в этом сообщении.")
        return

    _save_report(message.reply_to_message, data)
    await message.answer("Финансовый отчет сохранен.")


@router.callback_query(F.data == "shift_stats")
async def shift_stats(call: CallbackQuery):
    if not await check_employee(call):
        return

    row = _report_row()
    await call.message.edit_text(_report_text(row), reply_markup=_report_markup(row))
    await call.answer()


@router.callback_query(F.data.startswith("finance_prev_"))
async def finance_prev(call: CallbackQuery):
    if not await check_employee(call):
        return

    current_id = int(call.data.removeprefix("finance_prev_"))
    row = _report_row(current_id, "prev")
    if not row:
        await call.answer("Это самый старый отчет", show_alert=True)
        return

    await call.message.edit_text(_report_text(row), reply_markup=_report_markup(row))
    await call.answer()


@router.callback_query(F.data.startswith("finance_next_"))
async def finance_next(call: CallbackQuery):
    if not await check_employee(call):
        return

    current_id = int(call.data.removeprefix("finance_next_"))
    row = _report_row(current_id, "next")
    if not row:
        await call.answer("Это самый новый отчет", show_alert=True)
        return

    await call.message.edit_text(_report_text(row), reply_markup=_report_markup(row))
    await call.answer()


@router.callback_query(F.data.startswith("finance_month_"))
async def finance_month(call: CallbackQuery):
    if not await check_employee(call):
        return

    month = call.data.removeprefix("finance_month_")
    await call.message.edit_text(_month_text(month), reply_markup=finance_empty_kb())
    await call.answer()


@router.message(lambda m: m.text == "/shift_stats")
async def shift_stats_cmd(message: Message):
    if not has_access(message.from_user.id):
        return

    row = _report_row()
    await message.answer(_report_text(row), reply_markup=_report_markup(row))
