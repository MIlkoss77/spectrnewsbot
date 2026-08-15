import logging
import os
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import POST_TIMES, CHANNEL_ID, PREMIUM_CHANNEL_ID, PREMIUM_POST_TIMES
from content.generator import generate_for_slot, generate_for_premium_slot, add_cta

logger = logging.getLogger(__name__)

MSK = timezone(timedelta(hours=3))

COUNTER_FILE = os.path.join(os.path.dirname(__file__), "post_counter.txt")
PREMIUM_COUNTER_FILE = os.path.join(os.path.dirname(__file__), "premium_counter.txt")

CTA_EVERY_N = 5


def _read_counter() -> int:
    """Read post counter from file."""
    try:
        with open(COUNTER_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def _write_counter(value: int) -> None:
    """Write post counter to file."""
    with open(COUNTER_FILE, "w") as f:
        f.write(str(value))


def _read_premium_counter() -> int:
    """Read premium post counter from file."""
    try:
        with open(PREMIUM_COUNTER_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def _write_premium_counter(value: int) -> None:
    """Write premium post counter to file."""
    with open(PREMIUM_COUNTER_FILE, "w") as f:
        f.write(str(value))


async def post_to_channel(bot) -> None:
    """Generate content and post it to the Telegram channel."""
    now = datetime.now(MSK)
    hour = now.hour
    logger.info("Scheduled post triggered at %s MSK", now.strftime("%H:%M"))

    try:
        content_type, text = await generate_for_slot(hour)

        # Add CTA every N posts
        counter = _read_counter() + 1
        _write_counter(counter)

        if counter % CTA_EVERY_N == 0:
            text = add_cta(text)
            logger.info("CTA added (post #%d)", counter)

        await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode=None)
        logger.info("Posted [%s] to channel successfully (post #%d)", content_type, counter)
    except Exception:
        logger.exception("Failed to post to channel")


async def post_to_premium_channel(bot) -> None:
    """Generate premium content and post it to the premium Telegram channel."""
    now = datetime.now(MSK)
    hour = now.hour
    logger.info("Premium scheduled post triggered at %s MSK", now.strftime("%H:%M"))

    try:
        content_type, text = await generate_for_premium_slot(hour)

        counter = _read_premium_counter() + 1
        _write_premium_counter(counter)

        await bot.send_message(chat_id=PREMIUM_CHANNEL_ID, text=text, parse_mode=None)
        logger.info("Posted [%s] to premium channel successfully (post #%d)", content_type, counter)
    except Exception:
        logger.exception("Failed to post to premium channel")


def setup_scheduler(bot) -> AsyncIOScheduler:
    """Configure and return the APScheduler instance with channel posting jobs."""
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    # Free channel jobs
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
        logger.info("Scheduled free channel post at %s MSK", time_str)

    # Premium channel jobs (only if configured)
    if PREMIUM_CHANNEL_ID:
        for time_str in PREMIUM_POST_TIMES:
            parts = time_str.split(":")
            hour, minute = int(parts[0]), int(parts[1])

            scheduler.add_job(
                post_to_premium_channel,
                trigger=CronTrigger(hour=hour, minute=minute, timezone="Europe/Moscow"),
                args=[bot],
                id=f"premium_post_{hour:02d}{minute:02d}",
                name=f"Premium post at {time_str} MSK",
                replace_existing=True,
            )
            logger.info("Scheduled premium channel post at %s MSK", time_str)

    total_jobs = len(POST_TIMES) + (len(PREMIUM_POST_TIMES) if PREMIUM_CHANNEL_ID else 0)
    scheduler.start()
    logger.info("Scheduler started with %d jobs", total_jobs)
    return scheduler
