import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

import config
import database
import content_generator

logger = logging.getLogger(__name__)

# Глобальная ссылка на бота (инициализируется в bot.py)
_bot = None
_dp = None


def set_bot(bot):
    global _bot
    _bot = bot


async def publish_post(category: str):
    """Генерирует и публикует пост в канал."""
    topic = await database.get_random_topic(category)
    if not topic:
        logger.warning(f"Нет доступных тем для категории: {category}")
        return

    try:
        content = await content_generator.generate_post(
            category=category,
            title=topic["title"],
            description=topic["description"],
        )

        post_id = await database.save_post(topic["id"], category, content)

        msg = await _bot.send_message(
            chat_id=config.CHANNEL_ID,
            text=content,
            parse_mode="HTML",
        )

        await database.mark_published(post_id, channel_msg_id=msg.message_id)
        logger.info(f"Опубликован пост #{post_id} (тема: {topic['title']})")

    except Exception as e:
        logger.error(f"Ошибка публикации поста: {e}")
        if 'post_id' in locals():
            await database.mark_published(post_id, status="error", error=str(e))


async def morning_post():
    """Утренний микро-протокол."""
    logger.info("Запуск утренней публикации (микро-протокол)")
    await publish_post("micro_protocol")


async def evening_post():
    """Вечерний разбор исследования."""
    logger.info("Запуск вечерней публикации (исследование)")
    await publish_post("research")


async def myth_post():
    """Пост-миф (3 раза в неделю: вт, чт, сб)."""
    logger.info("Запуск публикации мифа")
    await publish_post("myth")


async def protocol_post():
    """Пост-протокол (2 раза в неделю: пт, вс)."""
    logger.info("Запуск публикации протокола")
    await publish_post("protocol")


async def catchup_post():
    """«Ловчий» пост в канале — напоминание забрать гайд."""
    logger.info("Запуск ловчего поста")
    text = (
        f"🧠 <b>Ещё не забрал бесплатный «Нейро-Стек»?</b>\n\n"
        f"5 научных протоколов для апгрейда мозга — бесплатно.\n\n"
        f"👉 @{config.BOT_USERNAME}"
    )
    try:
        await _bot.send_message(
            chat_id=config.CHANNEL_ID,
            text=text,
            parse_mode="HTML",
        )
        logger.info("Ловчий пост опубликован")
    except Exception as e:
        logger.error(f"Ошибка публикации ловчего поста: {e}")


def setup_scheduler() -> AsyncIOScheduler:
    tz = pytz.timezone(config.TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=tz)

    # Каждый день утром — микро-протокол
    scheduler.add_job(
        morning_post,
        CronTrigger(
            day_of_week="mon-sun",
            hour=config.MORNING_HOUR,
            minute=config.MORNING_MINUTE,
        ),
        id="morning_protocol",
        name="Утренний микро-протокол",
        replace_existing=True,
    )

    # Каждый день вечером — разбор исследования
    scheduler.add_job(
        evening_post,
        CronTrigger(
            day_of_week="mon-sun",
            hour=config.EVENING_HOUR,
            minute=config.EVENING_MINUTE,
        ),
        id="evening_research",
        name="Вечерний разбор исследования",
        replace_existing=True,
    )

    # Вт, Чт, Сб — разбор мифа (дополнительный пост)
    scheduler.add_job(
        myth_post,
        CronTrigger(
            day_of_week="tue,thu,sat",
            hour=13,
            minute=0,
        ),
        id="myth_post",
        name="Разбор мифа",
        replace_existing=True,
    )

    # Пт, Вс — протокол продуктивности
    scheduler.add_job(
        protocol_post,
        CronTrigger(
            day_of_week="fri,sun",
            hour=13,
            minute=0,
        ),
        id="protocol_post",
        name="Протокол продуктивности",
        replace_existing=True,
    )

    # Каждые 2 недели (каждый 2-й понедельник) — ловчий пост
    scheduler.add_job(
        catchup_post,
        CronTrigger(
            day_of_week="mon",
            week="*/2",
            hour=12,
            minute=0,
        ),
        id="catchup_post",
        name="Ловчий пост (каждые 2 недели)",
        replace_existing=True,
    )

    return scheduler
