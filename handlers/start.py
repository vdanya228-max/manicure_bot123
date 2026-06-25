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
    """Обработчик команды /start"""
    await state.clear()
    user_id = message.from_user.id

    is_sub = await check_subscription(user_id, message.bot)

    if not is_sub:
        await message.answer(
            "⚠️ <b>Для записи необходимо подписаться на наш канал.</b>\n\n"
            "После подписки нажмите «Проверить подписку».",
            reply_markup=get_subscription_keyboard(),
            parse_mode="HTML"
        )
        return

    is_admin_user = user_id == ADMIN_ID
    await message.answer(
        "💅 <b>Добро пожаловать в бот записи на маникюр!</b>\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(is_subscribed=True, is_admin=is_admin_user),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "book")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    """Начать процесс записи"""
    await callback.answer()                    # ← Очень важно! Отвечаем сразу
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


@router.callback_query(F.data == "prices")
async def show_prices(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        PRICES_HTML,
        reply_markup=get_prices_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "portfolio")
async def show_portfolio(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        PORTFOLIO_BUTTON_TEXT,
        reply_markup=get_portfolio_keyboard(),
        parse_mode="HTML"
    )
