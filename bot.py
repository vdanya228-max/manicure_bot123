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

    # === Правильная настройка webhook ===
    webhook_url = os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_HOSTNAME")
    if not webhook_url:
        logger.error("❌ WEBHOOK_URL не задан!")
        return

    if not webhook_url.startswith("https://"):
        webhook_url = "https://" + webhook_url

    full_webhook_url = f"{webhook_url}/webhook"
    await bot.set_webhook(full_webhook_url)
    logger.info(f"Webhook установлен: {full_webhook_url}")

    # === Правильный обработчик webhook ===
    async def handle_webhook(request):
        update = types.Update(**await request.json())
        await dp.feed_update(bot, update)
        return web.Response()

    app = web.Application()
    app.router.add_get("/health", health_check)
    app.router.add_post("/webhook", handle_webhook)

    port = int(os.getenv("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"🚀 Webhook сервер запущен на порту {port}")
    await asyncio.Event().wait()
