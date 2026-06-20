"""
Админ-панель (доступ только по ADMIN_ID).
"""
import logging
from aiogram import Router, F

logger = logging.getLogger(__name__)
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from datetime import datetime
from config import ADMIN_ID
from keyboards import (
    get_admin_main_keyboard,
    get_admin_dates_keyboard,
    get_admin_cancel_booking_keyboard,
    get_back_keyboard,
    get_admin_after_cancel_keyboard
)
from states import AdminStates
from database import (
    add_time_slot,
    remove_time_slot,
    get_all_time_slots,
    close_day,
    open_day,
    get_closed_days,
    get_all_bookings_for_date,
    get_booking_by_id,
    admin_cancel_booking,
    get_user_count,
    get_available_dates
)

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Вход в админ-панель по команде /admin."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    
    await state.clear()
    await message.answer(
        "👑 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    
    await state.clear()
    await callback.message.edit_text(
        "👑 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_panel_from_menu")
async def admin_panel_from_main_menu(callback: CallbackQuery, state: FSMContext):
    """Открытие админ-панели из главного меню (кнопка для админа)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    
    await state.clear()
    await callback.message.edit_text(
        "👑 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_view_date")
async def admin_choose_date_to_view(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔", show_alert=True)
    
    await callback.message.edit_text(
        "📅 Выберите дату для просмотра расписания:",
        reply_markup=get_admin_dates_keyboard([]),  # генерит все даты
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.viewing_date)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_date:"), AdminStates.viewing_date)
async def admin_view_schedule_for_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split(":")[1]
    
    bookings = await get_all_bookings_for_date(date_str)
    closed = await get_closed_days()
    is_closed = date_str in closed
    
    text = f"📋 <b>Расписание на {date_str}</b>\n\n"
    
    if is_closed:
        text += "🚫 <b>День закрыт администратором</b>\n\n"
    
    if bookings:
        text += "<b>Записи:</b>\n"
        for b in bookings:
            text += f"• {b['time']} — {b['client_name']} ({b['phone']})\n"
    else:
        text += "Свободных записей нет.\n"
    
    # Показать свободные слоты
    from database import get_available_times_for_date
    free = await get_available_times_for_date(date_str)
    if free:
        text += f"\n🕐 Свободно: {', '.join(free)}"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "admin_add_slot")
async def admin_add_slot_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔", show_alert=True)
    
    current_slots = await get_all_time_slots()
    text = (
        f"➕ <b>Добавление временного слота</b>\n\n"
        f"Текущие слоты: {', '.join(current_slots)}\n\n"
        f"Введите новое время в формате <b>HH:MM</b> (например: 20:00)"
    )
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(AdminStates.adding_time_slot)
    await callback.answer()


@router.message(AdminStates.adding_time_slot)
async def admin_add_slot_process(message: Message, state: FSMContext):
    time_str = message.text.strip()
    
    # Валидация формата
    try:
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await message.answer("❌ Неверный формат. Введите время как HH:MM (пример: 09:30)")
        return
    
    success = await add_time_slot(time_str)
    
    if success:
        await message.answer(
            f"✅ Слот <b>{time_str}</b> успешно добавлен!",
            reply_markup=get_admin_main_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"⚠️ Слот {time_str} уже существует.",
            reply_markup=get_admin_main_keyboard()
        )
    
    await state.clear()


@router.callback_query(F.data == "admin_remove_slot")
async def admin_remove_slot_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔", show_alert=True)
    
    slots = await get_all_time_slots()
    if not slots:
        await callback.message.edit_text(
            "Нет слотов для удаления.",
            reply_markup=get_admin_main_keyboard()
        )
        await state.clear()
        return
    
    text = "➖ Выберите слот для удаления:\n\n" + "\n".join([f"• {s}" for s in slots])
    # Для простоты — просим ввести время текстом
    text += "\n\nВведите время слота, который нужно удалить (HH:MM):"
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(AdminStates.removing_time_slot)
    await callback.answer()


@router.message(AdminStates.removing_time_slot)
async def admin_remove_slot_process(message: Message, state: FSMContext):
    time_str = message.text.strip()
    
    success = await remove_time_slot(time_str)
    
    if success:
        await message.answer(
            f"✅ Слот <b>{time_str}</b> удалён.",
            reply_markup=get_admin_main_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"❌ Слот {time_str} не найден.",
            reply_markup=get_admin_main_keyboard()
        )
    
    await state.clear()


@router.callback_query(F.data == "admin_close_day")
async def admin_close_day_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔", show_alert=True)
    
    await callback.message.edit_text(
        "🚫 Введите дату для закрытия в формате <b>YYYY-MM-DD</b>\n"
        "Например: 2026-07-15",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.closing_day)
    await callback.answer()


@router.message(AdminStates.closing_day)
async def admin_close_day_process(message: Message, state: FSMContext):
    date_str = message.text.strip()
    
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте YYYY-MM-DD")
        return
    
    success = await close_day(date_str)
    
    if success:
        await message.answer(
            f"✅ День <b>{date_str}</b> закрыт для записи.",
            reply_markup=get_admin_main_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"⚠️ День {date_str} уже был закрыт.",
            reply_markup=get_admin_main_keyboard()
        )
    
    await state.clear()


@router.callback_query(F.data == "admin_open_day")
async def admin_open_day_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔", show_alert=True)
    
    closed = await get_closed_days()
    if not closed:
        await callback.message.edit_text(
            "Нет закрытых дней.",
            reply_markup=get_admin_main_keyboard()
        )
        await state.clear()
        return
    
    text = "🔓 Закрытые дни:\n" + "\n".join([f"• {d}" for d in closed])
    text += "\n\nВведите дату для открытия (YYYY-MM-DD):"
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(AdminStates.opening_day)
    await callback.answer()


@router.message(AdminStates.opening_day)
async def admin_open_day_process(message: Message, state: FSMContext):
    date_str = message.text.strip()
    
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте YYYY-MM-DD")
        return
    
    success = await open_day(date_str)
    
    await message.answer(
        f"✅ День <b>{date_str}</b> {'открыт' if success else 'не был закрыт'}.",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )
    await state.clear()


@router.callback_query(F.data == "admin_cancel_booking")
async def admin_choose_booking_to_cancel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔", show_alert=True)
    
    # Показываем ВСЕ будущие записи (а не только сегодня/завтра)
    all_bookings = await get_all_future_bookings()
    
    if not all_bookings:
        await callback.message.edit_text(
            "Нет будущих записей.",
            reply_markup=get_admin_main_keyboard()
        )
        return
    
    await callback.message.edit_text(
        "❌ Выберите запись для отмены (все будущие записи):",
        reply_markup=get_admin_cancel_booking_keyboard(all_bookings),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.cancelling_booking)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_cancel_from_notif:"))
async def admin_cancel_from_notification(callback: CallbackQuery, state: FSMContext):
    """Отмена записи прямо из уведомления о новой записи."""
    booking_id = int(callback.data.split(":")[1])
    
    booking = await get_booking_by_id(booking_id)
    if not booking:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    
    await state.update_data(
        cancel_booking_id=booking_id,
        cancel_user_id=booking["user_id"],
        cancel_date=booking["date"],
        cancel_time=booking["time"],
        cancel_client_name=booking["client_name"]
    )
    
    text = (
        f"❌ <b>Отмена записи #{booking_id}</b>\n\n"
        f"Клиент: <b>{booking['client_name']}</b>\n"
        f"📅 {booking['date']} в {booking['time']}\n\n"
        f"Введите причину отмены (или напишите «без причины»):"
    )
    
    await callback.message.answer(text, parse_mode="HTML")
    await state.set_state(AdminStates.entering_cancel_reason)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_cancel:"), AdminStates.cancelling_booking)
async def admin_cancel_specific_booking(callback: CallbackQuery, state: FSMContext):
    """Админ выбрал запись для отмены — просим ввести причину."""
    booking_id = int(callback.data.split(":")[1])
    
    booking = await get_booking_by_id(booking_id)
    if not booking:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    
    # Сохраняем данные записи во FSM
    await state.update_data(
        cancel_booking_id=booking_id,
        cancel_user_id=booking["user_id"],
        cancel_date=booking["date"],
        cancel_time=booking["time"],
        cancel_client_name=booking["client_name"]
    )
    
    text = (
        f"❌ <b>Отмена записи #{booking_id}</b>\n\n"
        f"Клиент: <b>{booking['client_name']}</b>\n"
        f"📅 {booking['date']} в {booking['time']}\n\n"
        f"Введите <b>причину отмены</b> (она будет отправлена клиенту):\n"
        f"Или напишите <code>без причины</code>, если причина не нужна."
    )
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(AdminStates.entering_cancel_reason)
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔", show_alert=True)
    
    total_users = await get_user_count()
    closed_days = await get_closed_days()
    available_dates = await get_available_dates()
    
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей с записями: <b>{total_users}</b>\n"
        f"📅 Доступных дат: <b>{len(available_dates)}</b>\n"
        f"🚫 Закрытых дней: <b>{len(closed_days)}</b>\n"
        f"Закрытые даты: {', '.join(closed_days) if closed_days else 'нет'}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.entering_cancel_reason)
async def admin_process_cancel_reason(message: Message, state: FSMContext, bot):
    """Админ ввёл причину отмены — отменяем запись и уведомляем клиента."""
    data = await state.get_data()
    booking_id = data.get("cancel_booking_id")
    user_id = data.get("cancel_user_id")
    date_str = data.get("cancel_date")
    time_str = data.get("cancel_time")
    client_name = data.get("cancel_client_name")
    
    if not booking_id:
        await message.answer("Ошибка. Начните отмену заново через админ-панель.")
        await state.clear()
        return
    
    reason = message.text.strip()
    
    # Если админ написал "без причины" или пусто — используем стандартный текст
    if reason.lower() in ["без причины", "нет", "не нужно", ""]:
        reason_text = "По техническим причинам / личным обстоятельствам мастера."
    else:
        reason_text = reason
    
    # Удаляем напоминание
    from scheduler import remove_reminder
    await remove_reminder(booking_id, user_id)
    
    # Отменяем в БД
    success = await admin_cancel_booking(booking_id)
    
    if success:
        # Уведомляем клиента с причиной
        cancel_message = (
            f"❌ <b>Ваша запись отменена администратором.</b>\n\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Время: {time_str}\n\n"
            f"📝 <b>Причина:</b> {reason_text}\n\n"
            f"Приносим извинения за неудобства. Вы можете записаться на другое время."
        )
        try:
            await bot.send_message(user_id, cancel_message, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Не удалось уведомить клиента {user_id}: {e}")
        
        text = f"✅ Запись #{booking_id} отменена.\nПричина отправлена клиенту."
    else:
        text = "❌ Не удалось отменить запись."
    
    await message.answer(
        text,
        reply_markup=get_admin_after_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.clear()


print("✅ Admin-обработчики готовы")