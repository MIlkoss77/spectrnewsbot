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

# Публиковать тестовый пост в канал при каждом старте бота.
# По умолчанию выключено: перезапуск сервиса не должен дёргать подписчиков.
# Включить для проверки: STARTUP_POST=true
STARTUP_POST = os.getenv("STARTUP_POST", "false").strip().lower() in ("true", "1", "yes")

# ---------------------------------------------------------------- CTA / продажи
# Имя бота-воронки (без @): выдаёт бесплатный гайд и принимает оплату.
BOT_USERNAME = os.getenv("BOT_USERNAME", "spectrnewsbot").lstrip("@")
BOT_LINK = f"https://t.me/{BOT_USERNAME}"

# Ссылка на бесплатный канал — для кнопки под постами.
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/ruspectrmind")

# ---- Лид-магнит: бесплатный PDF выдаётся по /start -------------------------
PDF_PATH = os.getenv("PDF_PATH", "freeguide.pdf")
DB_PATH = os.getenv("DB_PATH", "spectrmind.db")

LEAD_MAGNET_CAPTION = (
    "\U0001f9e0 Твой бесплатный гайд <b>«Нейро-Стек»</b> — 5 протоколов для апгрейда мозга.\n\n"
    "\U0001f447 Забирай, сохраняй и применяй!\n\n"
    "Хочешь больше? Закрытый канал + полный нейрогайд — кнопки ниже."
)


def build_lead_magnet_keyboard(user_id=None):
    """Кнопки под бесплатным гайдом: канал, закрытый канал, полный нейрогайд."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows = []
    if CHANNEL_LINK:
        rows.append([InlineKeyboardButton(text="\U0001f4da Бесплатный канал", url=CHANNEL_LINK)])

    channel_link = payment_link_for("channel", user_id)
    if channel_link:
        label = "\U0001f512 Закрытый канал"
        if PAID_CHANNEL_PRICE:
            label += f" {PAID_CHANNEL_PRICE}"
        rows.append([InlineKeyboardButton(text=label, url=channel_link)])

    guide_link = payment_link_for("guide", user_id)
    if guide_link:
        label = "\U0001f9e0 Полный нейрогайд"
        if NEUROGUIDE_PRICE:
            label += f" {NEUROGUIDE_PRICE}"
        rows.append([InlineKeyboardButton(text=label, url=guide_link)])

    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None

# ---- Robokassa: ссылки на оплату формируются на лету -----------------------
# Ссылки вида /Merchant/Index/{guid} — это разовые счёта из личного кабинета,
# они истекают, и кнопка в канале со временем отдаёт 500. Поэтому адрес
# собирается с подписью при каждом показе: такой не истекает никогда.
ROBOKASSA_MERCHANT_LOGIN = os.getenv("ROBOKASSA_MERCHANT_LOGIN", os.getenv("ROBOKASSA_LOGIN", ""))
ROBOKASSA_PASSWORD_1 = os.getenv("ROBOKASSA_PASSWORD_1", os.getenv("ROBOKASSA_PASSWORD1", ""))
ROBOKASSA_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"

# Куда возвращать покупателя после оплаты. По умолчанию — этот же бот, чтобы
# человек не оставался на странице Robokassa без объяснений.
ROBOKASSA_SUCCESS_URL = os.getenv("ROBOKASSA_SUCCESS_URL", "")
ROBOKASSA_FAIL_URL = os.getenv("ROBOKASSA_FAIL_URL", "")

# Ссылки из личного кабинета: запасной вариант, если подпись не настроена.
PAID_CHANNEL_LINK = os.getenv("PAID_CHANNEL_LINK", "")
PAID_CHANNEL_PRICE = os.getenv("PAID_CHANNEL_PRICE", "990\u20bd")
NEUROGUIDE_LINK = os.getenv("NEUROGUIDE_LINK", "")
NEUROGUIDE_PRICE = os.getenv("NEUROGUIDE_PRICE", "1990\u20bd")

# Суммы для генерации ссылок (числом, как ждёт Robokassa)
PAID_CHANNEL_SUM = os.getenv("PAID_CHANNEL_SUM", "990.00")
NEUROGUIDE_SUM = os.getenv("NEUROGUIDE_SUM", "1990.00")

SHOW_DIRECT_PAY_BUTTONS = os.getenv("SHOW_DIRECT_PAY_BUTTONS", "false").strip().lower() in ("true", "1", "yes")
SHOW_CHANNEL_BUTTON = os.getenv("SHOW_CHANNEL_BUTTON", "false").strip().lower() in ("true", "1", "yes")


def robokassa_ready() -> bool:
    """Можно ли формировать ссылки на оплату."""
    return bool(ROBOKASSA_MERCHANT_LOGIN and ROBOKASSA_PASSWORD_1)


def build_robokassa_link(
    out_sum: str,
    description: str,
    invoice_id=None,
    user_id=None,
    recurring: bool = False,
) -> str:
    """Собрать подписанную ссылку на оплату.

    Подпись: MD5 от MerchantLogin:OutSum:InvId[:модификаторы]:Пароль#1[:Shp_*],
    где Shp_-параметры идут после пароля, строго по алфавиту.

    ``user_id`` передаётся как Shp_user и возвращается в уведомлении об оплате —
    по нему можно понять, какому человеку выдать доступ. Если ссылку собрать
    нельзя, возвращается исходная ссылка из .env (или пустая строка).
    """
    import hashlib

    if not robokassa_ready():
        return ""

    inv_id = str(invoice_id if invoice_id is not None else _next_invoice_id())
    out_sum = f"{float(str(out_sum).replace(',', '.')):.2f}"

    signature_base = f"{ROBOKASSA_MERCHANT_LOGIN}:{out_sum}:{inv_id}"
    if recurring:
        signature_base += ":Recurring=true"
    signature_base += f":{ROBOKASSA_PASSWORD_1}"
    if user_id is not None:
        signature_base += f":Shp_user={user_id}"

    signature = hashlib.md5(signature_base.encode("utf-8")).hexdigest()

    params = [
        ("MerchantLogin", ROBOKASSA_MERCHANT_LOGIN),
        ("OutSum", out_sum),
        ("InvId", inv_id),
        ("SignatureValue", signature),
        ("Description", description),
        ("Culture", "ru"),
        ("Encoding", "utf-8"),
    ]
    if recurring:
        params.append(("Recurring", "true"))
    if user_id is not None:
        params.append(("Shp_user", str(user_id)))
    if ROBOKASSA_SUCCESS_URL:
        params.append(("SuccessUrl2", ROBOKASSA_SUCCESS_URL))
        params.append(("SuccessUrl2Method", "GET"))
    if ROBOKASSA_FAIL_URL:
        params.append(("FailUrl2", ROBOKASSA_FAIL_URL))
        params.append(("FailUrl2Method", "GET"))

    from urllib.parse import urlencode
    return f"{ROBOKASSA_URL}?{urlencode(params)}"


_INVOICE_LOCK = None
_INVOICE_LAST = [0]


def _next_invoice_id() -> int:
    """Уникальный InvId.

    Повторный номер Robokassa отвергает с ошибкой 40, а два человека могут
    нажать кнопку в одну секунду. Микросекундное время даёт монотонно
    возрастающий номер без повторов; на случай перевода часов значение
    принудительно увеличивается.
    """
    global _INVOICE_LOCK
    import threading
    import time

    # Ленивая инициализация замка: config импортируется очень рано.
    if _INVOICE_LOCK is None:
        _INVOICE_LOCK = threading.Lock()

    with _INVOICE_LOCK:
        candidate = int(time.time() * 1_000_000)
        if candidate <= _INVOICE_LAST[0]:
            candidate = _INVOICE_LAST[0] + 1
        _INVOICE_LAST[0] = candidate

    # Ограничение Robokassa: до 2^63-1
    return candidate % 9_000_000_000_000_000_000


def payment_link_for(product: str, user_id=None) -> str:
    """Живая ссылка на оплату: 'channel' (подписка) или 'guide'.

    Если подпись не настроена (нет логина или пароля в .env), возвращается
    ссылка из личного кабинета — она может быть просрочена, но лучше, чем
    кнопка, ведущая в никуда.
    """
    if product == "channel":
        link = build_robokassa_link(
            PAID_CHANNEL_SUM, "SPECTR CLUB — подписка на месяц",
            user_id=user_id, recurring=True,
        )
        return link or PAID_CHANNEL_LINK
    link = build_robokassa_link(
        NEUROGUIDE_SUM, "SpectrMind: полный нейрогайд",
        user_id=user_id,
    )
    return link or NEUROGUIDE_LINK


# CTA показывается каждый N-й пост. При одном посте в день: 3 = раз в 3 дня.
CTA_EVERY_N_POSTS = int(os.getenv("CTA_EVERY_N_POSTS", "3"))

# Тексты CTA: сначала боль читателя, потом предложение и ссылка на бота.
CTA_VARIANTS = [
    (
        "\U0001f9e0 Устал от постоянной тревоги?\n\n"
        "21-дневный протокол для мозга: сон, стресс, фокус — по шагам, "
        "с объяснением, почему каждый шаг работает.\n\n"
        "\u27a1\ufe0f Забрать протокол: @{username}"
    ),
    (
        "\U0001f634 Не получается наладить сон?\n\n"
        "21-дневный протокол для мозга: от света утром до температуры "
        "спальни вечером — что делать и в каком порядке.\n\n"
        "\u27a1\ufe0f Забрать протокол: @{username}"
    ),
    (
        "\U0001f525 Постоянно в стрессе и на пределе?\n\n"
        "21-дневный протокол для мозга: восстановление нервной системы "
        "без эзотерики — только то, что подтверждено исследованиями.\n\n"
        "\u27a1\ufe0f Забрать протокол: @{username}"
    ),
    (
        "\U0001f9e9 Чувствуешь, что голова работает не на полную?\n\n"
        "21-дневный протокол для мозга: концентрация, память и энергия — "
        "пошаговая программа на три недели.\n\n"
        "\u27a1\ufe0f Забрать протокол: @{username}"
    ),
]


def get_cta_text(index: int = 0) -> str:
    """Return a CTA text, cycling through the variants."""
    variant = CTA_VARIANTS[index % len(CTA_VARIANTS)]
    return variant.format(username=BOT_USERNAME)


# Раньше воронка и автопостинг были двумя разными процессами на одном токене,
# и они перехватывали друг у друга команду /start. Теперь это один бот:
# он и гайд выдаёт, и посты публикует. Поэтому совпадение токена с ботом-воронкой
# — норма, и проверка только пишет предупреждение в лог, если вы запустили
# ВТОРОЙ процесс на том же токене.
FUNNEL_BOT_ID = "8808411768"


def describe_token(token: str) -> str:
    """Короткое описание токена для лога: какой бот и не запущен ли второй процесс."""
    bot_id = token.split(":", 1)[0].strip() if ":" in token else ""
    if bot_id == FUNNEL_BOT_ID:
        return (
            f"токен бота @{BOT_USERNAME} (id {bot_id}) — основного бота с воронкой. "
            f"Это ожидаемо. Убедитесь, что на этом токене запущен ТОЛЬКО один процесс "
            f"этого бота, иначе они будут перехватывать друг у друга /start."
        )
    return f"токен бота id {bot_id or '?'}"

# Fallback models, used when the primary one fails or returns nothing.
# These were verified as dead on the production server and were removed:
#   deepseek/deepseek-v4-flash     -> ответ 200 без текста, валил генерацию
#   google/gemini-2.0-flash-001    -> 404 No endpoints found
# Run `python3 tools_check_models.py --free` to list free models that exist
# right now, then put one or two working ids here.
FALLBACK_MODELS: list = []

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
