"""
Конфигурация бота для мастера маникюра.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота от @BotFather
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ID администратора (ваш Telegram ID). Можно получить у @userinfobot
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "123456789"))

# Настройка канала для обязательной подписки
CHANNEL_ID: int = int(os.getenv("CHANNEL_ID", "-1001234567890"))  # Пример: -100xxxxxxxxxx
CHANNEL_LINK: str = os.getenv("CHANNEL_LINK", "https://t.me/your_channel")  # Ссылка на канал

# Название базы данных SQLite
DATABASE_NAME: str = "manicure_bot.db"

# Количество дней вперед для расписания (1 месяц)
SCHEDULE_DAYS_AHEAD: int = 30

# Стандартные временные слоты (можно менять через админ-панель)
DEFAULT_TIME_SLOTS: list[str] = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
    "15:00", "15:30", "16:00", "16:30", "17:00", "17:30",
    "18:00", "18:30", "19:00"
]

# Текст напоминания (за 24 часа)
REMINDER_TEXT: str = (
    "🔔 <b>Напоминаем, что вы записаны на маникюр завтра в {time}.</b>\n"
    "Ждём вас! 💅\n"
    "Если нужно отменить — напишите в боте."
)

# HTML для прайса
PRICES_HTML: str = (
    "💅 <b>Прайс на услуги маникюра:</b>\n\n"
    "• <b>Френч</b> — 1000₽\n"
    "• <b>Квадрат</b> — 500₽\n\n"
    "<i>Цены могут меняться. Уточняйте у мастера.</i>"
)

# Ссылка на портфолио
PORTFOLIO_LINK: str = "https://ru.pinterest.com/crystalwithluv/_created/"
PORTFOLIO_BUTTON_TEXT: str = "📸 Смотреть портфолио"

print("✅ Конфигурация загружена")