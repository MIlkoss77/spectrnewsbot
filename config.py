import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "SpectrMindBot")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@spectrmind_channel")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/spectrmind_channel")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("MODEL", "google/gemma-4-31b-it")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")

MORNING_HOUR = int(os.getenv("MORNING_POST_HOUR", "8"))
MORNING_MINUTE = int(os.getenv("MORNING_POST_MINUTE", "0"))
EVENING_HOUR = int(os.getenv("EVENING_POST_HOUR", "19"))
EVENING_MINUTE = int(os.getenv("EVENING_POST_MINUTE", "0"))

PDF_PATH = os.getenv("PDF_PATH", "neuro_stack.pdf")
_admin_raw = os.getenv("ADMIN_IDS") or os.getenv("ADMIN_ID") or ""
ADMIN_IDS = [int(x) for x in _admin_raw.split(",") if x.strip()]

PAID_CHANNEL_LINK = os.getenv("PAID_CHANNEL_LINK", "https://t.me/+xxxxx")
PAID_CHANNEL_PRICE = os.getenv("PAID_CHANNEL_PRICE", "990₽")
NEUROGUIDE_LINK = os.getenv("NEUROGUIDE_LINK", "https://spectrmind.ru/neuroguide")
NEUROGUIDE_PRICE = os.getenv("NEUROGUIDE_PRICE", "1990₽")

PREMIUM_CHANNEL_ID = os.getenv("PREMIUM_CHANNEL_ID", "")
PREMIUM_POST_TIMES = [t.strip() for t in os.getenv("PREMIUM_POST_TIMES", "10:00,15:00,21:00").split(",")]

DB_PATH = "spectrmind.db"


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
