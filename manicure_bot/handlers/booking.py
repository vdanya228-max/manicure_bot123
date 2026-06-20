"""
Обработчики процесса бронирования (FSM).
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from datetime import datetime
from keyboards import (
    get_dates_keyboard,
    get_times_keyboard,
    get_confirm_booking_keyboard,
    get_main_menu_keyboard,
    get_cancel_confirm_keyboard
)
from states import BookingStates
from database import (
    get_available_dates,
    get_available_times_for_date,
    create_booking,
    get_user_booking,
    cancel_booking
)
from scheduler import schedule_reminder, remove_reminder
from handlers.common import check_subscription

logger = logging.getLogger(__name__)
router = Router()


async def show_available_dates(callback: CallbackQuery, state: FSMContext):
    """Показать доступные даты."""
    dates = await get_available_dates()
    
    if not dates:
        await callback.message.edit_text(
            "😔 К сожалению, на ближайший месяц нет свободных дат.\n"
            "Попробуйте позже или свяжитесь с мастером.",
            reply_markup=get_main_menu_keyboard(is_subscribed=True),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    text = (
        "📅 <b>Выберите удобную дату:</b>\n\n"
        "Доступны только даты с свободными слотами."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_dates_keyboard(dates),
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.choosing_date)
    await callback.answer()


@router.callback_query(F.data.startswith("date:"), BookingStates.choosing_date)
async def process_date_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора даты."""
    date_str = callback.data.split(":")[1]
    
    times = await get_available_times_for_date(date_str)
    
    if not times:
        await callback.answer("На эту дату больше нет свободного времени.", show_alert=True)
        # Обновляем список дат
        dates = await get_available_dates()
        await callback.message.edit_text(
            "📅 <b>Выберите удобную дату:</b>",
            reply_markup=get_dates_keyboard(dates),
            parse_mode="HTML"
        )
        return
    
    await state.update_data(selected_date=date_str)
    
    text = f"🕐 <b>Выберите время на {date_str}:</b>"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_times_keyboard(times, date_str),
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.choosing_time)
    await callback.answer()


@router.callback_query(F.data.startswith("time|"), BookingStates.choosing_time)
async def process_time_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени."""
    parts = callback.data.split("|")
    date_str = parts[1]
    time_str = parts[2]
    
    await state.update_data(selected_date=date_str, selected_time=time_str)
    
    text = (
        f"📋 <b>Подтвердите данные записи:</b>\n\n"
        f"📅 Дата: <b>{date_str}</b>\n"
        f"🕐 Время: <b>{time_str}</b>\n\n"
        f"Далее нужно будет ввести ваше имя и телефон."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_confirm_booking_keyboard(date_str, time_str),
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.confirming)
    await callback.answer()


@router.callback_query(F.data.startswith("confirm|"), BookingStates.confirming)
async def ask_for_name(callback: CallbackQuery, state: FSMContext):
    """После подтверждения даты/времени — просим имя."""
    parts = callback.data.split("|")
    date_str = parts[1]
    time_str = parts[2]
    
    # Сохраняем ещё раз на всякий случай
    await state.update_data(selected_date=date_str, selected_time=time_str)
    
    text = (
        "👤 <b>Введите ваше имя:</b>\n\n"
        "Например: Анна Иванова"
    )
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(BookingStates.entering_name)
    await callback.answer()


@router.message(BookingStates.entering_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка ввода имени."""
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Имя слишком короткое. Введите ещё раз:")
        return
    
    await state.update_data(client_name=name)
    
    text = (
        "📞 <b>Введите ваш номер телефона:</b>\n\n"
        "Например: +79001234567 или 89001234567"
    )
    
    await message.answer(text, parse_mode="HTML")
    await state.set_state(BookingStates.entering_phone)


@router.message(BookingStates.entering_phone)
async def process_phone_and_confirm(message: Message, state: FSMContext):
    """Обработка телефона и финальное подтверждение + сохранение."""
    phone = message.text.strip()
    bot = message.bot  # Получаем bot из сообщения
    
    # Простая валидация телефона
    if len(phone) < 10 or not any(c.isdigit() for c in phone):
        await message.answer("Номер телефона некорректный. Введите ещё раз (только цифры и +):")
        return
    
    data = await state.get_data()
    date_str = data.get("selected_date")
    time_str = data.get("selected_time")
    client_name = data.get("client_name")
    
    if not all([date_str, time_str, client_name]):
        await message.answer("Произошла ошибка. Начните запись заново командой /start")
        await state.clear()
        return
    
    # Создаём запись в БД
    success = await create_booking(
        user_id=message.from_user.id,
        client_name=client_name,
        phone=phone,
        date_str=date_str,
        time_str=time_str
    )
    
    if not success:
        await message.answer(
            "❌ Не удалось создать запись. Возможно, слот уже занят или у вас уже есть запись.\n"
            "Попробуйте выбрать другое время.",
            reply_markup=get_main_menu_keyboard(is_subscribed=True)
        )
        await state.clear()
        return
    
    # Планируем напоминание (если >24ч)
    booking = await get_user_booking(message.from_user.id)
    if booking:
        await schedule_reminder(
            bot=bot,
            user_id=message.from_user.id,
            date_str=date_str,
            time_str=time_str,
            booking_id=booking["id"]
        )
    
    # Уведомление админа (с кликабельным контактом + кнопки)
    from config import ADMIN_ID
    user = message.from_user
    
    if user.username:
        contact = f'<a href="https://t.me/{user.username}">@{user.username}</a>'
        contact_url = f"https://t.me/{user.username}"
    else:
        contact = f'<a href="tg://user?id={user.id}">Написать клиенту</a>'
        contact_url = f"tg://user?id={user.id}"
    
    admin_text = (
        f"🆕 <b>НОВАЯ ЗАПИСЬ!</b>\n\n"
        f"👤 Клиент: <b>{client_name}</b> ({contact})\n"
        f"📞 Телефон: <code>{phone}</code>\n"
        f"📅 Дата: <b>{date_str}</b>\n"
        f"🕐 Время: <b>{time_str}</b>\n"
        f"🆔 User ID: <code>{user.id}</code>"
    )
    
    # Клавиатура с быстрыми действиями
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Написать клиенту", url=contact_url)],
        [InlineKeyboardButton(text="❌ Отменить эту запись", callback_data=f"admin_cancel_from_notif:{booking['id']}")]
    ])
    
    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML", reply_markup=admin_kb)
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление админу: {e}")
    
    # Пост в канал (если нужно)
    from config import CHANNEL_ID
    channel_text = (
        f"💅 <b>Новая запись на маникюр</b>\n\n"
        f"📅 {date_str} в {time_str}\n"
        f"👤 {client_name}"
    )
    try:
        await bot.send_message(CHANNEL_ID, channel_text, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Не удалось отправить в канал: {e}")
    
    # Сообщение пользователю
    success_text = (
        f"✅ <b>Запись успешно создана!</b>\n\n"
        f"📅 <b>Дата:</b> {date_str}\n"
        f"🕐 <b>Время:</b> {time_str}\n"
        f"👤 <b>Имя:</b> {client_name}\n"
        f"📞 <b>Телефон:</b> {phone}\n\n"
        f"Напоминание придёт за 24 часа до визита.\n"
        f"Чтобы отменить — используйте меню."
    )
    
    await message.answer(
        success_text,
        reply_markup=get_main_menu_keyboard(is_subscribed=True),
        parse_mode="HTML"
    )
    
    await state.clear()


@router.callback_query(F.data == "confirm_cancel_my")
async def confirm_cancel_my_booking(callback: CallbackQuery, bot):
    """Подтверждённая отмена своей записи."""
    user_id = callback.from_user.id
    booking = await get_user_booking(user_id)
    
    if not booking:
        await callback.message.edit_text(
            "У вас нет активной записи.",
            reply_markup=get_main_menu_keyboard(is_subscribed=True)
        )
        await callback.answer()
        return
    
    booking_id = booking["id"]
    
    # Удаляем напоминание
    await remove_reminder(booking_id, user_id)
    
    # Отменяем в БД
    success = await cancel_booking(user_id)
    
    if success:
        text = (
            "✅ <b>Ваша запись отменена.</b>\n\n"
            f"Освободилось время: {booking['date']} {booking['time']}"
        )
        # Уведомляем админа
        from config import ADMIN_ID
        try:
            await bot.send_message(
                ADMIN_ID,
                f"❌ Клиент отменил запись:\n"
                f"👤 {booking['client_name']}\n"
                f"📅 {booking['date']} {booking['time']}",
                parse_mode="HTML"
            )
        except:
            pass
    else:
        text = "❌ Не удалось отменить запись. Обратитесь к мастеру."
    
    await callback.message.edit_text(
        text,
        reply_markup=get_main_menu_keyboard(is_subscribed=True),
        parse_mode="HTML"
    )
    await callback.answer()


print("✅ Booking-обработчики готовы")