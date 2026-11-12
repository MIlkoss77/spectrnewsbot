"""Модуль автоворонки дожима для Spectr Mind (@spectrnewsbot).

Планирует и отправляет три отложенных касания после получения базового PDF-гайда:
- Шаг 1: через 15 минут (дофаминовые рецепторы, Semax/Selank, оффер на 1 990 ₽)
- Шаг 2: на следующий день ровно в 14:00 МСК (аденозиновый краш, оффер на 1 990 ₽)
- Шаг 3: через 48 часов (финальный выбор: гайд за 1 990 ₽ или клуб за 990 ₽)

Хранилище: SQLite (по умолчанию funnel_timers.db).
"""
import asyncio
from datetime import datetime, time, timedelta, timezone
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config

logger = logging.getLogger(__name__)

FUNNEL_DB_PATH = os.getenv("FUNNEL_DB_PATH", "funnel_timers.db")
MSK_TZ = timezone(timedelta(hours=3))

# ==============================================================================
# ТЕКСТЫ СООБЩЕНИЙ ВОРОНКИ (HTML)
# ==============================================================================

STEP_1_TEXT = (
    "⚡️ <b>Почему утреннего света и отказа от кофе хватит только на 20%?</b>\n\n"
    "Если ты уже открыл 5-ю страницу руководства, то увидел главную проблему: "
    "когда дофаминовые рецепторы D2 выгорали годами, одной коррекции утра недостаточно.\n\n"
    "Многие пытаются решить это горстями БАДов, янтарной кислотой, родиолой или "
    "аптечными пептидами (<b>Semax, Selank</b>). Но без точной схемы циклирования "
    "(<i>on/off periods</i>) мозг ловит рецепторную толерантность и жесткий откат уже через 14 дней.\n\n"
    "В полной системе <b>«SPECTRMIND // НЕЙРО ПРОТОКОЛЫ»</b> мы собрали:\n"
    "• <b>Календари циклирования (90 дней):</b> точные протоколы синергии (Semax, Selank, P21, адаптогены) без толерантности\n"
    "• <b>21-дневную систему</b> пошаговой перенастройки мозга\n"
    "• <b>Бонус:</b> 7 дней в закрытом клубе <b>SPECTR CLUB</b> (микро-протоколы каждое утро в 8:00)\n\n"
    "🎁 Специальная цена для читателей гайда: <b>1 990 ₽</b> вместо <s>3 990 ₽</s>."
)

STEP_2_TEXT = (
    "🕑 <b>Сейчас ~14:00. Почувствовал тяжесть в голове и потерю фокуса?</b>\n\n"
    "Прямо сейчас в твоем мозге закончилось действие утреннего кофеина, и "
    "накопленный за ночь аденозин обрушился на рецепторы. Префронтальная кора "
    "отключается, уступая место суете.\n\n"
    "Чтобы выдавать <b>4 часа сверхглубокой работы (Flow State) вместо 12 часов суеты</b>, "
    "нужно восстановить фазу глубокого сна <i>NREM Stage 3</i>, когда глимфатическая "
    "система вымывает нейротоксины.\n\n"
    "Забирай полную систему <b>«НЕЙРО ПРОТОКОЛЫ»</b> со скидкой 50%:\n"
    "• Архитектура сна (синхронизация NREM 3 и REM за 6–7 часов)\n"
    "• Дофаминовый детокс 2.0 (перезагрузка рецепторов D2 без срывов)\n"
    "• 90-дневные календари пептидов и адаптогенов + 7 дней в <b>SPECTR CLUB</b>"
)

STEP_3_TEXT = (
    "🧠 <b>Твой мозг принял решение за миллисекунды до того, как ты прочитал эту строчку.</b>\n\n"
    "Прошло 48 часов с момента, как ты скачал базовый протокол. Базовые привычки дают до 20% ресурса. "
    "Если ты готов забрать остальные 80% потенциала — выбирай свой формат старта:\n\n"
    "1️⃣ <b>Полная система «НЕЙРО ПРОТОКОЛЫ» + 7 дней в SPECTR CLUB</b> — <b>1 990 ₽</b> (вместо <s>3 990 ₽</s>)\n"
    "2️⃣ <b>Доступ в Закрытый канал</b> с ежедневными протоколами и разборами — <b>990 ₽</b>"
)


# ==============================================================================
# КЛАВИАТУРЫ ОПЛАТЫ
# ==============================================================================

def get_step_1_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Кнопка покупки полного гайда со скидкой."""
    guide_link = config.payment_link_for("guide", user_id) or "https://spectrmind.ru"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧠 Забрать «НЕЙРО ПРОТОКОЛЫ» — 1 990 ₽",
                    url=guide_link,
                )
            ]
        ]
    )


def get_step_2_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Кнопка дневного оффера 14:00 со скидкой 50%."""
    guide_link = config.payment_link_for("guide", user_id) or "https://spectrmind.ru"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧠 Забрать со скидкой 50% — 1 990 ₽",
                    url=guide_link,
                )
            ]
        ]
    )


def get_step_3_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Две опции выбора: полный гайд за 1 990 ₽ или клуб за 990 ₽."""
    guide_link = config.payment_link_for("guide", user_id) or "https://spectrmind.ru"
    channel_link = config.payment_link_for("channel", user_id) or "https://spectrmind.ru"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="1️⃣ Нейро Протоколы — 1 990 ₽",
                    url=guide_link,
                )
            ],
            [
                InlineKeyboardButton(
                    text="2️⃣ Закрытый клуб — 990 ₽/мес",
                    url=channel_link,
                )
            ],
        ]
    )


# ==============================================================================
# БАЗА ДАННЫХ ВОРОНКИ
# ==============================================================================

async def init_funnel_db(db_path: str = FUNNEL_DB_PATH) -> None:
    """Создать таблицу и индексы для отслеживания шагов воронки."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS funnel_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                step INTEGER NOT NULL,
                send_at INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at INTEGER NOT NULL,
                sent_at INTEGER,
                error_message TEXT
            )
            """
        )
        await db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_funnel_user_step ON funnel_steps (user_id, step)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_funnel_pending ON funnel_steps (status, send_at)"
        )
        await db.commit()
    logger.info("База данных воронки готова: %s", db_path)


def calculate_step_timestamps(base_time: Optional[datetime] = None) -> Tuple[int, int, int]:
    """Рассчитать точные UNIX timestamps для трех шагов.

    - Шаг 1: через 15 минут
    - Шаг 2: на следующий день ровно в 14:00 по МСК
    - Шаг 3: через 48 часов
    """
    if base_time is None:
        base_time = datetime.now(timezone.utc)
    elif base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=timezone.utc)

    # 1. Через 15 минут
    step1_dt = base_time + timedelta(minutes=15)

    # 2. На следующий календарный день ровно в 14:00 по МСК
    base_msk = base_time.astimezone(MSK_TZ)
    next_day = (base_msk + timedelta(days=1)).date()
    step2_msk = datetime.combine(next_day, time(14, 0, 0), tzinfo=MSK_TZ)
    step2_dt = step2_msk.astimezone(timezone.utc)

    # 3. Через 48 часов
    step3_dt = base_time + timedelta(hours=48)

    return (
        int(step1_dt.timestamp()),
        int(step2_dt.timestamp()),
        int(step3_dt.timestamp()),
    )


async def schedule_user_funnel(
    user_id: int,
    base_time: Optional[datetime] = None,
    db_path: str = FUNNEL_DB_PATH,
    force: bool = False,
) -> bool:
    """Запланировать три шага воронки для пользователя.

    Возвращает True, если шаги успешно запланированы, и False, если пользователь
    уже был зарегистрирован в воронке (при force=False).
    """
    await init_funnel_db(db_path)

    ts1, ts2, ts3 = calculate_step_timestamps(base_time)
    now_ts = int(datetime.now(timezone.utc).timestamp())

    async with aiosqlite.connect(db_path) as db:
        if not force:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM funnel_steps WHERE user_id = ?",
                (user_id,),
            )
            count = (await cursor.fetchone())[0]
            if count > 0:
                logger.info("Пользователь %s уже зарегистрирован в воронке, пропуск", user_id)
                return False

        steps_data = [
            (user_id, 1, ts1, "pending", now_ts),
            (user_id, 2, ts2, "pending", now_ts),
            (user_id, 3, ts3, "pending", now_ts),
        ]

        await db.executemany(
            """
            INSERT INTO funnel_steps (user_id, step, send_at, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, step) DO UPDATE SET
                send_at = excluded.send_at,
                status = 'pending',
                error_message = NULL
            """,
            steps_data,
        )
        await db.commit()

    logger.info("Запланирована автоворонка для user_id=%s (шаги 1, 2, 3)", user_id)
    return True


async def mark_step_sent(step_id: int, db_path: str = FUNNEL_DB_PATH) -> None:
    now_ts = int(datetime.now(timezone.utc).timestamp())
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE funnel_steps SET status = 'sent', sent_at = ? WHERE id = ?",
            (now_ts, step_id),
        )
        await db.commit()


async def mark_step_failed(step_id: int, error_msg: str, db_path: str = FUNNEL_DB_PATH) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE funnel_steps SET status = 'failed', error_message = ? WHERE id = ?",
            (str(error_msg)[:500], step_id),
        )
        await db.commit()


async def mark_user_blocked(user_id: int, db_path: str = FUNNEL_DB_PATH) -> None:
    """Если пользователь заблокировал бота, отменяем все оставшиеся шаги."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            UPDATE funnel_steps
            SET status = 'blocked', error_message = 'Bot blocked by user'
            WHERE user_id = ? AND status = 'pending'
            """,
            (user_id,),
        )
        await db.commit()
    logger.info("Пользователь %s заблокировал бота, шаги воронки отменены", user_id)


async def send_funnel_step(bot: Bot, user_id: int, step: int) -> bool:
    """Сформировать и отправить конкретный шаг воронки."""
    if step == 1:
        text = STEP_1_TEXT
        kb = get_step_1_keyboard(user_id)
    elif step == 2:
        text = STEP_2_TEXT
        kb = get_step_2_keyboard(user_id)
    elif step == 3:
        text = STEP_3_TEXT
        kb = get_step_3_keyboard(user_id)
    else:
        logger.error("Неизвестный шаг воронки: %s", step)
        return False

    await bot.send_message(
        chat_id=user_id,
        text=text,
        parse_mode="HTML",
        reply_markup=kb,
        disable_web_page_preview=True,
    )
    return True


async def process_due_funnel_steps(bot: Bot, db_path: str = FUNNEL_DB_PATH) -> int:
    """Найти и отправить все наступившие шаги воронки (send_at <= now).

    Возвращает количество успешно отправленных сообщений.
    """
    await init_funnel_db(db_path)
    now_ts = int(datetime.now(timezone.utc).timestamp())

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, user_id, step FROM funnel_steps
            WHERE status = 'pending' AND send_at <= ?
            ORDER BY send_at ASC
            LIMIT 50
            """,
            (now_ts,),
        )
        rows = await cursor.fetchall()

    if not rows:
        return 0

    sent_count = 0
    for row in rows:
        step_id = row["id"]
        user_id = row["user_id"]
        step = row["step"]

        try:
            await send_funnel_step(bot, user_id, step)
            await mark_step_sent(step_id, db_path)
            sent_count += 1
            logger.info("Отправлен шаг %d автоворонки пользователю %d (id записи %d)", step, user_id, step_id)
            # Микропауза между отправками во избежание флуд-лимитов Telegram
            await asyncio.sleep(0.05)

        except TelegramForbiddenError:
            logger.warning("Бот заблокирован пользователем %d (шаг %d)", user_id, step)
            await mark_user_blocked(user_id, db_path)

        except TelegramRetryAfter as exc:
            logger.warning("Флуд-контроль при отправке шага %d: ожидание %s сек", step, exc.retry_after)
            await asyncio.sleep(exc.retry_after)

        except TelegramAPIError as exc:
            logger.error("Telegram API ошибка при отправке шага %d пользователю %d: %s", step, user_id, exc)
            await mark_step_failed(step_id, str(exc), db_path)

        except Exception as exc:
            logger.exception("Непредвиденная ошибка при отправке шага %d пользователю %d", step, user_id)
            await mark_step_failed(step_id, str(exc), db_path)

    return sent_count


async def funnel_worker(bot: Bot, db_path: str = FUNNEL_DB_PATH, poll_interval: int = 30) -> None:
    """Фоновый воркер, проверяющий базу каждые poll_interval секунд."""
    logger.info("Воркер автоворонки запущен (интервал: %d сек, база: %s)", poll_interval, db_path)
    while True:
        try:
            await process_due_funnel_steps(bot, db_path)
            from trial_club import process_club_trials
            await process_club_trials(bot, db_path)
        except asyncio.CancelledError:
            logger.info("Воркер автоворонки остановлен по отмене задачи")
            break
        except Exception:
            logger.exception("Ошибка в цикле воркера автоворонки")

        try:
            await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            logger.info("Воркер автоворонки остановлен во время паузы")
            break


async def get_funnel_stats(db_path: str = FUNNEL_DB_PATH) -> Dict[str, Any]:
    """Сводная статистика по шагам и статусам воронки (для команды /funnel админа)."""
    await init_funnel_db(db_path)
    async with aiosqlite.connect(db_path) as db:
        # Всего уникальных пользователей
        cursor = await db.execute("SELECT COUNT(DISTINCT user_id) FROM funnel_steps")
        total_users = (await cursor.fetchone())[0]

        # Статистика по статусам
        cursor = await db.execute(
            "SELECT status, COUNT(*) FROM funnel_steps GROUP BY status"
        )
        status_counts = dict(await cursor.fetchall())

        # Статистика по шагам (сколько отправлено каждого шага)
        cursor = await db.execute(
            """
            SELECT step, status, COUNT(*)
            FROM funnel_steps
            GROUP BY step, status
            """
        )
        step_breakdown = {}
        for step, status, count in await cursor.fetchall():
            if step not in step_breakdown:
                step_breakdown[step] = {}
            step_breakdown[step][status] = count

    return {
        "total_users": total_users,
        "statuses": status_counts,
        "steps": step_breakdown,
    }
