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


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    await state.clear()
    user_id = message.from_user.id
    
    is_subscribed = await check_subscription(user_id, message.bot)
    
    if not is_subscribed:
        text = (
            "👋 <b>Привет!</b>\n\n"
            "Я бот для записи к мастеру маникюра.\n\n"
            "⚠️ <b>Для записи необходимо подписаться на наш Telegram-канал.</b>"
        )
        await message.answer(
            text,
            reply_markup=get_subscription_keyboard(),
            parse_mode="HTML"
        )
        return
    
    text = (
        "💅 <b>Добро пожаловать в бот записи на маникюр!</b>\n\n"
        "Здесь вы можете выбрать удобное время и записаться.\n"
        "Также доступны прайс и портфолио работ.\n\n"
        "Выберите действие:"
    )
    
    is_admin_user = message.from_user.id == ADMIN_ID
    await message.answer(
        text,
        reply_markup=get_main_menu_keyboard(is_subscribed=True, is_admin=is_admin_user),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "prices")
async def show_prices(callback: CallbackQuery):
    """Показать прайс (без FSM)."""
    await callback.message.edit_text(
        PRICES_HTML,
        reply_markup=get_prices_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "portfolio")
async def show_portfolio(callback: CallbackQuery):
    """Показать портфолио."""
    text = (
        "📸 <b>Портфолио работ мастера</b>\n\n"
        "Нажмите кнопку ниже, чтобы посмотреть примеры работ в Pinterest."
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_portfolio_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "book")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    """Начать процесс записи (проверка подписки + переход к выбору даты)."""
    user_id = callback.from_user.id
    
    # Проверка подписки
    is_sub = await check_subscription(user_id, callback.bot)
    if not is_sub:
        await callback.message.edit_text(
            "⚠️ <b>Для записи необходимо подписаться на канал.</b>",
            reply_markup=get_subscription_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
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
        await callback.answer()
        return
    
    # Переходим к выбору даты
    from .booking import show_available_dates
    await show_available_dates(callback, state)


print("✅ Start-обработчики готовы")