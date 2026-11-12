"""Модуль выдачи и контроля 7-дневного бонусного доступа в SPECTR CLUB.

Используется для покупателей полного гайда («НЕЙРО ПРОТОКОЛЫ» / «Нейро-Хакер»):
- По deep-link ?start=trial7 бот выдаёт персональную одноразовую ссылку
  в закрытый канал (PREMIUM_CHANNEL_ID) и фиксирует таймер на 7 дней.
- На 6-й день (за 24 часа до окончания) присылает напоминание с кнопкой продления (990 ₽/мес).
- Через 7 дней автоматически исключает пользователя из канала (ban + unban,
  чтобы пользователь мог вернуться после оплаты) и присылает кнопку возврата.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional, Tuple

import aiosqlite
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config

logger = logging.getLogger(__name__)

TRIAL_DURATION_SECONDS = 7 * 86400
REMIND_BEFORE_SECONDS = 24 * 3600


async def init_trial_db(db_path: str = config.FUNNEL_DB_PATH) -> None:
    """Создать таблицу учёта 7-дневных триалов в SPECTR CLUB."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS club_trials (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                granted_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                reminded_day6 INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                source TEXT DEFAULT 'trial7'
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_trials_status_exp ON club_trials (status, expires_at)"
        )
        await db.commit()


def build_renew_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Кнопка продления подписки на SPECTR CLUB (990 ₽/мес)."""
    channel_link = config.payment_link_for("channel", user_id) or "https://spectrmind.ru"
    price = config.PAID_CHANNEL_PRICE or "990₽"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🔒 Продлить SPECTR CLUB — {price}/мес",
                    url=channel_link,
                )
            ]
        ]
    )


async def activate_7day_trial(
    bot: Bot,
    user_id: int,
    username: Optional[str] = None,
    source: str = "trial7",
    db_path: str = config.FUNNEL_DB_PATH,
    now_ts: Optional[int] = None,
) -> Tuple[bool, str]:
    """Активировать 7-дневный бонусный доступ в SPECTR CLUB для покупателя гайда.

    Возвращает (success, payload):
    - при success=True payload содержит одноразовую инвайт-ссылку;
    - при success=False payload содержит человекочитаемую причину отказа.
    """
    await init_trial_db(db_path)

    if not config.PREMIUM_CHANNEL_ID:
        return False, "Закрытый канал временно не настроен. Напишите в поддержку."

    if now_ts is None:
        now_ts = int(datetime.now(timezone.utc).timestamp())

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT status, expires_at FROM club_trials WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()

    if row:
        status = row["status"]
        expires_at = row["expires_at"]
        if status == "converted":
            return False, "У тебя уже активна полная подписка SPECTR CLUB."
        if status == "active" and expires_at > now_ts:
            days_left = max(1, (expires_at - now_ts + 86399) // 86400)
            return (
                False,
                f"Твой 7-дневный доступ в SPECTR CLUB уже активирован (осталось дней: {days_left}).",
            )
        return (
            False,
            "Пробный 7-дневный период в SPECTR CLUB уже был использован ранее. "
            "Чтобы вернуться в закрытый канал, оформи подписку по кнопке ниже 👇",
        )

    try:
        invite = await bot.create_chat_invite_link(
            chat_id=config.PREMIUM_CHANNEL_ID,
            member_limit=1,
            name=f"Trial 7d user {user_id}",
        )
        invite_url = invite.invite_link
    except TelegramAPIError as exc:
        logger.exception("Не удалось создать инвайт-ссылку для trial user_id=%s", user_id)
        return False, f"Ошибка генерации пропуска: {exc}"

    expires_at = now_ts + TRIAL_DURATION_SECONDS
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO club_trials (user_id, username, granted_at, expires_at, reminded_day6, status, source)
            VALUES (?, ?, ?, ?, 0, 'active', ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                granted_at = excluded.granted_at,
                expires_at = excluded.expires_at,
                reminded_day6 = 0,
                status = 'active',
                source = excluded.source
            """,
            (user_id, username, now_ts, expires_at, source),
        )
        await db.commit()

    logger.info("Выдан 7-дневный доступ в SPECTR CLUB для user_id=%s (@%s)", user_id, username or "-")
    return True, invite_url


async def mark_trial_converted(user_id: int, db_path: str = config.FUNNEL_DB_PATH) -> bool:
    """Пометить триал как оплаченный (пользователь не будет удалён на 7-й день)."""
    await init_trial_db(db_path)
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "UPDATE club_trials SET status = 'converted' WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()
        return cursor.rowcount > 0


async def process_club_trials(
    bot: Bot,
    db_path: str = config.FUNNEL_DB_PATH,
    now_ts: Optional[int] = None,
) -> Tuple[int, int]:
    """Обработать напоминания (6-й день) и исключения (7-й день).

    Возвращает (reminded_count, expired_count).
    """
    await init_trial_db(db_path)
    if now_ts is None:
        now_ts = int(datetime.now(timezone.utc).timestamp())

    reminded_count = 0
    expired_count = 0

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        # 1. Напоминание за 24 часа до конца 7-дневного срока (6-й день)
        remind_threshold = now_ts + REMIND_BEFORE_SECONDS
        cursor = await db.execute(
            """
            SELECT user_id FROM club_trials
            WHERE status = 'active' AND reminded_day6 = 0
              AND expires_at <= ? AND expires_at > ?
            """,
            (remind_threshold, now_ts),
        )
        to_remind = [r["user_id"] for r in await cursor.fetchall()]

        # 2. Истёкшие триалы (прошло >= 7 дней)
        cursor = await db.execute(
            """
            SELECT user_id FROM club_trials
            WHERE status = 'active' AND expires_at <= ?
            """,
            (now_ts,),
        )
        to_expire = [r["user_id"] for r in await cursor.fetchall()]

    for uid in to_remind:
        try:
            await bot.send_message(
                chat_id=uid,
                text=(
                    "⏳ <b>Напоминание: через 24 часа завершается твой 7-дневный бонусный доступ в SPECTR CLUB.</b>\n\n"
                    "Чтобы продолжить получать утренние микро-протоколы в 8:00, разборы исследований и поддержку комьюнити — "
                    "продли подписку по кнопке ниже 👇"
                ),
                parse_mode="HTML",
                reply_markup=build_renew_keyboard(uid),
                disable_web_page_preview=True,
            )
            reminded_count += 1
        except TelegramForbiddenError:
            logger.info("Пользователь %s заблокировал бота (напоминание 6-го дня)", uid)
        except TelegramAPIError as exc:
            logger.warning("Ошибка напоминания триала user_id=%s: %s", uid, exc)

        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "UPDATE club_trials SET reminded_day6 = 1 WHERE user_id = ?",
                (uid,),
            )
            await db.commit()

    for uid in to_expire:
        if config.PREMIUM_CHANNEL_ID:
            try:
                # Исключение без вечного бана: ban + сразу unban
                await bot.ban_chat_member(chat_id=config.PREMIUM_CHANNEL_ID, user_id=uid)
                await bot.unban_chat_member(
                    chat_id=config.PREMIUM_CHANNEL_ID,
                    user_id=uid,
                    only_if_banned=True,
                )
                logger.info("Исключён по истечении 7 дней из SPECTR CLUB: user_id=%s", uid)
            except TelegramAPIError as exc:
                logger.warning("Не удалось исключить user_id=%s из канала: %s", uid, exc)

        try:
            await bot.send_message(
                chat_id=uid,
                text=(
                    "⌛️ <b>Твой 7-дневный бонусный период в SPECTR CLUB завершён.</b>\n\n"
                    "Доступ к закрытому каналу закрыт. Если хочешь вернуться и продолжить работу "
                    "по утренним протоколам — оформи подписку в один клик 👇"
                ),
                parse_mode="HTML",
                reply_markup=build_renew_keyboard(uid),
                disable_web_page_preview=True,
            )
        except (TelegramForbiddenError, TelegramAPIError):
            pass

        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "UPDATE club_trials SET status = 'expired' WHERE user_id = ?",
                (uid,),
            )
            await db.commit()
        expired_count += 1

    return reminded_count, expired_count


async def get_trial_stats(db_path: str = config.FUNNEL_DB_PATH) -> Dict[str, Any]:
    """Статистика 7-дневных триалов для админа."""
    await init_trial_db(db_path)
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT status, COUNT(*) FROM club_trials GROUP BY status"
        )
        counts = dict(await cursor.fetchall())
    return {
        "active": counts.get("active", 0),
        "expired": counts.get("expired", 0),
        "converted": counts.get("converted", 0),
    }
