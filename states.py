"""
FSM состояния для бота записи на маникюр.
"""
from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    """Состояния процесса бронирования."""
    choosing_date = State()      # Выбор даты из календаря
    choosing_time = State()      # Выбор времени
    entering_name = State()      # Ввод имени
    entering_phone = State()     # Ввод телефона
    confirming = State()         # Подтверждение записи


class AdminStates(StatesGroup):
    """Состояния админ-панели."""
    choosing_action = State()
    adding_time_slot = State()
    removing_time_slot = State()
    closing_day = State()
    opening_day = State()
    viewing_date = State()
    cancelling_booking = State()
    entering_cancel_reason = State()
    changing_booking_time = State()  # Изменение времени записи админом