"""
Модуль планировщика напоминаний (APScheduler + aiogram).
"""
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from typing import Optional
from aiogram import Bot
from config import REMINDER_TEXT
from database import get_all_future_bookings, get_user_booking

logger = logging.getLogger(__name__)

scheduler: Optional[AsyncIOScheduler] = None


def init_scheduler() -> AsyncIOScheduler:
    """Инициализация планировщика."""
    global scheduler
    if scheduler is None:
        jobstores = {
            'default': MemoryJobStore()
        }
        scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="Europe/Moscow")
        scheduler.start()
        logger.info("✅ APScheduler запущен")
    return scheduler


async def send_reminder(bot: Bot, user_id: int, time_str: str, date_str: str):
    """Отправка напоминания пользователю."""
    try:
        text = REMINDER_TEXT.format(time=time_str)
        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="HTML"
        )
        logger.info(f"Напоминание отправлено пользователю {user_id} на {date_str} {time_str}")
    except Exception as e:
        logger.error(f"Ошибка отправки напоминания пользователю {user_id}: {e}")


async def schedule_reminder(
    bot: Bot,
    user_id: int,
    date_str: str,
    time_str: str,
    booking_id: int
) -> bool:
    """
    Запланировать напоминание за 24 часа до записи.
    Если до записи меньше 24 часов — не планируем.
    """
    try:
        # Парсим дату и время записи
        appointment_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        now = datetime.now()
        
        # Если запись меньше чем через 24 часа — не создаём напоминание
        if appointment_dt - now < timedelta(hours=24):
            logger.info(f"Напоминание для {user_id} не создано (менее 24ч до записи)")
            return False
        
        # Время отправки напоминания = appointment_dt - 24 часа
        reminder_time = appointment_dt - timedelta(hours=24)
        
        job_id = f"reminder_{booking_id}_{user_id}"
        
        # Удаляем старую задачу если есть
        if scheduler and scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
        
        scheduler.add_job(
            send_reminder,
            trigger='date',
            run_date=reminder_time,
            args=[bot, user_id, time_str, date_str],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=3600  # 1 час на выполнение если просрочили
        )
        
        logger.info(f"Напоминание запланировано для user_id={user_id} на {reminder_time}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка планирования напоминания: {e}")
        return False


async def remove_reminder(booking_id: int, user_id: int) -> None:
    """Удалить запланированное напоминание при отмене записи."""
    if not scheduler:
        return
    job_id = f"reminder_{booking_id}_{user_id}"
    try:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            logger.info(f"Напоминание удалено: {job_id}")
    except Exception as e:
        logger.warning(f"Не удалось удалить job {job_id}: {e}")


async def restore_reminders(bot: Bot) -> None:
    """
    Восстановить все напоминания при запуске бота.
    Вызывается в main после init_db.
    """
    if not scheduler:
        init_scheduler()
    
    future_bookings = await get_all_future_bookings()
    restored_count = 0
    
    for booking in future_bookings:
        user_id = booking["user_id"]
        date_str = booking["date"]
        time_str = booking["time"]
        booking_id = booking["id"]
        
        # Пытаемся запланировать (функция сама проверит >24ч)
        success = await schedule_reminder(bot, user_id, date_str, time_str, booking_id)
        if success:
            restored_count += 1
    
    logger.info(f"Восстановлено {restored_count} напоминаний из базы данных")


def shutdown_scheduler() -> None:
    """Остановка планировщика."""
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler остановлен")


print("✅ Модуль scheduler.py готов")