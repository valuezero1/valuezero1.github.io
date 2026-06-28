from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import CHECKLIST_REPORT_CHAT_ID, CHECKLIST_REPORT_THREAD_ID, CHECKLISTCHECKER_ID
from database import conn, cursor, is_employee
from keyboards import (
    SHIFT_RECEIVERS,
    checklist_final_kb,
    checklist_next_kb,
    checklist_photo_done_kb,
    home_kb,
    main_menu,
    shift_receivers_kb,
)

router = Router()


class ChecklistState(StatesGroup):
    receiver = State()
    photo = State()
    section = State()
    issue = State()
    final = State()


CHECKLIST_SECTIONS = [
    {
        "title": "Ресепшен",
        "photo": True,
        "items": [
            "Визуальный порядок",
            "Геймпады составлены на док-станции",
            "Нет чужой посуды/банок/прочего мусора",
            "Провода аккуратно уложены",
            "Нет валяющихся повсюду чеков",
        ],
    },
    {
        "title": "Холодильники",
        "photo": True,
        "items": [
            "Холодильник выставлен товарами",
            "Нет щелей между позициями",
        ],
    },
    {
        "title": "Уборные",
        "photo": True,
        "items": [
            "В мыльницах есть мыло",
            "Полотенца для рук в дозаторе",
            "В кабинках нет мусора, не валяется бумага и прочий мусор",
            "Туалетная бумага в кабинках",
            "Унитазы чистые",
        ],
    },
    {
        "title": "Лаундж зона",
        "photo": False,
        "items": [
            "Столешница протерта, нет пыли/разводов/мусора",
            "Отсутствие личных вещей персонала",
        ],
    },
    {
        "title": "Зоны Playstation",
        "photo": False,
        "items": [
            "Геймпады убраны на ресепшен",
            "На ТВ включено слайд-шоу франшизы",
            "В зоне не валяется мусор",
            "Общий визуальный порядок",
            "Отсутствуют торчащие провода из ТВ и короба с PS",
        ],
    },
    {
        "title": "Зоны PC",
        "photo": False,
        "items": [
            "Мониторы ровно, на одном уровне, протерты",
            "Девайсы лежат ровно, клавиатуры собраны",
            "Девайсы протерты, тактильная чистота",
            "Провода аккуратно сложены",
            "Наушники на стойке, микрофоном вперед",
            "Стол протерт, нет разводов, мусора и пыли",
            "Спинки кресел подняты, высота опущена",
            "Подушки и спинки прикреплены к креслам",
            "На креслах нет пятен, разводов, пыли",
            "В каждой клавиатуре влажная салфетка",
            "На стенах нет грязи, разводов",
            "Мусорные ведра не переполнены",
            "Неактивные девайсы подключены на заряд",
            "Провода за системным блоком аккуратно убраны",
            "Общий визуальный порядок",
        ],
    },
    {
        "title": "Коридоры",
        "photo": False,
        "items": [
            "По коридору не валяется мусор",
            "Мусорные ведра не переполнены",
            "Нет грязи на стенах",
            "Пол в приемлемом состоянии",
        ],
    },
    {
        "title": "Кальянная зона",
        "photo": False,
        "items": [
            "Нет грязных кальянов, все аккуратно составлены",
            "Нет грязных чаш, все аккуратно составлены",
            "Весь табак составлен в положенное место",
            "Столы протерты, нет разводов и пятен от сиропа",
            "Калауды аккуратно составлены",
            "Ведро с мусором не переполнено",
            "Раковина не желтая, нет следов сиропа/табака",
            "Чистая печь, микроволновка и чайник",
            "Общая визуальная чистота",
        ],
    },
    {
        "title": "Отсутствие негативных отзывов за смену",
        "photo": False,
        "items": ["Негативные отзывы отсутствуют"],
    },
]


def _section_text(section):
    items = "\n".join(f"• {item}" for item in section["items"])
    return f"{section['title']}\n\n{items}"


async def _send_current_step(message, state: FSMContext):
    data = await state.get_data()
    index = data.get("section_index", 0)

    if index >= len(CHECKLIST_SECTIONS):
        await state.set_state(ChecklistState.final)
        await message.answer("Итог:", reply_markup=checklist_final_kb())
        return

    section = CHECKLIST_SECTIONS[index]
    if section["photo"]:
        await state.set_state(ChecklistState.photo)
        await message.answer(
            f"{section['title']}\n\n"
            "Отправьте одно или несколько фото. Когда все фото загружены, нажмите кнопку ниже.",
            reply_markup=checklist_photo_done_kb(),
        )
        return

    await state.set_state(ChecklistState.section)
    await message.answer(_section_text(section), reply_markup=checklist_next_kb())


async def _finish_checklist(call: CallbackQuery, state: FSMContext, final_text: str):
    data = await state.get_data()
    receiver = data.get("receiver", "Не указан")
    photos = data.get("photos", [])
    issues = data.get("issues", [])
    opened_by = call.from_user.full_name
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("INSERT INTO shifts(opened_at, status) VALUES (?, ?)", (now, "open"))
    conn.commit()
    shift_id = cursor.lastrowid

    cursor.execute("SELECT id FROM employees WHERE tg_id=? AND active=1", (call.from_user.id,))
    employee = cursor.fetchone()
    if employee:
        cursor.execute(
            "INSERT INTO shift_employees(shift_id, employee_id) VALUES (?, ?)",
            (shift_id, employee[0]),
        )
        conn.commit()

    issues_text = (
        "\n".join(f"• {title}: {text}" for title, text in issues)
        if issues
        else "Замечаний нет"
    )

    report = (
        "🟢 Чек-лист открытия смены\n"
        f"Смена ID: {shift_id}\n"
        f"Кто принимает: {receiver}\n"
        f"Открыл: {opened_by} ({call.from_user.id})\n"
        f"Время: {now}\n\n"
        "Разделы чек-листа:\n"
        + "\n".join(f"• {section['title']}" for section in CHECKLIST_SECTIONS)
        + f"\n\nЗамечания:\n{issues_text}"
        + f"\n\nИтог: {final_text}"
    )

    if CHECKLIST_REPORT_CHAT_ID:
        send_kwargs = {"chat_id": CHECKLIST_REPORT_CHAT_ID}
        if CHECKLIST_REPORT_THREAD_ID:
            send_kwargs["message_thread_id"] = CHECKLIST_REPORT_THREAD_ID

        await call.bot.send_message(text=report, **send_kwargs)
        for title, file_id in photos:
            await call.bot.send_photo(
                photo=file_id,
                caption=f"Фото: {title}",
                **send_kwargs,
            )
    else:
        for target_id in CHECKLISTCHECKER_ID:
            await call.bot.send_message(target_id, report)
            for title, file_id in photos:
                await call.bot.send_photo(target_id, file_id, caption=f"Фото: {title}")

    await state.clear()
    await call.message.answer("Смена открыта, чек-лист отправлен.", reply_markup=main_menu())
    await call.answer()


@router.callback_query(F.data == "open_shift")
async def open_shift_checklist(call: CallbackQuery, state: FSMContext):
    if not is_employee(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    await state.clear()
    await state.set_state(ChecklistState.receiver)
    await call.message.answer("Кто принимает смену?", reply_markup=shift_receivers_kb())
    await call.answer()


@router.callback_query(F.data.startswith("shift_receiver_"))
async def shift_receiver(call: CallbackQuery, state: FSMContext):
    value = call.data.removeprefix("shift_receiver_")
    receiver = "Ресепшен" if value == "reception" else SHIFT_RECEIVERS[int(value)]

    await state.update_data(receiver=receiver, section_index=0, photos=[], issues=[])
    await _send_current_step(call.message, state)
    await call.answer()


@router.message(ChecklistState.photo, F.photo)
async def checklist_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    index = data.get("section_index", 0)
    section = CHECKLIST_SECTIONS[index]
    photos = data.get("photos", [])
    photos.append((section["title"], message.photo[-1].file_id))

    await state.update_data(photos=photos)
    await message.answer(
        f"Фото сохранено для раздела: {section['title']}\n"
        f"Всего фото в отчете: {len(photos)}",
        reply_markup=checklist_photo_done_kb(),
    )


@router.message(ChecklistState.photo, F.document)
async def checklist_photo_document(message: Message, state: FSMContext):
    if not message.document.mime_type or not message.document.mime_type.startswith("image/"):
        await message.answer("Нужно отправить фото или изображение.")
        return

    data = await state.get_data()
    index = data.get("section_index", 0)
    section = CHECKLIST_SECTIONS[index]
    photos = data.get("photos", [])
    photos.append((section["title"], message.document.file_id))

    await state.update_data(photos=photos)
    await message.answer(
        f"Фото сохранено для раздела: {section['title']}\n"
        f"Всего фото в отчете: {len(photos)}",
        reply_markup=checklist_photo_done_kb(),
    )


@router.callback_query(F.data == "checklist_photo_done")
async def checklist_photo_done(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    index = data.get("section_index", 0)
    section = CHECKLIST_SECTIONS[index]
    photos = data.get("photos", [])
    has_section_photo = any(title == section["title"] for title, _ in photos)

    if not has_section_photo:
        await call.answer("Сначала отправьте хотя бы одно фото", show_alert=True)
        return

    await state.set_state(ChecklistState.section)
    await call.message.answer(_section_text(section), reply_markup=checklist_next_kb())
    await call.answer()


@router.message(ChecklistState.photo)
async def checklist_photo_required(message: Message):
    await message.answer("На этом этапе нужно отправить фото.")


@router.callback_query(F.data == "checklist_next")
async def checklist_next(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(section_index=data.get("section_index", 0) + 1)
    await _send_current_step(call.message, state)
    await call.answer()


@router.callback_query(F.data == "checklist_issue")
async def checklist_issue(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    section = CHECKLIST_SECTIONS[data.get("section_index", 0)]

    await state.set_state(ChecklistState.issue)
    await call.message.answer(
        f"Напишите, что не выполнено по разделу: {section['title']}",
        reply_markup=home_kb(),
    )
    await call.answer()


@router.message(ChecklistState.issue)
async def checklist_issue_text(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    if not text:
        await message.answer("Напишите замечание текстом.")
        return

    data = await state.get_data()
    index = data.get("section_index", 0)
    section = CHECKLIST_SECTIONS[index]
    issues = data.get("issues", [])
    issues.append((section["title"], text))

    await state.update_data(issues=issues, section_index=index + 1)
    await _send_current_step(message, state)


@router.callback_query(F.data == "checklist_final_ok")
async def checklist_final_ok(call: CallbackQuery, state: FSMContext):
    await _finish_checklist(
        call,
        state,
        "Смену принимаю, претензий к предыдущей смене не имею.",
    )


@router.callback_query(F.data == "checklist_final_claims")
async def checklist_final_claims(call: CallbackQuery, state: FSMContext):
    await _finish_checklist(
        call,
        state,
        "Смену принимаю, есть претензии к предыдущей смене.",
    )
