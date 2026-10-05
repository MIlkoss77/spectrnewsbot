import logging
import os
from datetime import datetime, timezone, timedelta

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import (
    ADMIN_ID,
    BOT_LINK,
    CHANNEL_ID,
    CHANNEL_LINK,
    CTA_EVERY_N_POSTS,
    NEUROGUIDE_LINK,
    NEUROGUIDE_PRICE,
    PAID_CHANNEL_LINK,
    PAID_CHANNEL_PRICE,
    POST_TIMES,
    PREMIUM_POST_TIMES,
    SHOW_DIRECT_PAY_BUTTONS,
    get_cta_text,
)
from content.generator import PollPost, generate_for_premium_slot, generate_for_slot

logger = logging.getLogger(__name__)

MSK = timezone(timedelta(hours=3))

COUNTER_FILE = os.path.join(os.path.dirname(__file__), "post_counter.txt")
PREMIUM_COUNTER_FILE = os.path.join(os.path.dirname(__file__), "premium_counter.txt")


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


def build_keyboard(with_pay_buttons: bool) -> InlineKeyboardMarkup | None:
    """Кнопки под постом: всегда канал, на CTA-постах — оплата и бот.

    Основной путь покупки — бот @spectrnewsbot: у него в /start бесплатный
    гайд и кнопки оплаты. Прямые ссылки на Робокассу добавляются только если
    заданы в .env и включены через SHOW_DIRECT_PAY_BUTTONS.
    """
    rows = []

    if with_pay_buttons:
        guide_label = "\U0001f9e0 21-дневный протокол"
        if NEUROGUIDE_PRICE:
            guide_label += f" — {NEUROGUIDE_PRICE}"
        rows.append([InlineKeyboardButton(text=guide_label, url=BOT_LINK)])

        if SHOW_DIRECT_PAY_BUTTONS and PAID_CHANNEL_LINK:
            channel_label = "\U0001f512 Канал — оплатить"
            if PAID_CHANNEL_PRICE:
                channel_label += f" {PAID_CHANNEL_PRICE}"
            rows.append([InlineKeyboardButton(text=channel_label, url=PAID_CHANNEL_LINK)])

        if SHOW_DIRECT_PAY_BUTTONS and NEUROGUIDE_LINK:
            guide_pay_label = "\u2b07\ufe0f Гайд — оплатить"
            if NEUROGUIDE_PRICE:
                guide_pay_label += f" {NEUROGUIDE_PRICE}"
            rows.append([InlineKeyboardButton(text=guide_pay_label, url=NEUROGUIDE_LINK)])

    if CHANNEL_LINK:
        rows.append([
            InlineKeyboardButton(text="\U0001f4da Бесплатный канал", url=CHANNEL_LINK)
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


async def send_post(bot, content_type: str, post, with_cta: bool) -> None:
    """Publish a generated post to the channel.

    Polls go out through send_poll so Telegram renders real answer buttons;
    everything else is a plain text message. The CTA and the keyboard always
    belong to the same message, so they are built together here.
    """
    keyboard = build_keyboard(with_pay_buttons=with_cta)
    cta = get_cta_text(_read_counter()) if with_cta else ""

    if isinstance(post, PollPost):
        if post.context_text:
            # Вводный текст идёт отдельным сообщением, опрос — следом.
            context = f"{post.context_text}\n\n{cta}" if cta else post.context_text
            await bot.send_message(
                chat_id=CHANNEL_ID, text=context, parse_mode=None, reply_markup=keyboard
            )
            keyboard = None  # кнопки уже висят на контексте
        await bot.send_poll(
            chat_id=CHANNEL_ID,
            question=post.question,
            options=post.options,
            is_anonymous=True,
            allows_multiple_answers=False,
            reply_markup=keyboard,
        )
        logger.info("Poll posted: %r (%d options)", post.question[:60], len(post.options))
        return

    text = f"{post}\n\n{cta}" if cta else post
    await bot.send_message(
        chat_id=CHANNEL_ID, text=text, parse_mode=None, reply_markup=keyboard
    )


async def post_to_channel(bot) -> None:
    """Generate content and post it to the Telegram channel."""
    now = datetime.now(MSK)
    hour = now.hour
    logger.info("Scheduled post triggered at %s MSK", now.strftime("%H:%M"))

    try:
        content_type, post = await generate_for_slot(hour)

        counter = _read_counter() + 1
        _write_counter(counter)

        with_cta = counter % CTA_EVERY_N_POSTS == 0
        if with_cta:
            logger.info("CTA with purchase buttons attached (post #%d)", counter)

        await send_post(bot, content_type, post, with_cta=with_cta)
        logger.info("Posted [%s] to channel successfully (post #%d)", content_type, counter)
    except Exception:
        logger.exception("Failed to post to channel")


async def post_to_premium_channel(bot) -> None:
    """Generate premium content and send it to admin's DM."""
    now = datetime.now(MSK)
    hour = now.hour
    logger.info("Premium scheduled post triggered at %s MSK", now.strftime("%H:%M"))

    try:
        content_type, text = await generate_for_premium_slot(hour)

        counter = _read_premium_counter() + 1
        _write_premium_counter(counter)

        await bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode=None)
        logger.info("Sent [%s] to admin DM successfully (post #%d)", content_type, counter)
    except Exception:
        logger.exception("Failed to send premium post to admin DM")


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

    # Premium posts to admin DM (if ADMIN_ID configured)
    if ADMIN_ID:
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
            logger.info("Scheduled premium post (admin DM) at %s MSK", time_str)

    total_jobs = len(POST_TIMES) + (len(PREMIUM_POST_TIMES) if ADMIN_ID else 0)
    scheduler.start()
    logger.info("Scheduler started with %d jobs", total_jobs)
    return scheduler
