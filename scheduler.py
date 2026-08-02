import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import POST_TIMES, CHANNEL_ID
from content.generator import generate_content

logger = logging.getLogger(__name__)

MSK = timezone(timedelta(hours=3))


async def post_to_channel(bot) -> None:
    """Generate content and post it to the Telegram channel."""
    now = datetime.now(MSK).strftime("%H:%M")
    logger.info("Scheduled post triggered at %s MSK", now)

    try:
        content_type, text = await generate_content()
        await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode=None)
        logger.info("Posted [%s] to channel successfully", content_type)
    except Exception:
        logger.exception("Failed to post to channel")


def setup_scheduler(bot) -> AsyncIOScheduler:
    """Configure and return the APScheduler instance with channel posting jobs."""
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    for time_str in POST_TIMES:
        parts = time_str.split(":")
        hour, minute = int(parts[0]), int(parts[1])

        scheduler.add_job(
            post_to_channel,
            trigger=CronTrigger(hour=hour, minute=minute, timezone="Europe/Moscow"),
            args=[bot],
            id=f"post_{hour:02d}{minute:02d}",
            name=f"Post at {time_str} MSK",
            replace_existing=True,
        )
        logger.info("Scheduled post at %s MSK", time_str)

    scheduler.start()
    logger.info("Scheduler started with %d jobs", len(POST_TIMES))
    return scheduler
