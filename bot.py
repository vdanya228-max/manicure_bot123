"""
Главный файл Telegram-бота для мастера маникюра.
Поддерживает как Long Polling (локально), так и Webhook (Railway / production).
"""
import sys
from pathlib import Path

# === Максимально надёжный фикс путей (Render + Railway) ===
BASE_DIR = str(Path(__file__).resolve().parent)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, "/opt/render/project/src")   # Render.com
sys.path.insert(0, "/app")                      # Railway

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from config import BOT_TOKEN, ADMIN_ID
from database import init_db
from scheduler import init_scheduler, restore_reminders, shutdown_scheduler

# Импорт роутеров
from handlers.start import router as start_router
from handlers.booking import router as booking_router
from handlers.admin import router as admin_router
from handlers.common import router as common_router

# Настройка логирования
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
        await bot.send_message(ADMIN_ID, "✅ Бот успешно запущен (Webhook режим)")
    except Exception as e:
        logger.warning(f"Не удалось уведомить админа: {e}")
    logger.info("✅ Бот готов к работе")


async def on_shutdown(bot: Bot):
    logger.info("🛑 Остановка бота...")
    shutdown_scheduler()


async def health_check(request):
    """Health check endpoint для UptimeRobot / Railway"""
    return web.Response(text="OK", status=200)


async def main_webhook():
    """Запуск в режиме Webhook (для Railway и production)"""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
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

    # Railway автоматически даёт публичный домен
    webhook_url = os.getenv("WEBHOOK_URL") or os.getenv("RAILWAY_PUBLIC_DOMAIN")
    
    if not webhook_url:
        logger.error("❌ WEBHOOK_URL или RAILWAY_PUBLIC_DOMAIN не задан!")
        return

    # Убираем https:// если есть
    if webhook_url.startswith("https://"):
        webhook_url = webhook_url.replace("https://", "")

    full_webhook_url = f"https://{webhook_url}/webhook"

    # Устанавливаем webhook
    await bot.set_webhook(full_webhook_url)
    logger.info(f"Webhook установлен: {full_webhook_url}")

    # Создаём aiohttp приложение
    app = web.Application()
    app.router.add_get("/health", health_check)
    app.router.add_post("/webhook", dp.feed_webhook_update)

    # Railway использует переменную PORT
    port = int(os.getenv("PORT", 8080))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"🚀 Webhook сервер запущен на порту {port}")
    await asyncio.Event().wait()  # Держим сервер живым


async def main_polling():
    """Обычный режим Long Polling (для локальной разработки)"""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
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
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    # Если есть переменная окружения RAILWAY_PUBLIC_DOMAIN или WEBHOOK_URL → используем webhook
    use_webhook = bool(os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv("WEBHOOK_URL"))

    try:
        if use_webhook:
            asyncio.run(main_webhook())
        else:
            asyncio.run(main_polling())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")