import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.db import init_db
from app.admin_handlers import admin_router
from app.handlers import router


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    await init_db()
    bot = Bot(token=settings.bot_token)
    # MemoryStorage: FSM state is lost on restart (acceptable for admin flows).
    # Admins will simply re-start any interrupted operation after a restart.
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    # Admin router must be registered FIRST so its handlers take priority
    # over the customer router for shared button texts (e.g. "📋 Xizmatlar").
    dp.include_router(admin_router)
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
