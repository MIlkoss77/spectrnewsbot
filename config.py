import os
import sys
from dotenv import load_dotenv

if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
# Primary model. Override in .env; verify with: python3 tools_check_models.py
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

POST_TIMES_RAW = os.getenv("POST_TIMES", "09:00")
POST_TIMES = [t.strip() for t in POST_TIMES_RAW.split(",")]

# Premium channel (optional)
PREMIUM_CHANNEL_ID = os.getenv("PREMIUM_CHANNEL_ID", "")
PREMIUM_POST_TIMES_RAW = os.getenv("PREMIUM_POST_TIMES", "10:00,18:00")
PREMIUM_POST_TIMES = [t.strip() for t in PREMIUM_POST_TIMES_RAW.split(",")]

# Proxy for Telegram API (aiohttp doesn't use system proxy settings)
# Example: http://127.0.0.1:10809 or socks5://127.0.0.1:10808
PROXY_URL = os.getenv("PROXY_URL", "")

# Send one test post to the channel on every bot start (set false for production)
STARTUP_POST = os.getenv("STARTUP_POST", "true").strip().lower() not in ("false", "0", "no")

# Fallback models, used when the primary one fails or returns nothing.
# These were verified as dead on the production server and were removed:
#   deepseek/deepseek-v4-flash     -> ответ 200 без текста, валил генерацию
#   google/gemini-2.0-flash-001    -> 404 No endpoints found
# Run `python3 tools_check_models.py --free` to list free models that exist
# right now, then put one or two working ids here.
FALLBACK_MODELS: list = []

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
