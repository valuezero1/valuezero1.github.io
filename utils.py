from config import ADMIN_ID
from database import is_employee


def has_access(tg_id: int) -> bool:
    return tg_id == ADMIN_ID or is_employee(tg_id)


async def guard(call):
    if not has_access(call.from_user.id):
        await call.answer(
            "Нет доступа. Подай заявку как сотрудник",
            show_alert=True,
        )
        return False
    return True


async def check_employee(call):
    return await guard(call)
