"""
Модуль работы с базой данных SQLite (aiosqlite).
"""
import aiosqlite
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
from config import DATABASE_NAME, DEFAULT_TIME_SLOTS, SCHEDULE_DAYS_AHEAD

logger = logging.getLogger(__name__)

DB_PATH = DATABASE_NAME


async def init_db() -> None:
    """Инициализация базы данных и создание таблиц."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица записей клиентов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                client_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                date TEXT NOT NULL,           -- YYYY-MM-DD
                time TEXT NOT NULL,           -- HH:MM
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица временных слотов (глобальные)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS time_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT UNIQUE NOT NULL
            )
        """)

        # Таблица закрытых дней
        await db.execute("""
            CREATE TABLE IF NOT EXISTS closed_days (
                date TEXT PRIMARY KEY,
                closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT DEFAULT 'Закрыт администратором'
            )
        """)

        # Всегда добавляем стандартные слоты, если их нет (INSERT OR IGNORE)
        for t in DEFAULT_TIME_SLOTS:
            await db.execute(
                "INSERT OR IGNORE INTO time_slots (time) VALUES (?)", (t,)
            )
        logger.info("Стандартные временные слоты проверены/добавлены")

        await db.commit()
        logger.info("✅ База данных инициализирована")


async def get_all_time_slots() -> List[str]:
    """Получить все доступные временные слоты."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT time FROM time_slots ORDER BY time")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def add_time_slot(time_str: str) -> bool:
    """Добавить новый временной слот."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT INTO time_slots (time) VALUES (?)", (time_str,))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False  # уже существует


async def remove_time_slot(time_str: str) -> bool:
    """Удалить временной слот."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM time_slots WHERE time = ?", (time_str,))
        await db.commit()
        return cursor.rowcount > 0


async def is_day_closed(date_str: str) -> bool:
    """Проверить, закрыт ли день."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM closed_days WHERE date = ?", (date_str,))
        return await cursor.fetchone() is not None


async def close_day(date_str: str, reason: str = "Закрыт администратором") -> bool:
    """Закрыть день для записи."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO closed_days (date, reason) VALUES (?, ?)",
                (date_str, reason)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False  # уже закрыт


async def open_day(date_str: str) -> bool:
    """Открыть ранее закрытый день."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM closed_days WHERE date = ?", (date_str,))
        await db.commit()
        return cursor.rowcount > 0


async def get_closed_days() -> List[str]:
    """Получить список закрытых дней."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT date FROM closed_days ORDER BY date")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def get_available_dates() -> List[str]:
    """
    Получить список доступных дат на SCHEDULE_DAYS_AHEAD дней вперед.
    Дата доступна, если:
    - не закрыта
    - есть хотя бы один свободный слот
    """
    from datetime import datetime, timedelta
    today = datetime.now().date()
    dates = []
    for i in range(SCHEDULE_DAYS_AHEAD + 1):
        d = today + timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        if await is_day_closed(date_str):
            continue
        # Проверить, есть ли свободные слоты
        free_times = await get_available_times_for_date(date_str)
        if free_times:
            dates.append(date_str)
    return dates


async def get_available_times_for_date(date_str: str) -> List[str]:
    """Получить свободные времена для конкретной даты."""
    if await is_day_closed(date_str):
        return []

    all_slots = await get_all_time_slots()
    if not all_slots:
        return []

    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем занятые времена на эту дату
        cursor = await db.execute(
            "SELECT time FROM bookings WHERE date = ?",
            (date_str,)
        )
        booked_times = {row[0] for row in await cursor.fetchall()}

    available = [t for t in all_slots if t not in booked_times]
    return sorted(available)


async def create_booking(
    user_id: int,
    client_name: str,
    phone: str,
    date_str: str,
    time_str: str
) -> bool:
    """
    Создать запись. Пользователь может иметь только одну активную запись.
    """
    # Проверка: уже есть запись у пользователя?
    existing = await get_user_booking(user_id)
    if existing:
        return False

    # Проверка доступности слота
    available = await get_available_times_for_date(date_str)
    if time_str not in available:
        return False

    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                """
                INSERT INTO bookings (user_id, client_name, phone, date, time)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, client_name, phone, date_str, time_str)
            )
            await db.commit()
            logger.info(f"Создана запись: user_id={user_id}, {date_str} {time_str}")
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_user_booking(user_id: int) -> Optional[Dict[str, Any]]:
    """Получить текущую запись пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT id, client_name, phone, date, time, created_at
            FROM bookings WHERE user_id = ?
            """,
            (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "client_name": row[1],
                "phone": row[2],
                "date": row[3],
                "time": row[4],
                "created_at": row[5]
            }
        return None


async def cancel_booking(user_id: int) -> bool:
    """Отменить запись пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM bookings WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_booking_by_id(booking_id: int) -> Optional[Dict[str, Any]]:
    """Получить запись по ID (для админа)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT id, user_id, client_name, phone, date, time, created_at
            FROM bookings WHERE id = ?
            """,
            (booking_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "user_id": row[1],
                "client_name": row[2],
                "phone": row[3],
                "date": row[4],
                "time": row[5],
                "created_at": row[6]
            }
        return None


async def get_all_bookings_for_date(date_str: str) -> List[Dict[str, Any]]:
    """Получить все записи на конкретную дату (для админа)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT id, user_id, client_name, phone, time, created_at
            FROM bookings WHERE date = ? ORDER BY time
            """,
            (date_str,)
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "user_id": r[1],
                "client_name": r[2],
                "phone": r[3],
                "time": r[4],
                "created_at": r[5]
            }
            for r in rows
        ]


async def get_all_future_bookings() -> List[Dict[str, Any]]:
    """Получить все будущие записи (для восстановления напоминаний)."""
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT id, user_id, client_name, phone, date, time
            FROM bookings 
            WHERE date >= ?
            ORDER BY date, time
            """,
            (today,)
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "user_id": r[1],
                "client_name": r[2],
                "phone": r[3],
                "date": r[4],
                "time": r[5]
            }
            for r in rows
        ]


async def admin_cancel_booking(booking_id: int) -> bool:
    """Отменить любую запись (для админа)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM bookings WHERE id = ?",
            (booking_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_user_count() -> int:
    """Количество уникальных пользователей с записями."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(DISTINCT user_id) FROM bookings")
        return (await cursor.fetchone())[0]


async def get_bookings_count_last_days(days: int) -> int:
    """Количество записей за последние N дней."""
    from datetime import datetime, timedelta
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM bookings WHERE date >= ? AND date <= ?",
            (start_date, today)
        )
        return (await cursor.fetchone())[0]


async def update_booking_time(booking_id: int, new_time: str) -> bool:
    """
    Изменить время существующей записи (для админа).
    Проверяет, что новое время свободно на эту дату.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем дату записи
        cursor = await db.execute("SELECT date FROM bookings WHERE id = ?", (booking_id,))
        row = await cursor.fetchone()
        if not row:
            return False
        date_str = row[0]

        # Проверяем, свободно ли новое время
        cursor = await db.execute(
            "SELECT 1 FROM bookings WHERE date = ? AND time = ? AND id != ?",
            (date_str, new_time, booking_id)
        )
        if await cursor.fetchone():
            return False  # время уже занято

        # Обновляем время
        await db.execute(
            "UPDATE bookings SET time = ? WHERE id = ?",
            (new_time, booking_id)
        )
        await db.commit()
        return True


print("✅ Модуль database.py готов")