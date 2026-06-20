"""
Общие обработчики (назад, подписка, ошибки и т.д.).
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from keyboards import get_main_menu_keyboard, get_subscription_keyboard
from config import CHANNEL_ID, CHANNEL_LINK, ADMIN_ID
from database import get_user_booking

logger = logging.getLogger(__name__)
router = Router()


async def check_subscription(user_id: int, bot) -> bool:
    """Проверка подписки пользователя на канал."""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        # Статусы: 'member', 'administrator', 'creator'
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning(f"Ошибка проверки подписки для {user_id}: {e}")
        return False


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await callback.answer()          # Сразу отвечаем, чтобы убрать загрузку
    await state.clear()
    user_id = callback.from_user.id
    
    # Проверяем подписку
    is_sub = await check_subscription(user_id, callback.bot)
    
    text = (
        "💅 <b>Добро пожаловать в бот записи на маникюр!</b>\n\n"
        "Выберите действие:"
    )
    
    if not is_sub:
        text = (
            "⚠️ <b>Для записи необходимо подписаться на наш канал.</b>\n\n"
            "После подписки нажмите «Проверить подписку»."
        )
        await callback.message.edit_text(
            text,
            reply_markup=get_subscription_keyboard(),
            parse_mode="HTML"
        )
    else:
        is_admin_user = user_id == ADMIN_ID
        await callback.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard(is_subscribed=True, is_admin=is_admin_user),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery, state: FSMContext):
    """Проверка подписки по кнопке."""
    user_id = callback.from_user.id
    is_sub = await check_subscription(user_id, callback.bot)
    
    if is_sub:
        await callback.message.edit_text(
            "✅ <b>Спасибо! Вы подписаны на канал.</b>\n\n"
            "Теперь вам доступна запись на маникюр.",
            reply_markup=get_main_menu_keyboard(is_subscribed=True),
            parse_mode="HTML"
        )
        await callback.answer("Подписка подтверждена!")
    else:
        await callback.answer(
            "❌ Вы ещё не подписаны на канал. Пожалуйста, подпишитесь.",
            show_alert=True
        )


@router.callback_query(F.data == "my_booking")
async def show_my_booking(callback: CallbackQuery):
    """Показать текущую запись пользователя."""
    user_id = callback.from_user.id
    booking = await get_user_booking(user_id)
    
    if booking:
        text = (
            f"📋 <b>Ваша текущая запись:</b>\n\n"
            f"📅 <b>Дата:</b> {booking['date']}\n"
            f"🕐 <b>Время:</b> {booking['time']}\n"
            f"👤 <b>Имя:</b> {booking['client_name']}\n"
            f"📞 <b>Телефон:</b> {booking['phone']}\n\n"
            f"<i>Чтобы отменить — нажмите кнопку ниже.</i>"
        )
        from keyboards import get_cancel_confirm_keyboard
        await callback.message.edit_text(
            text,
            reply_markup=get_cancel_confirm_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "ℹ️ У вас нет активной записи.\n\n"
            "Вы можете записаться на удобное время.",
            reply_markup=get_main_menu_keyboard(is_subscribed=True),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "cancel_my_booking")
async def cancel_my_booking_handler(callback: CallbackQuery):
    """Кнопка 'Отменить мою запись' из главного меню — показывает текущую запись с возможностью отмены."""
    await show_my_booking(callback)


print("✅ Общие обработчики готовы")