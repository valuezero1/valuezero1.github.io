import asyncio

from aiogram import Bot


async def run_coal_cycle(bot: Bot, order_id: int, tg_id: int, zone: str, table_number: str):
    title = f"Кальян #{order_id}: {zone}, номер {table_number}"

    for cycle in range(2):
        await asyncio.sleep(15 * 60)
        await bot.send_message(tg_id, f"🔥 {title}\nПора поставить угли")

        await asyncio.sleep(3 * 60)
        await bot.send_message(tg_id, f"🔄 {title}\nПора перевернуть угли")

        await asyncio.sleep(3 * 60)
        await bot.send_message(tg_id, f"🔥 {title}\nПора поставить угли")

    await bot.send_message(tg_id, f"✅ {title}\nВедение кальяна завершено")
