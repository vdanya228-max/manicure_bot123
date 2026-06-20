"""
Модуль клавиатур (inline и reply).
"""
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
from typing import List, Optional
from config import CHANNEL_LINK, PORTFOLIO_LINK, PORTFOLIO_BUTTON_TEXT


def get_main_menu_keyboard(is_subscribed: bool = True, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Главное меню бота. Для администратора добавляется кнопка админ-панели."""
    builder = InlineKeyboardBuilder()
    
    if is_subscribed:
        builder.button(text="📅 Записаться на маникюр", callback_data="book")
    else:
        builder.button(text="📅 Записаться на маникюр", callback_data="check_subscription")
    
    builder.button(text="💰 Прайсы", callback_data="prices")
    builder.button(text="📸 Портфолио", callback_data="portfolio")
    builder.button(text="❌ Отменить мою запись", callback_data="cancel_my_booking")
    builder.button(text="ℹ️ Моя запись", callback_data="my_booking")
    
    # Для администратора добавляем кнопку админ-панели
    if is_admin:
        builder.button(text="👑 Админ-панель", callback_data="admin_panel_from_menu")
    
    builder.adjust(1)
    return builder.as_markup()


def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для проверки подписки."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Подписаться на канал", url=CHANNEL_LINK)
    builder.button(text="✅ Проверить подписку", callback_data="check_subscription")
    builder.adjust(1)
    return builder.as_markup()


def get_prices_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после показа прайса."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Записаться", callback_data="book")
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_portfolio_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура портфолио."""
    builder = InlineKeyboardBuilder()
    builder.button(text=PORTFOLIO_BUTTON_TEXT, url=PORTFOLIO_LINK)
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_dates_keyboard(dates: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура с доступными датами (календарь)."""
    builder = InlineKeyboardBuilder()
    
    for date_str in dates:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            # Красиво: 20 июня (пн)
            weekday = dt.strftime("%a").lower()
            weekdays_ru = {
                'mon': 'пн', 'tue': 'вт', 'wed': 'ср',
                'thu': 'чт', 'fri': 'пт', 'sat': 'сб', 'sun': 'вс'
            }
            ru_weekday = weekdays_ru.get(weekday, weekday)
            text = f"{dt.day} {dt.strftime('%B').lower()[:3]} ({ru_weekday})"
            # Для русского месяца
            months_ru = {
                1: 'янв', 2: 'фев', 3: 'мар', 4: 'апр',
                5: 'мая', 6: 'июн', 7: 'июл', 8: 'авг',
                9: 'сен', 10: 'окт', 11: 'ноя', 12: 'дек'
            }
            text = f"{dt.day} {months_ru[dt.month]} ({ru_weekday})"
        except:
            text = date_str
        
        builder.button(text=text, callback_data=f"date:{date_str}")
    
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    builder.adjust(2)  # 2 колонки
    return builder.as_markup()


def get_times_keyboard(times: List[str], date_str: str) -> InlineKeyboardMarkup:
    """Клавиатура с доступным временем."""
    builder = InlineKeyboardBuilder()
    
    for t in times:
        builder.button(text=f"🕐 {t}", callback_data=f"time|{date_str}|{t}")
    
    builder.button(text="🔙 Выбрать другую дату", callback_data="book")
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    builder.adjust(3)  # 3 колонки для времени
    return builder.as_markup()


def get_confirm_booking_keyboard(date_str: str, time_str: str) -> InlineKeyboardMarkup:
    """Подтверждение записи."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить запись", callback_data=f"confirm|{date_str}|{time_str}")
    builder.button(text="❌ Отменить", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_cancel_confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение отмены своей записи."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, отменить мою запись", callback_data="confirm_cancel_my")
    builder.button(text="🔙 Нет, оставить", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню администратора."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Посмотреть расписание на дату", callback_data="admin_view_date")
    builder.button(text="➕ Добавить временной слот", callback_data="admin_add_slot")
    builder.button(text="➖ Удалить временной слот", callback_data="admin_remove_slot")
    builder.button(text="🚫 Закрыть день", callback_data="admin_close_day")
    builder.button(text="🔓 Открыть день", callback_data="admin_open_day")
    builder.button(text="❌ Отменить запись клиента", callback_data="admin_cancel_booking")
    builder.button(text="📋 Все активные записи", callback_data="admin_all_bookings")
    builder.button(text="⏰ Изменить время записи", callback_data="admin_change_time")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="🔙 Выйти из админ-панели", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_admin_dates_keyboard(dates: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура дат для админа (все даты, даже закрытые)."""
    builder = InlineKeyboardBuilder()
    today = datetime.now().date()
    
    for i in range(31):
        d = today + timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        dt = d
        months_ru = {1:'янв',2:'фев',3:'мар',4:'апр',5:'мая',6:'июн',
                     7:'июл',8:'авг',9:'сен',10:'окт',11:'ноя',12:'дек'}
        weekday = dt.strftime("%a").lower()
        weekdays_ru = {'mon':'пн','tue':'вт','wed':'ср','thu':'чт','fri':'пт','sat':'сб','sun':'вс'}
        text = f"{dt.day} {months_ru[dt.month]} ({weekdays_ru.get(weekday, weekday)})"
        builder.button(text=text, callback_data=f"admin_date:{date_str}")
    
    builder.button(text="🔙 Назад", callback_data="admin_panel")
    builder.adjust(3)
    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Просто кнопка назад."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    return builder.as_markup()


def get_admin_cancel_booking_keyboard(bookings: List[dict]) -> InlineKeyboardMarkup:
    """Список записей для отмены админом."""
    builder = InlineKeyboardBuilder()
    for b in bookings:
        text = f"{b['date']} {b['time']} — {b['client_name']}"
        builder.button(text=text, callback_data=f"admin_cancel:{b['id']}")
    builder.button(text="🔙 Назад", callback_data="admin_panel")
    builder.adjust(1)
    return builder.as_markup()


def get_admin_after_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после успешной отмены записи админом (удобные следующие действия)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить ещё одну запись", callback_data="admin_cancel_booking")
    builder.button(text="📅 Посмотреть расписание на дату", callback_data="admin_view_date")
    builder.button(text="👑 Вернуться в админ-меню", callback_data="admin_panel")
    builder.adjust(1)
    return builder.as_markup()


print("✅ Клавиатуры готовы")