import sys
from pathlib import Path

# Фикс путей для Render
BASE_DIR = str(Path(__file__).resolve().parent)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, "/opt/render/project/src")
sys.path.insert(0, "/app")

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from config import BOT_TOKEN, ADMIN_ID
from database import init_db
from scheduler import init_scheduler, restore_reminders, shutdown_scheduler

from handlers.start import router as start_router
from handlers.booking import router as booking_router
from handlers.admin import router as admin_router
from handlers.common import router as common_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = None
dp = None

async def on_startup(bot_instance: Bot):
    logger.info("🚀 Запуск бота...")
    await init_db()
    init_scheduler()
    await restore_reminders(bot_instance)
    try:
        await bot_instance.send_message(ADMIN_ID, "✅ Бот успешно запущен")
    except Exception as e:
        logger.warning(f"Не удалось уведомить админа: {e}")


async def health_check(request):
    return web.Response(text="OK")


async def handle_webhook(request):
    update = types.Update(**await request.json())
    await dp.feed_update(bot, update)
    return web.Response()


async def main():
    global bot, dp

    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен!")
        return

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем все роутеры
    dp.include_router(start_router)
    dp.include_router(booking_router)
    dp.include_router(admin_router)
    dp.include_router(common_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(lambda b: shutdown_scheduler())

    # === Webhook режим ===
    webhook_url = os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_HOSTNAME")
    if webhook_url:
        if not webhook_url.startswith("https://"):
            webhook_url = "https://" + webhook_url
        await bot.set_webhook(f"{webhook_url}/webhook")
        logger.info(f"Webhook установлен: {webhook_url}/webhook")

        app = web.Application()
        app.router.add_get("/health", health_check)
        app.router.add_post("/webhook", handle_webhook)

        port = int(os.getenv("PORT", 10000))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"🚀 Сервер запущен на порту {port}")
        await asyncio.Event().wait()
    else:
        # Polling режим (для локального запуска)
        logger.info("🤖 Запуск в режиме Polling...")
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
