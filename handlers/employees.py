from aiogram import F, Router
from aiogram.types import CallbackQuery

router = Router()

from utils import check_employee

@router.callback_query(F.data == "new_order")
async def new_order(call: CallbackQuery):

    if not await check_employee(call):
        return

    await call.message.answer("🍃 Выбор стола")

@router.callback_query(F.data == "become_employee")
async def become_employee(call: CallbackQuery):

    from database import cursor, conn

    cursor.execute("""
        SELECT id FROM employees WHERE tg_id=?
    """, (call.from_user.id,))

    if cursor.fetchone():
        await call.answer("Ты уже сотрудник", show_alert=True)
        return

    cursor.execute("""
        INSERT INTO employee_requests (tg_id, name, status)
        VALUES (?, ?, 'pending')
    """, (call.from_user.id, call.from_user.full_name))

    conn.commit()

    await call.answer("Заявка отправлена", show_alert=True)