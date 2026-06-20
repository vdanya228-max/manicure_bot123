"""
Обработчики старта и главного меню (цены, портфолио).
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from keyboards import (
    get_main_menu_keyboard,
    get_subscription_keyboard,
    get_prices_keyboard,
    get_portfolio_keyboard
)
from config import PRICES_HTML, PORTFOLIO_LINK, PORTFOLIO_BUTTON_TEXT, ADMIN_ID
from handlers.common import check_subscription
from database import get_user_booking

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "book")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    """Начать процесс записи"""
    await callback.answer()                    # ← Добавь это в самое начало!
    
    user_id = callback.from_user.id
    
    # Проверка подписки
    is_sub = await check_subscription(user_id, callback.bot)
    if not is_sub:
        await callback.message.edit_text(
            "⚠️ <b>Для записи необходимо подписаться на канал.</b>",
            reply_markup=get_subscription_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Проверка: уже есть запись?
    existing = await get_user_booking(user_id)
    if existing:
        await callback.message.edit_text(
            f"❌ У вас уже есть активная запись:\n"
            f"📅 {existing['date']} в {existing['time']}\n\n"
            f"Сначала отмените её, чтобы записаться на другое время.",
            reply_markup=get_main_menu_keyboard(is_subscribed=True),
            parse_mode="HTML"
        )
        return
    
    # Переходим к выбору даты
    from .booking import show_available_dates
    await show_available_dates(callback, state)
