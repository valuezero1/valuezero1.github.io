from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_ID
from database import conn, cursor
from keyboards import main_menu, request_access_menu
from utils import has_access

router = Router()


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
async def requests(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute(
        """
        SELECT id, tg_id, name FROM employee_requests
        WHERE status='pending'
        """
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
                        InlineKeyboardButton(
                            text="✅ Одобрить",
                            callback_data=f"approve_{req_id}",
                        ),
                        InlineKeyboardButton(
                            text="❌ Отклонить",
                            callback_data=f"reject_{req_id}",
                        ),
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
        """
        INSERT INTO employees (tg_id, name, active)
        VALUES (?, ?, 1)
        """,
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
