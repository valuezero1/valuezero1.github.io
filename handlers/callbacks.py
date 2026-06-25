import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID
from database import conn, cursor
from handlers.orders import OrderState
from keyboards import (
    PLACES_BY_ZONE,
    TOBACCO_CATEGORIES,
    TOBACCO_CATEGORY_BY_CODE,
    ZONE_BY_CODE,
    active_orders_kb,
    clear_active_orders_confirm_kb,
    confirm_kb,
    employees_kb,
    main_menu,
    order_delivered_kb,
    order_started_kb,
    places_kb,
    request_access_menu,
    shift_menu,
    tobacco_categories_kb,
    tobacco_menu,
    zones_kb,
)
from scheduler import run_coal_cycle
from utils import check_employee, has_access

router = Router()


class TobaccoState(StatesGroup):
    category = State()
    name = State()


def _is_admin(user_id):
    return user_id == ADMIN_ID


def _tobacco_text():
    cursor.execute("SELECT name, category FROM tobacco ORDER BY category, name")
    rows = cursor.fetchall()

    grouped = {code: [] for code, _ in TOBACCO_CATEGORIES}
    for name, category in rows:
        grouped.setdefault(category or "", []).append(name)

    text_parts = ["🍃 Табаки в наличии"]
    for code, title in TOBACCO_CATEGORIES:
        names = grouped.get(code, [])
        content = "\n".join(f"• {name}" for name in names) if names else "пока пусто"
        text_parts.append(f"\n{title}:\n{content}")

    return "\n".join(text_parts)


@router.callback_query(F.data == "main_menu")
async def main_menu_cb(call: CallbackQuery, state: FSMContext):
    await state.clear()
    if not has_access(call.from_user.id):
        await call.message.answer(
            "Доступа к боту пока нет. Отправь заявку администратору.",
            reply_markup=request_access_menu(),
        )
        await call.answer()
        return

    await call.message.answer("Главное меню", reply_markup=main_menu())
    await call.answer()


@router.callback_query(F.data == "shift_menu")
async def shift_menu_cb(call: CallbackQuery):
    if not await check_employee(call):
        return

    await call.message.edit_text("Меню смены", reply_markup=shift_menu())
    await call.answer()


@router.callback_query(F.data == "close_shift")
async def close_shift_cb(call: CallbackQuery):
    if not await check_employee(call):
        return

    from datetime import datetime

    cursor.execute("SELECT id FROM shifts WHERE status='open' ORDER BY id DESC LIMIT 1")
    shift = cursor.fetchone()

    if not shift:
        await call.answer("Нет активной смены", show_alert=True)
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "UPDATE shifts SET status='closed', closed_at=? WHERE id=?",
        (now, shift[0]),
    )
    conn.commit()

    await call.answer("Смена закрыта", show_alert=True)


@router.callback_query(F.data == "tobacco_menu")
async def tobacco_menu_cb(call: CallbackQuery):
    if not await check_employee(call):
        return

    await call.message.edit_text(
        _tobacco_text(),
        reply_markup=tobacco_menu(is_admin=_is_admin(call.from_user.id)),
    )
    await call.answer()


@router.callback_query(F.data == "add_tobacco")
async def add_tobacco(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer("Добавлять вкусы может только админ", show_alert=True)
        return

    await state.clear()
    await state.set_state(TobaccoState.category)
    await call.message.answer("Выберите категорию:", reply_markup=tobacco_categories_kb("tobacco_cat"))
    await call.answer()


@router.callback_query(F.data.startswith("tobacco_cat_"))
async def tobacco_category(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer("Добавлять вкусы может только админ", show_alert=True)
        return

    category = call.data.removeprefix("tobacco_cat_")
    if category not in TOBACCO_CATEGORY_BY_CODE:
        await call.answer("Категория не найдена", show_alert=True)
        return

    await state.update_data(category=category)
    await state.set_state(TobaccoState.name)
    await call.message.answer("Введите название вкуса:")
    await call.answer()


@router.message(TobaccoState.name)
async def tobacco_name(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        await message.answer("Добавлять вкусы может только админ")
        await state.clear()
        return

    name = message.text.strip() if message.text else ""
    if not name:
        await message.answer("Введите название вкуса текстом")
        return

    data = await state.get_data()
    cursor.execute(
        "INSERT INTO tobacco(name, grams, category) VALUES (?, ?, ?)",
        (name, 0, data["category"]),
    )
    conn.commit()
    await state.clear()

    await message.answer(
        f"Вкус добавлен: {name}\nКатегория: {TOBACCO_CATEGORY_BY_CODE[data['category']]}",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "new_order")
async def new_order(call: CallbackQuery, state: FSMContext):
    if not await check_employee(call):
        return

    await state.clear()
    await state.set_state(OrderState.zone)
    await call.message.answer("Выберите зону:", reply_markup=zones_kb())
    await call.answer()


@router.callback_query(F.data.startswith("zone_"))
async def zone(call: CallbackQuery, state: FSMContext):
    zone_code = call.data.split("_", 1)[1]
    zone_name = ZONE_BY_CODE.get(zone_code)

    if not zone_name:
        await call.answer("Зона не найдена", show_alert=True)
        return

    await state.update_data(zone_code=zone_code, zone=zone_name)
    await state.set_state(OrderState.table)
    await call.message.answer("Выберите номер:", reply_markup=places_kb(zone_code))
    await call.answer()


@router.callback_query(F.data.startswith("place_"))
async def place(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    zone_code = data.get("zone_code")
    places = PLACES_BY_ZONE.get(zone_code, [])

    try:
        place_index = int(call.data.split("_", 1)[1])
        table_number = places[place_index]
    except (ValueError, IndexError):
        await call.answer("Место не найдено", show_alert=True)
        return

    await state.update_data(table=table_number)
    await state.set_state(OrderState.flavor)
    await call.message.answer("Введите вкус кальяна:")
    await call.answer()


@router.message(OrderState.flavor)
async def flavor(message: Message, state: FSMContext):
    flavor_name = message.text.strip() if message.text else ""

    if not flavor_name:
        await message.answer("Введите вкус текстом")
        return

    cursor.execute("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
    employees = cursor.fetchall()
    if not employees:
        await message.answer("Нет сотрудников для назначения", reply_markup=main_menu())
        await state.clear()
        return

    await state.update_data(flavor=flavor_name)
    await message.answer("Назначьте сотрудника:", reply_markup=employees_kb(employees))


@router.callback_query(F.data.startswith("assign_"))
async def assign_employee(call: CallbackQuery, state: FSMContext):
    employee_id = int(call.data.split("_", 1)[1])
    cursor.execute("SELECT id, tg_id, name FROM employees WHERE id=? AND active=1", (employee_id,))
    employee = cursor.fetchone()

    if not employee:
        await call.answer("Сотрудник не найден", show_alert=True)
        return

    emp_id, emp_tg, emp_name = employee
    await state.update_data(employee_id=emp_id, employee_tg=emp_tg, employee_name=emp_name)
    data = await state.get_data()

    await call.message.answer(
        "Проверь:\n"
        f"Зона: {data['zone']}\n"
        f"Номер: {data['table']}\n"
        f"Вкус: {data['flavor']}\n"
        f"Сотрудник: {emp_name}",
        reply_markup=confirm_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "confirm_order")
async def confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if not {"table", "zone", "flavor", "employee_id", "employee_tg"}.issubset(data):
        await call.answer("Начни создание заказа заново", show_alert=True)
        await state.clear()
        return

    cursor.execute(
        """
        INSERT INTO orders(table_number, zone, flavor, employee_id, status)
        VALUES (?, ?, ?, ?, 'active')
        """,
        (data["table"], data["zone"], data["flavor"], data["employee_id"]),
    )
    conn.commit()
    order_id = cursor.lastrowid

    await state.clear()
    await call.message.answer("Кальян создан", reply_markup=main_menu())
    await call.bot.send_message(
        data["employee_tg"],
        "🔥 Новый кальян\n"
        f"ID: {order_id}\n"
        f"Зона: {data['zone']}\n"
        f"Номер: {data['table']}\n"
        f"Вкус: {data['flavor']}",
        reply_markup=order_started_kb(order_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("order_start_"))
async def order_start(call: CallbackQuery):
    order_id = int(call.data.removeprefix("order_start_"))

    cursor.execute(
        """
        SELECT o.table_number, o.zone, e.tg_id
        FROM orders o
        JOIN employees e ON e.id=o.employee_id
        WHERE o.id=?
        """,
        (order_id,),
    )
    order = cursor.fetchone()
    if not order:
        await call.answer("Заказ не найден", show_alert=True)
        return

    table_number, zone_name, employee_tg = order
    if call.from_user.id != employee_tg:
        await call.answer("Эта задача назначена другому сотруднику", show_alert=True)
        return

    await call.message.answer(
        f"Принято: {zone_name}, номер {table_number}",
        reply_markup=order_delivered_kb(order_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("order_delivered_"))
async def order_delivered(call: CallbackQuery):
    order_id = int(call.data.removeprefix("order_delivered_"))

    cursor.execute(
        """
        SELECT o.table_number, o.zone, e.tg_id
        FROM orders o
        JOIN employees e ON e.id=o.employee_id
        WHERE o.id=?
        """,
        (order_id,),
    )
    order = cursor.fetchone()
    if not order:
        await call.answer("Заказ не найден", show_alert=True)
        return

    table_number, zone_name, employee_tg = order
    if call.from_user.id != employee_tg:
        await call.answer("Эта задача назначена другому сотруднику", show_alert=True)
        return

    await call.message.answer(
        f"Таймер на 15 минут установлен\nКальян #{order_id}: {zone_name}, номер {table_number}"
    )
    asyncio.create_task(run_coal_cycle(call.bot, order_id, employee_tg, zone_name, table_number))
    await call.answer()


@router.callback_query(F.data == "cancel_order")
async def cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("Отменено", reply_markup=main_menu())
    await call.answer()


@router.callback_query(F.data == "active_orders")
async def active_orders(call: CallbackQuery):
    if not await check_employee(call):
        return

    cursor.execute(
        """
        SELECT o.id, o.table_number, o.zone, o.flavor, e.name
        FROM orders o
        LEFT JOIN employees e ON e.id=o.employee_id
        WHERE o.status='active'
        ORDER BY o.id DESC
        """
    )
    rows = cursor.fetchall()

    if not rows:
        await call.message.edit_text("Активных кальянов нет", reply_markup=main_menu())
        await call.answer()
        return

    text = "📋 Активные кальяны:\n\n"
    for order_id, table_number, zone_name, flavor_name, emp_name in rows:
        text += (
            f"ID: {order_id}\n"
            f"Зона: {zone_name}\n"
            f"Номер: {table_number}\n"
            f"Вкус: {flavor_name}\n"
            f"Сотрудник: {emp_name or 'не назначен'}\n"
            "------------\n"
        )

    await call.message.edit_text(text, reply_markup=active_orders_kb())
    await call.answer()


@router.callback_query(F.data == "clear_active_orders")
async def clear_active_orders(call: CallbackQuery):
    if not await check_employee(call):
        return

    cursor.execute("SELECT COUNT(*) FROM orders WHERE status='active'")
    count = cursor.fetchone()[0]

    if not count:
        await call.answer("Активных кальянов нет", show_alert=True)
        return

    await call.message.answer(
        f"Очистить активные кальяны? Сейчас активно: {count}",
        reply_markup=clear_active_orders_confirm_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "confirm_clear_active_orders")
async def confirm_clear_active_orders(call: CallbackQuery):
    if not await check_employee(call):
        return

    cursor.execute("UPDATE orders SET status='cleared' WHERE status='active'")
    cleared = cursor.rowcount
    conn.commit()

    await call.message.answer(
        f"Активные кальяны очищены: {cleared}",
        reply_markup=main_menu(),
    )
    await call.answer()


@router.callback_query(F.data == "become_employee")
async def become_employee(call: CallbackQuery):
    cursor.execute("SELECT id FROM employees WHERE tg_id=?", (call.from_user.id,))
    if cursor.fetchone():
        await call.answer("Ты уже сотрудник", show_alert=True)
        return

    cursor.execute(
        """
        SELECT id FROM employee_requests
        WHERE tg_id=? AND status='pending'
        """,
        (call.from_user.id,),
    )
    if cursor.fetchone():
        await call.answer("Заявка уже отправлена", show_alert=True)
        return

    cursor.execute(
        """
        INSERT INTO employee_requests (tg_id, name, status)
        VALUES (?, ?, 'pending')
        """,
        (call.from_user.id, call.from_user.full_name),
    )
    conn.commit()

    await call.bot.send_message(
        ADMIN_ID,
        "Новая заявка на доступ:\n"
        f"{call.from_user.full_name}\n"
        f"TG ID: {call.from_user.id}\n\n"
        "Открой /requests, чтобы одобрить или отклонить.",
    )
    await call.answer("Заявка отправлена администратору", show_alert=True)
