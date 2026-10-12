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
    """Создать таблицу подписчиков и, при необходимости, мигрировать её."""
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
        # Метка источника приходит из ссылки вида t.me/bot?start=ig.
        # Колонка добавляется отдельно, чтобы не потерять уже собранную базу.
        cursor = await db.execute("PRAGMA table_info(subscribers)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "source" not in columns:
            await db.execute("ALTER TABLE subscribers ADD COLUMN source TEXT")
            logger.info("Добавлена колонка source в таблицу подписчиков")
        await db.commit()
    logger.info("База подписчиков готова: %s", db_path)


async def add_subscriber(
    db_path: str,
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    source: Optional[str] = None,
) -> None:
    """Записать нажавшего /start; повторный запуск обновляет данные, не дублирует.

    ``source`` — метка из deep-link (``?start=ig``). Пустое значение не затирает
    уже известный источник: человек мог прийти из инсты, а позже открыть бота
    по прямой ссылке.
    """
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO subscribers (user_id, username, first_name, source)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   username = excluded.username,
                   first_name = excluded.first_name,
                   source = COALESCE(excluded.source, subscribers.source),
                   is_active = 1""",
            (user_id, username, first_name, source or None),
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


async def get_source_stats(db_path: str) -> List[Dict]:
    """Разбивка подписчиков по источнику: t.me/bot?start=<метка>.

    Люди, пришедшие по ссылке без метки, попадают в «без метки».
    """
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """SELECT COALESCE(NULLIF(TRIM(source), ''), 'без метки') AS src,
                      COUNT(*) AS total
               FROM subscribers
               WHERE is_active = 1
               GROUP BY src
               ORDER BY total DESC"""
        )
        rows = await cursor.fetchall()
        return [{"source": row[0], "count": row[1]} for row in rows]


async def get_active_subscribers(db_path: str) -> List[Dict]:
    """Список подписчиков, например для рассылки."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT user_id, username, first_name FROM subscribers WHERE is_active = 1"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
