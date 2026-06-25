import asyncio

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from database import init_db

from handlers.admin import router as admin_router
from handlers.orders import router as order_router
from handlers.shifts import router as shift_router
from handlers.checklist import router as checklist_router
from handlers.finance import router as finance_router
from handlers.callbacks import router as callback_router


print("BOT START")


async def main():
    print("MAIN START")

    init_db()

    bot = Bot(BOT_TOKEN)

    dp = Dispatcher()

    dp.include_router(admin_router)
    dp.include_router(checklist_router)
    dp.include_router(finance_router)
    dp.include_router(shift_router)
    dp.include_router(callback_router)
    dp.include_router(order_router)

    print("POLLING START")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
