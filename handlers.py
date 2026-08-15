import logging

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

from config import ADMIN_ID, CHANNEL_ID, PREMIUM_CHANNEL_ID
from content.generator import generate_content, generate_premium_content
from content.prompts import CONTENT_TYPES, PREMIUM_CONTENT_TYPES

logger = logging.getLogger(__name__)
router = Router()


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
        "/post_premium \u2014 опубликовать в премиум канал (админ)\n"
        "/types \u2014 список типов контента\n"
        "/schedule \u2014 текущее расписание\n"
        "/help \u2014 справка",
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "\U0001f4a1 <b>Как работает бот:</b>\n\n"
        "Автоматически генерирует и публикует посты о нейронауке "
        "в канал SpectrMind 2-3 раза в день.\n\n"
        "<b>Бесплатный канал:</b>\n"
        "\u2699\ufe0f Микро-протоколы \u2014 практические советы\n"
        "\u274c Разбор мифов \u2014 научные факты vs заблуждения\n"
        "\U0001f52c Исследования \u2014 разбор научных работ\n"
        "\u2600\ufe0f Утренние протоколы \u2014 старт дня для мозга\n"
        "\U0001f319 Вечерние советы \u2014 восстановление и сон\n\n"
        "<b>Премиум канал:</b>\n"
        "\U0001f9ec Глубокие разборы \u2014 детальный анализ исследований\n"
        "\U0001f48e Протоколы+ \u2014 расширенные протоколы с обоснованием\n"
        "\U0001f4f0 Дайджесты \u2014 обзор открытий недели\n\n"
        "<b>Генерация:</b>\n"
        "/generate \u2014 случайный тип\n"
        "/generate micro_protocol \u2014 конкретный тип\n"
        "/post micro_protocol \u2014 опубликовать в бесплатный канал\n"
        "/generate_premium \u2014 премиум пост\n"
        "/post_premium \u2014 опубликовать в премиум канал\n\n"
        "<i>Используется платный OpenRouter API (GPT-4o-mini).</i>",
        parse_mode="HTML",
    )


@router.message(Command("types"))
async def cmd_types(message: Message) -> None:
    lines = ["<b>\U0001f4cb Типы контента:</b>\n"]
    lines.append("<b>Бесплатный канал:</b>")
    for ct in CONTENT_TYPES.values():
        lines.append(f"{ct.emoji} <code>{ct.key}</code> \u2014 {ct.label} (вес {ct.weight})")
    if PREMIUM_CHANNEL_ID:
        lines.append("\n<b>Премиум канал:</b>")
        for ct in PREMIUM_CONTENT_TYPES.values():
            lines.append(f"{ct.emoji} <code>{ct.key}</code> \u2014 {ct.label} (вес {ct.weight})")
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
    if PREMIUM_CHANNEL_ID:
        premium_times = ", ".join(PREMIUM_POST_TIMES)
        text += (
            f"\n<b>Премиум канал:</b>\n"
            f"Время (МСК): {premium_times}\n"
            f"Канал: {PREMIUM_CHANNEL_ID}\n"
        )
    text += "\n<i>Бот автоматически генерирует и публикует посты в указанное время.</i>"
    await message.answer(text, parse_mode="HTML")


@router.message(Command("generate"))
async def cmd_generate(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    content_type = None

    if len(args) > 1:
        requested = args[1].strip()
        if requested in CONTENT_TYPES:
            content_type = requested
        else:
            valid = ", ".join(CONTENT_TYPES.keys())
            await message.answer(
                f"\u274c Неизвестный тип: <code>{requested}</code>\n\n"
                f"Доступные: {valid}",
                parse_mode="HTML",
            )
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

    args = message.text.split(maxsplit=1)
    content_type = None

    if len(args) > 1:
        requested = args[1].strip()
        if requested in CONTENT_TYPES:
            content_type = requested
        else:
            valid = ", ".join(CONTENT_TYPES.keys())
            await message.answer(
                f"\u274c Неизвестный тип: <code>{requested}</code>\n\n"
                f"Доступные: {valid}",
                parse_mode="HTML",
            )
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
    args = message.text.split(maxsplit=1)
    content_type = None

    if len(args) > 1:
        requested = args[1].strip()
        if requested in PREMIUM_CONTENT_TYPES:
            content_type = requested
        else:
            valid = ", ".join(PREMIUM_CONTENT_TYPES.keys())
            await message.answer(
                f"\u274c Неизвестный тип: <code>{requested}</code>\n\n"
                f"Доступные: {valid}",
                parse_mode="HTML",
            )
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

    if not PREMIUM_CHANNEL_ID:
        await message.answer("\u274c Премиум канал не настроен. Добавь PREMIUM_CHANNEL_ID в .env")
        return

    args = message.text.split(maxsplit=1)
    content_type = None

    if len(args) > 1:
        requested = args[1].strip()
        if requested in PREMIUM_CONTENT_TYPES:
            content_type = requested
        else:
            valid = ", ".join(PREMIUM_CONTENT_TYPES.keys())
            await message.answer(
                f"\u274c Неизвестный тип: <code>{requested}</code>\n\n"
                f"Доступные: {valid}",
                parse_mode="HTML",
            )
            return

    await message.answer("\u23f3 Генерирую и публикую в премиум канал...")

    try:
        ctype, text = await generate_premium_content(content_type)
        await message.bot.send_message(chat_id=PREMIUM_CHANNEL_ID, text=text, parse_mode=None)
        label = PREMIUM_CONTENT_TYPES[ctype].label
        await message.answer(f"\u2705 Опубликовано ({label}) в премиум канал {PREMIUM_CHANNEL_ID}")
    except Exception:
        logger.exception("Premium post failed")
        await message.answer("\u274c Не удалось опубликовать. Проверь логи.")
