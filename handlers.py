import logging

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

from config import ADMIN_ID, CHANNEL_ID
from content.generator import generate_content, generate_premium_content
from content.prompts import CONTENT_TYPES, PREMIUM_CONTENT_TYPES

logger = logging.getLogger(__name__)
router = Router()

# Русские псевдонимы, чтобы не набирать ключи вручную.
TYPE_ALIASES = {
    "бады": "supplement_recap",
    "бад": "supplement_recap",
    "добавки": "supplement_recap",
    "новости": "health_news",
    "новость": "health_news",
    "здоровье": "health_news",
    "загадка": "brain_curiosity",
    "загадки": "brain_curiosity",
    "миф": "myth_buster",
    "исследование": "research_digest",
    "протокол": "micro_protocol",
    "утро": "morning_routine",
    "вечер": "evening_reflection",
    "опрос": "poll",
}


def _resolve_type(requested: str, valid_types) -> str:
    """Map a user-supplied argument (or Russian alias) to a content type key."""
    key = requested.strip().lower()
    if key in valid_types:
        return key
    return TYPE_ALIASES.get(key, "")


def _is_admin(user_id: int) -> bool:
    return ADMIN_ID == 0 or user_id == ADMIN_ID


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "\U0001f9e0 <b>SpectrMind Bot</b>\n\n"
        "\u2699\ufe0f Бот для генерации и публикации постов о нейронауке.\n\n"
        "<b>Команды:</b>\n"
        "/generate \u2014 сгенерировать пост (превью)\n"
        "/post \u2014 опубликовать в бесплатный канал (админ)\n"
        "/generate_premium \u2014 сгенерировать премиум пост\n"
        "/post_premium \u2014 отправить премиум пост в личку (админ)\n"
        "/types \u2014 список типов контента\n"
        "/schedule \u2014 текущее расписание\n"
        "/diagnose \u2014 проверить модели и прокси (админ)\n"
        "/help \u2014 справка",
        parse_mode="HTML",
    )


def _rubric_lines(types_map) -> str:
    return "\n".join(f"{ct.emoji} {ct.label}" for ct in types_map.values())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "\U0001f4a1 <b>Как работает бот:</b>\n\n"
        "\u2699\ufe0f Публикует один пост в день в канал SpectrMind. "
        "Рубрика выбирается случайно, утром чаще выпадают протоколы.\n\n"
        f"<b>Бесплатный канал:</b>\n{_rubric_lines(CONTENT_TYPES)}\n\n"
        f"<b>Премиум (в личку):</b>\n{_rubric_lines(PREMIUM_CONTENT_TYPES)}\n\n"
        "<b>Генерация:</b>\n"
        "/generate \u2014 случайная рубрика\n"
        "/generate \u0431\u0430\u0434\u044b \u2014 конкретная рубрика (можно по-русски)\n"
        "/post \u0431\u0430\u0434\u044b \u2014 опубликовать в канал (админ)\n"
        "/generate_premium \u2014 премиум пост\n"
        "/post_premium \u2014 отправить в личку (админ)",
        parse_mode="HTML",
    )


@router.message(Command("diagnose"))
async def cmd_diagnose(message: Message) -> None:
    """Show which models and transport settings are actually working."""
    if not _is_admin(message.from_user.id):
        await message.answer("\u26a0\ufe0f Эта команда только для админа.")
        return

    from config import OPENROUTER_MODEL, FALLBACK_MODELS, PROXY_URL
    from content.generator import check_api_health

    await message.answer("\U0001f50d Проверяю модели, это займёт до минуты...")

    icons = {"ok": "\u2705", "fail": "\u26a0\ufe0f", "error": "\u274c"}
    lines = [f"<b>\U0001f50d Диагностика</b>\n"]
    lines.append(f"Прокси: <code>{PROXY_URL or 'не настроен'}</code>")
    lines.append(f"Основная модель: <code>{OPENROUTER_MODEL}</code>\n")

    results = await check_api_health()
    for status, model, detail in results:
        lines.append(f"{icons.get(status, '\u2022')} <code>{model}</code>\n    {detail}")

    working = [r for r in results if r[0] == "ok"]
    if working:
        lines.append(
            f"\n\u2705 Отвечают: {len(working)} из {len(results)}. "
            f"Публикация пойдёт через <code>{working[0][1]}</code>."
        )
    else:
        lines.append(
            "\n\u274c Ни одна модель не ответила. Проверь, запущен ли прокси "
            "на указанном порту, и верен ли <code>OPENROUTER_MODEL</code>."
        )

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("types"))
async def cmd_types(message: Message) -> None:
    lines = ["<b>\U0001f4cb Типы контента:</b>\n"]
    lines.append("<b>Бесплатный канал:</b>")
    for ct in CONTENT_TYPES.values():
        lines.append(f"{ct.emoji} <code>{ct.key}</code> \u2014 {ct.label} (вес {ct.weight})")
    lines.append("\n<b>Премиум (в личку):</b>")
    for ct in PREMIUM_CONTENT_TYPES.values():
        lines.append(f"{ct.emoji} <code>{ct.key}</code> \u2014 {ct.label} (вес {ct.weight})")
    lines.append(
        "\n<b>Русские псевдонимы:</b>\n"
        + ", ".join(f"<code>{alias}</code>" for alias in sorted(TYPE_ALIASES))
        + "\n\nПример: <code>/generate бады</code>"
    )
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("schedule"))
async def cmd_schedule(message: Message) -> None:
    from config import POST_TIMES, PREMIUM_POST_TIMES
    times = ", ".join(POST_TIMES)
    text = (
        f"\U0001f4c5 <b>Расписание постов:</b>\n\n"
        f"<b>Бесплатный канал:</b>\n"
        f"Время (МСК): {times}\n"
        f"Канал: {CHANNEL_ID or 'не задан'}\n"
    )
    premium_times = ", ".join(PREMIUM_POST_TIMES)
    text += (
        f"\n<b>Премиум (в личку админа):</b>\n"
        f"Время (МСК): {premium_times}\n"
    )
    text += "\n<i>Рубрика для каждого поста выбирается автоматически из ротации.</i>"
    await message.answer(text, parse_mode="HTML")


async def _parse_requested_type(message: Message, valid_types) -> tuple:
    """Parse the optional type argument. Returns (content_type, error_sent)."""
    args = message.text.split(maxsplit=1)
    if len(args) <= 1:
        return None, False

    requested = args[1].strip()
    resolved = _resolve_type(requested, valid_types)
    if resolved:
        return resolved, False

    valid = ", ".join(valid_types.keys())
    await message.answer(
        f"\u274c Неизвестный тип: <code>{requested}</code>\n\n"
        f"Доступные: {valid}\n"
        f"Можно по-русски: {', '.join(sorted(TYPE_ALIASES))}",
        parse_mode="HTML",
    )
    return None, True


@router.message(Command("generate"))
async def cmd_generate(message: Message) -> None:
    content_type, error = await _parse_requested_type(message, CONTENT_TYPES)
    if error:
        return

    await message.answer("\u23f3 Генерирую пост...")

    try:
        ctype, text = await generate_content(content_type)
        label = CONTENT_TYPES[ctype].label
        await message.answer(
            f"<b>\U0001f4dd Превью ({label}):</b>\n\n{text}",
            parse_mode=None,
        )
    except Exception:
        logger.exception("Generation failed")
        await message.answer("\u274c Не удалось сгенерировать пост. Попробуй позже.")


@router.message(Command("post"))
async def cmd_post(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("\u26a0\ufe0f Эта команда только для админа.")
        return

    content_type, error = await _parse_requested_type(message, CONTENT_TYPES)
    if error:
        return

    await message.answer("\u23f3 Генерирую и публикую...")

    try:
        ctype, text = await generate_content(content_type)
        await message.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode=None)
        label = CONTENT_TYPES[ctype].label
        await message.answer(f"\u2705 Опубликовано ({label}) в {CHANNEL_ID}")
    except Exception:
        logger.exception("Post failed")
        await message.answer("\u274c Не удалось опубликовать. Проверь логи.")


@router.message(Command("generate_premium"))
async def cmd_generate_premium(message: Message) -> None:
    content_type, error = await _parse_requested_type(message, PREMIUM_CONTENT_TYPES)
    if error:
        return

    await message.answer("\u23f3 Генерирую премиум пост...")

    try:
        ctype, text = await generate_premium_content(content_type)
        label = PREMIUM_CONTENT_TYPES[ctype].label
        await message.answer(
            f"<b>\U0001f4dd Премиум превью ({label}):</b>\n\n{text}",
            parse_mode=None,
        )
    except Exception:
        logger.exception("Premium generation failed")
        await message.answer("\u274c Не удалось сгенерировать премиум пост. Попробуй позже.")


@router.message(Command("post_premium"))
async def cmd_post_premium(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("\u26a0\ufe0f Эта команда только для админа.")
        return

    content_type, error = await _parse_requested_type(message, PREMIUM_CONTENT_TYPES)
    if error:
        return

    await message.answer("\u23f3 Генерирую и отправляю в личку...")

    try:
        ctype, text = await generate_premium_content(content_type)
        await message.bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode=None)
        label = PREMIUM_CONTENT_TYPES[ctype].label
        await message.answer(f"\u2705 Отправлено ({label}) в личку")
    except Exception:
        logger.exception("Premium post failed")
        await message.answer("\u274c Не удалось отправить. Проверь логи.")
