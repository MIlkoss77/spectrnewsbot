import asyncio
import logging

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from config import BOT_TOKEN, CHANNEL_ID, POST_TIMES, PROXY_URL, PREMIUM_CHANNEL_ID, PREMIUM_POST_TIMES
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

    # Post one test message on startup so the user can verify it works
    try:
        from datetime import datetime, timezone, timedelta
        from content.generator import generate_for_slot
        now = datetime.now(timezone(timedelta(hours=3)))
        ctype, text = await generate_for_slot(now.hour)
        await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode=None)
        logger.info("Startup post sent [%s]", ctype)
    except Exception:
        logger.exception("Startup post failed")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
