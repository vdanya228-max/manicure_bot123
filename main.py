"""
Точка входа для деплоя (Render, Railway и т.д.)
"""
import sys
from pathlib import Path

# === Фикс путей для Render.com / Railway ===
BASE_DIR = str(Path(__file__).resolve().parent)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, "/opt/render/project/src")
sys.path.insert(0, "/app")

from bot import main_webhook, main_polling
import os
import asyncio

if __name__ == "__main__":
    # Определяем, использовать ли webhook
    use_webhook = bool(
        os.getenv("RENDER_EXTERNAL_HOSTNAME") or 
        os.getenv("RAILWAY_PUBLIC_DOMAIN") or 
        os.getenv("WEBHOOK_URL")
    )
    
    if use_webhook:
        print("🚀 Запуск в режиме Webhook")
        asyncio.run(main_webhook())
    else:
        print("🚀 Запуск в режиме Polling (локально)")
        asyncio.run(main_polling())
