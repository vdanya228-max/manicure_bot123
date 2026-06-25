import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from keyboards import get_main_menu_keyboard, get_subscription_keyboard
from config import ADMIN_ID
from handlers.common import check_subscription
from database import get_user_booking

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    is_sub = await check_subscription(user_id, message.bot)

    if not is_sub:
        await message.answer(
            "⚠️ <b>Для записи необходимо подписаться на наш канал.</b>",
            reply_markup=get_subscription_keyboard(),
            parse_mode="HTML"
        )
        return

    is_admin_user = user_id == ADMIN_ID
    await message.answer(
        "💅 <b>Добро пожаловать в бот записи на маникюр!</b>\n\nВыберите действие:",
        reply_markup=get_main_menu_keyboard(is_subscribed=True, is_admin=is_admin_user),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "book")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    await callback.answer()                    # Отвечаем сразу
    user_id = callback.from_user.id

    try:
        is_sub = await check_subscription(user_id, callback.bot)
        if not is_sub:
            await callback.message.edit_text(
                "⚠️ <b>Для записи необходимо подписаться на канал.</b>",
                reply_markup=get_subscription_keyboard(),
                parse_mode="HTML"
            )
            return

        existing = await get_user_booking(user_id)
        if existing:
            await callback.message.edit_text(
                f"❌ У вас уже есть активная запись:\n📅 {existing['date']} в {existing['time']}",
                reply_markup=get_main_menu_keyboard(is_subscribed=True),
                parse_mode="HTML"
            )
            return

        from .booking import show_available_dates
        await show_available_dates(callback, state)

    except Exception as e:
        logger.error(f"Ошибка в start_booking: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка. Попробуйте позже или напишите администратору.",
            reply_markup=get_main_menu_keyboard(is_subscribed=True),
            parse_mode="HTML"
        )
