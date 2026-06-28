from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

ORDER_ZONES = [
    ("std1", "Стандарт 1", ["7", "8", "9", "10"]),
    ("std2", "Стандарт 2", ["40", "41", "42"]),
    ("boot1", "Буткемп 1", ["21", "22", "23", "24", "25"]),
    ("boot2", "Буткемп 2", ["30", "31", "32", "33", "34"]),
    ("duo1", "Дуо 1", ["1", "2"]),
    ("duo2", "Дуо 2", ["3", "4"]),
    ("duo3", "Дуо 3", ["26", "27"]),
    ("duo4", "Дуо 4", ["28", "29"]),
    ("trio1", "Трио 1", ["11", "12", "13"]),
    ("trio2", "Трио 2", ["14", "15", "16"]),
    ("trio3", "Трио 3", ["17", "18", "19"]),
    ("solo", "Соло", ["20"]),
    ("vip_boot", "VIP-буткемп", ["VIP-буткемп"]),
    ("ps1", "Пс1", ["Пс1"]),
    ("ps2", "Пс2", ["Пс2"]),
    ("ps3", "Пс3", ["Пс3"]),
    ("ps4", "Пс4", ["Пс4"]),
    ("ps_vip", "Пс VIP", ["Пс VIP"]),
]

TOBACCO_CATEGORIES = [
    ("sour_berries", "Кислые ягоды"),
    ("sweet_berries", "Сладкие ягоды"),
    ("sour_fruits", "Кислые фрукты"),
    ("sweet_fruits", "Сладкие фрукты"),
    ("herbal_fresh", "Травяные и свежие"),
    ("floral", "Цветочные"),
    ("desserts", "Десертные и кондитерские"),
    ("drinks", "Напитки"),
    ("mixes", "Миксы и авторские вкусы"),
]

SHIFT_RECEIVERS = [
    "Михаил",
    "Даниил В.",
    "Данила Э.",
    "Георгий",
    "Денис",
    "Глеб",
    "Елена",
    "Максим",
    "Соня",
]

ZONE_BY_CODE = {code: name for code, name, _ in ORDER_ZONES}
PLACES_BY_ZONE = {code: places for code, _, places in ORDER_ZONES}
TOBACCO_CATEGORY_BY_CODE = {code: name for code, name in TOBACCO_CATEGORIES}

WEBAPP_URL = "https://web-production-f2670.up.railway.app/"


def home_button():
    return InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")


def home_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[home_button()]])


def request_access_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👋 Я сотрудник", callback_data="become_employee")]
        ]
    )


def main_menu():
    """Главное меню: только WebApp + смена."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📊 Открыть панель управления",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )],
            [InlineKeyboardButton(text="🟢 Смена", callback_data="shift_menu")],
        ]
    )


def shift_menu():
    """Меню смены: только открыть и закрыть."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Открыть смену", callback_data="open_shift")],
            [InlineKeyboardButton(text="🔴 Закрыть смену", callback_data="close_shift")],
            [home_button()],
        ]
    )


# ── Остальные клавиатуры используются внутри бота (чеклист, заявки и т.д.) ──

def zones_kb():
    rows = []
    for index in range(0, len(ORDER_ZONES), 2):
        row = [
            InlineKeyboardButton(text=name, callback_data=f"zone_{code}")
            for code, name, _ in ORDER_ZONES[index: index + 2]
        ]
        rows.append(row)
    rows.append([home_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def places_kb(zone_code):
    places = PLACES_BY_ZONE.get(zone_code, [])
    rows = []
    for index in range(0, len(places), 3):
        row = [
            InlineKeyboardButton(text=place, callback_data=f"place_{index + offset}")
            for offset, place in enumerate(places[index: index + 3])
        ]
        rows.append(row)
    rows.append([home_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def employees_kb(employees):
    rows = []
    for emp_id, name in employees:
        rows.append([InlineKeyboardButton(text=name, callback_data=f"assign_{emp_id}")])
    rows.append([home_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Создать", callback_data="confirm_order"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order"),
            ],
            [home_button()],
        ]
    )


def tobacco_menu(is_admin=False):
    rows = []
    if is_admin:
        rows.append([InlineKeyboardButton(text="➕ Добавить вкус", callback_data="add_tobacco")])
    rows.append([home_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def active_orders_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧹 Очистить активные", callback_data="clear_active_orders")],
            [home_button()],
        ]
    )


def clear_active_orders_confirm_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, очистить", callback_data="confirm_clear_active_orders")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="active_orders")],
            [home_button()],
        ]
    )


def finance_report_kb(report_id, report_month):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"finance_prev_{report_id}"),
                InlineKeyboardButton(text="Вперед ➡️", callback_data=f"finance_next_{report_id}"),
            ],
            [InlineKeyboardButton(text="📆 Общая статистика за месяц", callback_data=f"finance_month_{report_month}")],
            [home_button()],
        ]
    )


def finance_empty_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[home_button()]])


def tobacco_categories_kb(prefix):
    rows = []
    for code, name in TOBACCO_CATEGORIES:
        rows.append([InlineKeyboardButton(text=name, callback_data=f"{prefix}_{code}")])
    rows.append([home_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def order_started_kb(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Сейчас сделаю", callback_data=f"order_start_{order_id}")],
            [home_button()],
        ]
    )


def order_delivered_kb(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отдал кальян", callback_data=f"order_delivered_{order_id}")],
            [home_button()],
        ]
    )


def shift_receivers_kb():
    rows = [
        [InlineKeyboardButton(text=name, callback_data=f"shift_receiver_{idx}")]
        for idx, name in enumerate(SHIFT_RECEIVERS)
    ]
    rows.append([InlineKeyboardButton(text="Ресепшен", callback_data="shift_receiver_reception")])
    rows.append([home_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def checklist_next_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнено", callback_data="checklist_next")],
            [InlineKeyboardButton(text="⚠️ Есть замечание", callback_data="checklist_issue")],
            [home_button()],
        ]
    )


def checklist_photo_done_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Фото отправлены, дальше", callback_data="checklist_photo_done")],
            [home_button()],
        ]
    )


def checklist_final_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Смену принимаю, претензий нет", callback_data="checklist_final_ok")],
            [InlineKeyboardButton(text="⚠️ Смену принимаю, есть претензии", callback_data="checklist_final_claims")],
            [home_button()],
        ]
    )
