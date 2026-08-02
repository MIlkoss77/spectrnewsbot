import logging

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

from config import ADMIN_ID, CHANNEL_ID
from content.generator import generate_content
from content.prompts import CONTENT_TYPES

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
        "/post \u2014 опубликовать в канал (только админ)\n"
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
        "<b>Типы контента:</b>\n"
        "\u2699\ufe0f Микро-протоколы \u2014 практические советы\n"
        "\u274c Разбор мифов \u2014 научные факты vs заблуждения\n"
        "\U0001f52c Исследования \u2014 разбор научных работ\n"
        "\u2600\ufe0f Утренние протоколы \u2014 старт дня для мозга\n"
        "\U0001f319 Вечерние советы \u2014 восстановление и сон\n\n"
        "<b>Генерация:</b>\n"
        "/generate \u2014 случайный тип\n"
        "/generate micro_protocol \u2014 конкретный тип\n"
        "/post micro_protocol \u2014 опубликовать конкретный тип\n\n"
        "<i>Используется бесплатный OpenRouter API.</i>",
        parse_mode="HTML",
    )


@router.message(Command("types"))
async def cmd_types(message: Message) -> None:
    lines = ["<b>\U0001f4cb Типы контента:</b>\n"]
    for ct in CONTENT_TYPES.values():
        lines.append(f"{ct.emoji} <code>{ct.key}</code> \u2014 {ct.label} (вес {ct.weight})")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("schedule"))
async def cmd_schedule(message: Message) -> None:
    from config import POST_TIMES
    times = ", ".join(POST_TIMES)
    await message.answer(
        f"\U0001f4c5 <b>Расписание постов:</b>\n\n"
        f"Время (МСК): {times}\n"
        f"Канал: {CHANNEL_ID or 'не задан'}\n\n"
        f"<i>Бот автоматически генерирует и публикует посты в указанное время.</i>",
        parse_mode="HTML",
    )


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
