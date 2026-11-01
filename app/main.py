import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.db import init_db
from app.admin_handlers import admin_router
from app.handlers import router
from app.reports import daily_report_scheduler


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    await init_db()
    bot = Bot(token=settings.bot_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Admin router registered first so admin actions take precedence
    dp.include_router(admin_router)
    dp.include_router(router)

    # Launch background daily report scheduler (runs non-blocking)
    asyncio.create_task(daily_report_scheduler(bot))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
