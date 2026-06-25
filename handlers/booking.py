"""
Обработчики процесса бронирования.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards import get_main_menu_keyboard
from database import (
    get_available_dates,
    get_available_times_for_date,
    create_booking
)

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("date:"))
async def select_date(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    date = callback.data.split(":")[1]
    await state.update_data(selected_date=date)

    from .keyboards import get_time_keyboard
    await callback.message.edit_text(
        f"📅 Вы выбрали дату: {date}\n\nВыберите время:",
        reply_markup=get_time_keyboard(date)
    )


@router.callback_query(F.data.startswith("time:"))
async def select_time(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    _, date, time = callback.data.split(":")
    user_id = callback.from_user.id

    success = await create_booking(user_id, date, time)

    if success:
        await callback.message.edit_text(
            f"✅ Вы успешно записаны!\n\n📅 {date} в {time}",
            reply_markup=get_main_menu_keyboard(is_subscribed=True)
        )
    else:
        await callback.message.edit_text(
            "❌ Не удалось создать запись. Возможно, это время уже занято.",
            reply_markup=get_main_menu_keyboard(is_subscribed=True)
        )


# Пример: если есть кнопка "Назад"
@router.callback_query(F.data == "back_to_dates")
async def back_to_dates(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    # Здесь можно вернуть пользователя к выбору даты
    from . import show_available_dates
    await show_available_dates(callback, state)
