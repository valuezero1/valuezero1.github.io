from datetime import datetime

from aiogram import Router
from aiogram.types import Message

from database import conn, cursor
from keyboards import main_menu
from utils import has_access

router = Router()


@router.message(lambda m: m.text == "/open_shift")
async def open_shift_hint(message: Message):
    if not has_access(message.from_user.id):
        return

    await message.answer("Открой смену через кнопку в меню смены.", reply_markup=main_menu())


@router.message(lambda m: m.text == "/close_shift")
async def close_shift(message: Message):
    if not has_access(message.from_user.id):
        return

    cursor.execute("SELECT id FROM shifts WHERE status='open' ORDER BY id DESC LIMIT 1")
    shift = cursor.fetchone()

    if not shift:
        await message.answer("Нет открытой смены", reply_markup=main_menu())
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "UPDATE shifts SET closed_at=?, status='closed' WHERE id=?",
        (now, shift[0]),
    )
    conn.commit()

    await message.answer(f"Смена закрыта\nID: {shift[0]}", reply_markup=main_menu())


@router.message(lambda m: m.text == "/shift")
async def shift_status(message: Message):
    if not has_access(message.from_user.id):
        return

    cursor.execute(
        """
        SELECT id, opened_at FROM shifts
        WHERE status='open'
        ORDER BY id DESC LIMIT 1
        """
    )
    shift = cursor.fetchone()

    if not shift:
        await message.answer("Сейчас нет активной смены", reply_markup=main_menu())
        return

    await message.answer(
        f"Активная смена\nID: {shift[0]}\nСтарт: {shift[1]}",
        reply_markup=main_menu(),
    )


@router.message(lambda m: m.text == "/shift_stats")
async def shift_stats(message: Message):
    if not has_access(message.from_user.id):
        return

    cursor.execute("SELECT id FROM shifts WHERE status='open' ORDER BY id DESC LIMIT 1")
    shift = cursor.fetchone()

    if not shift:
        await message.answer("Нет активной смены", reply_markup=main_menu())
        return

    cursor.execute("SELECT employee_id FROM shift_employees WHERE shift_id=?", (shift[0],))
    employees = cursor.fetchall()

    if not employees:
        await message.answer("Нет сотрудников в смене", reply_markup=main_menu())
        return

    text = "Смена:\n\n"
    for (emp_id,) in employees:
        cursor.execute("SELECT name FROM employees WHERE id=?", (emp_id,))
        emp = cursor.fetchone()
        name = emp[0] if emp else f"ID {emp_id}"

        cursor.execute(
            "SELECT COUNT(*) FROM orders WHERE employee_id=? AND status='closed'",
            (emp_id,),
        )
        count = cursor.fetchone()[0]
        text += f"{name}: {count} кальянов\n"

    await message.answer(text, reply_markup=main_menu())
