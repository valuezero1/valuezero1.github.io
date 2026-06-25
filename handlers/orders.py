from datetime import datetime

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from database import conn, cursor
from keyboards import main_menu, zones_kb
from utils import has_access

router = Router()


class OrderState(StatesGroup):
    zone = State()
    table = State()
    flavor = State()


@router.message(lambda m: m.text == "/new")
async def new_order_cmd(message: Message, state: FSMContext):
    if not has_access(message.from_user.id):
        await message.answer("Нет доступа. Нажми 'Я сотрудник'", reply_markup=main_menu())
        return

    await state.clear()
    await state.set_state(OrderState.zone)
    await message.answer("Выберите зону:", reply_markup=zones_kb())


@router.message(lambda m: m.text == "/stats")
async def stats(message: Message):
    cursor.execute(
        """
        SELECT employee_id, COUNT(*)
        FROM orders
        WHERE status='closed'
        GROUP BY employee_id
        """
    )
    rows = cursor.fetchall()

    if not rows:
        await message.answer("Пока нет закрытых заказов", reply_markup=main_menu())
        return

    text = "📊 Статистика сотрудников:\n\n"
    for employee_id, count in rows:
        cursor.execute("SELECT name FROM employees WHERE id=?", (employee_id,))
        emp = cursor.fetchone()
        name = emp[0] if emp else f"ID {employee_id}"
        text += f"{name}: {count} кальянов\n"

    await message.answer(text, reply_markup=main_menu())


@router.message(lambda m: m.text and m.text.startswith("/close"))
async def close_order(message: Message):
    try:
        order_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("Используй: /close ID", reply_markup=main_menu())
        return

    cursor.execute("SELECT created_at FROM orders WHERE id=?", (order_id,))
    row = cursor.fetchone()

    if not row:
        await message.answer("Заказ не найден", reply_markup=main_menu())
        return

    closed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        UPDATE orders
        SET status='closed', closed_at=?
        WHERE id=?
        """,
        (closed_at, order_id),
    )
    conn.commit()

    await message.answer(f"Кальян {order_id} закрыт", reply_markup=main_menu())
