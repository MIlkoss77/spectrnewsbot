import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from config import (
    BOT_TOKEN, CHANNEL_ID, POST_TIMES, PROXY_URL, PREMIUM_CHANNEL_ID,
    PREMIUM_POST_TIMES, STARTUP_POST,
)
from handlers import router
from scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set in .env")
    if not CHANNEL_ID:
        raise RuntimeError("CHANNEL_ID is not set in .env")

    session = None
    if PROXY_URL:
        session = AiohttpSession(proxy=PROXY_URL)
        logger.info("Using proxy: %s", PROXY_URL)

    bot = Bot(token=BOT_TOKEN, session=session)
    dp = Dispatcher()
    dp.include_router(router)

    setup_scheduler(bot)
    logger.info("Bot started. Channel: %s, schedule: %s", CHANNEL_ID, POST_TIMES)
    if PREMIUM_CHANNEL_ID:
        logger.info("Premium channel: %s, schedule: %s", PREMIUM_CHANNEL_ID, PREMIUM_POST_TIMES)

    # Optional test post on startup, so a restart can be verified in the channel.
    # Disable with STARTUP_POST=false — otherwise every restart adds a post.
    if STARTUP_POST:
        try:
            from datetime import datetime, timezone, timedelta
            from content.generator import generate_for_slot
            from scheduler import send_post
            now = datetime.now(timezone(timedelta(hours=3)))
            ctype, post = await generate_for_slot(now.hour)
            # No CTA on the startup post: it is a smoke test, not a scheduled slot.
            await send_post(bot, ctype, post, with_cta=False)
            logger.info("Startup post sent [%s]", ctype)
        except Exception:
            logger.exception("Startup post failed")
    else:
        logger.info("Startup post disabled (STARTUP_POST=false)")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
