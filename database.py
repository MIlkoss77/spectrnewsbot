"""Подписчики бота: кто нажал /start и получил бесплатный гайд.

Таблица одна: для воронки нужен только список людей и их число. Все служебные
таблицы старой базы (topics/posts/post_log) не переносятся — контент у нас
генерируется из content/topic_pool.py и нигде не хранится.
"""
import logging
from typing import Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)


async def init_db(db_path: str) -> None:
    """Создать таблицу подписчиков, если её ещё нет."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)
        await db.commit()
    logger.info("База подписчиков готова: %s", db_path)


async def add_subscriber(
    db_path: str,
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
) -> None:
    """Записать нажавшего /start; повторный запуск обновляет данные, не дублирует."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO subscribers (user_id, username, first_name)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   username = excluded.username,
                   first_name = excluded.first_name,
                   is_active = 1""",
            (user_id, username, first_name),
        )
        await db.commit()


async def get_subscriber_count(db_path: str) -> int:
    """Сколько человек получили гайд."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM subscribers WHERE is_active = 1"
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_active_subscribers(db_path: str) -> List[Dict]:
    """Список подписчиков, например для рассылки."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT user_id, username, first_name FROM subscribers WHERE is_active = 1"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
