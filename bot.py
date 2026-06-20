import sys
from pathlib import Path

# === Фикс путей для Render.com ===
BASE_DIR = str(Path(__file__).resolve().parent)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, "/opt/render/project/src")
sys.path.insert(0, "/app")

import asyncio
import logging
import os   # ← обязательно должен быть здесь

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from config import BOT_TOKEN, ADMIN_ID
from database import init_db
from scheduler import init_scheduler, restore_reminders, shutdown_scheduler

from handlers.start import router as start_router
from handlers.booking import router as booking_router
from handlers.admin import router as admin_router
from handlers.common import router as common_router

# ====================== Дальше идёт остальной код bot.py ======================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    logger.info("🚀 Запуск бота...")
    await init_db()
    init_scheduler()
    await restore_reminders(bot)
    try:
        await bot.send_message(ADMIN_ID, "✅ Бот успешно запущен")
    except Exception as e:
        logger.warning(f"Не удалось уведомить админа: {e}")


async def on_shutdown(bot: Bot):
    logger.info("🛑 Остановка бота...")
    shutdown_scheduler()


async def health_check(request):
    return web.Response(text="OK")


async def main_webhook():
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен!")
        return

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start_router)
    dp.include_router(booking_router)
    dp.include_router(admin_router)
    dp.include_router(common_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    webhook_url = os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_HOSTNAME")
    if not webhook_url:
        logger.error("❌ WEBHOOK_URL не задан!")
        return

    if not webhook_url.startswith("https://"):
        webhook_url = "https://" + webhook_url

    full_webhook_url = f"{webhook_url}/webhook"
    await bot.set_webhook(full_webhook_url)
    logger.info(f"Webhook установлен: {full_webhook_url}")

    app = web.Application()
    app.router.add_get("/health", health_check)
    app.router.add_post("/webhook", dp.feed_webhook_update)

    port = int(os.getenv("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"🚀 Webhook сервер запущен на порту {port}")
    await asyncio.Event().wait()


async def main_polling():
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен!")
        return

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start_router)
    dp.include_router(booking_router)
    dp.include_router(admin_router)
    dp.include_router(common_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("🤖 Бот запускается в режиме Polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    use_webhook = bool(
        os.getenv("RENDER_EXTERNAL_HOSTNAME") or 
        os.getenv("RAILWAY_PUBLIC_DOMAIN") or 
        os.getenv("WEBHOOK_URL")
    )
    if use_webhook:
        asyncio.run(main_webhook())
    else:
        asyncio.run(main_polling())
