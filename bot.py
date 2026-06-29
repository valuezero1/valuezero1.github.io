import asyncio
import os

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.types import MenuButtonWebApp, WebAppInfo

from api import app as fastapi_app
from config import BOT_TOKEN
from database import init_db
from handlers.admin import router as admin_router
from handlers.callbacks import router as callback_router
from handlers.checklist import router as checklist_router
from handlers.finance import router as finance_router
from handlers.orders import router as order_router
from handlers.shifts import router as shift_router
from keyboards import WEBAPP_URL

print("BOT START")


async def run_api():
    port = int(os.getenv("PORT", "8000"))
    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    print("MAIN START")

    init_db()

    bot = Bot(BOT_TOKEN)
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Открыть Rave",
            web_app=WebAppInfo(url=WEBAPP_URL),
        )
    )
    dp = Dispatcher()

    dp.include_router(admin_router)
    dp.include_router(checklist_router)
    dp.include_router(finance_router)
    dp.include_router(shift_router)
    dp.include_router(callback_router)
    dp.include_router(order_router)

    print("POLLING START")

    await asyncio.gather(
        dp.start_polling(bot),
        run_api(),
    )


if __name__ == "__main__":
    asyncio.run(main())
