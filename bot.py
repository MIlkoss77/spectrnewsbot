import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery,
    FSInputFile,
)
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramForbiddenError

import config
import database
import content_generator
import scheduler as sched

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

# ---------- Лид-магнит: PDF «Нейро-Стек» ----------

LEAD_MAGNET_CAPTION = (
    "🧠 Твой бесплатный гайд <b>«Нейро-Стек»</b> — 5 протоколов для апгрейда мозга.\n\n"
    "👇 Забирай, сохраняй и применяй!\n\n"
    "Хочешь больше? Закрытый канал + полный нейрогайд — кнопки ниже."
)

LEAD_MAGNET_KEYBOARD = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📚 Бесплатный канал", url=config.CHANNEL_LINK)],
    [InlineKeyboardButton(text=f"🔒 Закрытый канал {config.PAID_CHANNEL_PRICE}", url=config.PAID_CHANNEL_LINK)],
    [InlineKeyboardButton(text=f"🧠 Полный нейрогайд {config.NEUROGUIDE_PRICE}", url=config.NEUROGUIDE_LINK)],
])


# ---------- Хендлеры ----------

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Приветствие + выдача PDF-гайда."""
    user = message.from_user
    await database.add_subscriber(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )

    pdf_path = config.PDF_PATH
    if not os.path.exists(pdf_path):
        await message.answer(
            "⚠️ Гайд временно недоступен. Напиши нам — отправим вручную."
        )
        logger.error(f"PDF не найден: {pdf_path}")
        return

    await message.answer(
        "👋 Привет! Я — бот канала <b>SpectrMind</b>.\n\n"
        "Забирай свой бесплатный гайд 👇"
    )
    await message.answer_document(
        document=FSInputFile(pdf_path),
        caption=LEAD_MAGNET_CAPTION,
        reply_markup=LEAD_MAGNET_KEYBOARD,
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🤖 <b>Команды бота:</b>\n\n"
        "/start — получить бесплатный гайд «Нейро-Стек»\n"
        "/help — эта справка\n\n"
        "<b>Админ:</b>\n"
        "/now [категория] — пост в бесплатный канал\n"
        "/now_premium [тип] — пост в премиум канал\n"
        "/preview [категория] — превью поста\n"
        "/broadcast <текст> — рассылка подписчикам\n"
        "/announce <текст> — анонс в канал + рассылка\n"
        "/stats — статистика постов\n"
        "/subscribers — количество подписчиков\n"
        "/schedule — текущее расписание\n\n"
        "<b>Бесплатный канал:</b>\n"
        "• micro_protocol — утренний микро-протокол\n"
        "• research — разбор исследования\n"
        "• myth — разбор мифа\n"
        "• protocol — протокол продуктивности\n\n"
        "<b>Премиум канал:</b>\n"
        "• deep_analysis — глубокий разбор\n"
        "• protocol_plus — расширенный протокол\n"
        "• weekly_digest — дайджест недели"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    stats = await database.get_stats()
    await message.answer(
        f"📊 <b>Статистика канала:</b>\n\n"
        f"✅ Опубликовано постов: {stats['published']}\n"
        f"📝 Черновиков: {stats['drafts']}\n"
        f"💡 Тем в базе: {stats['topics']}\n"
        f"❌ Ошибок за неделю: {stats['errors_week']}"
    )


@router.message(Command("schedule"))
async def cmd_schedule(message: Message):
    text = (
        "📅 <b>Расписание постов:</b>\n\n"
        f"🌅 <b>Каждый день {config.MORNING_HOUR:02d}:{config.MORNING_MINUTE:02d}</b> — микро-протокол\n"
        f"🌆 <b>Каждый день {config.EVENING_HOUR:02d}:{config.EVENING_MINUTE:02d}</b> — разбор исследования\n"
        "🕐 <b>Вт, Чт, Сб 13:00</b> — разбор мифа\n"
        "🕐 <b>Пт, Вс 13:00</b> — протокол продуктивности\n"
    )
    if config.PREMIUM_CHANNEL_ID:
        times = ", ".join(config.PREMIUM_POST_TIMES)
        text += f"\n💎 <b>Премиум канал:</b> {times} (МСК)\n"
    text += f"\nЧасовой пояс: {config.TIMEZONE}"
    await message.answer(text)


@router.message(Command("preview"))
async def cmd_preview(message: Message):
    """Генерирует пост без публикации для проверки."""
    parts = message.text.split(maxsplit=1)
    category = parts[1] if len(parts) > 1 else "research"

    valid = ["micro_protocol", "research", "myth", "protocol"]
    if category not in valid:
        await message.answer(f"❌ Неверная категория. Доступные: {', '.join(valid)}")
        return

    topic = await database.get_random_topic(category)
    if not topic:
        await message.answer("❌ Нет доступных тем в базе.")
        return

    await message.answer("⏳ Генерирую превью поста...")
    try:
        content = await content_generator.generate_post(
            category=category,
            title=topic["title"],
            description=topic["description"],
        )
        await message.answer(
            f"📋 <b>Превью поста:</b>\n"
            f"Категория: {category}\n"
            f"Тема: {topic['title']}\n\n"
            f"{'─' * 30}\n\n{content}"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка генерации: {e}")


@router.message(Command("now"))
async def cmd_now(message: Message):
    """Немедленная публикация поста в канал."""
    parts = message.text.split(maxsplit=1)
    category = parts[1] if len(parts) > 1 else "research"

    valid = ["micro_protocol", "research", "myth", "protocol"]
    if category not in valid:
        await message.answer(f"❌ Неверная категория. Доступные: {', '.join(valid)}")
        return

    topic = await database.get_random_topic(category)
    if not topic:
        await message.answer("❌ Нет доступных тем в базе.")
        return

    await message.answer("⏳ Генерирую и публикую...")
    try:
        content = await content_generator.generate_post(
            category=category,
            title=topic["title"],
            description=topic["description"],
        )

        post_id = await database.save_post(topic["id"], category, content)
        msg = await bot.send_message(
            chat_id=config.CHANNEL_ID,
            text=content,
            parse_mode=ParseMode.HTML,
        )
        await database.mark_published(post_id, channel_msg_id=msg.message_id)

        await message.answer(
            f"✅ Пост опубликован!\n"
            f"ID поста: {post_id}\n"
            f"Тема: {topic['title']}\n"
            f"Сообщение в канале: {msg.message_id}"
        )
    except Exception as e:
        logger.error(f"Ошибка публикации: {e}")
        await message.answer(f"❌ Ошибка: {e}")


@router.message(Command("generate_premium"))
async def cmd_generate_premium(message: Message):
    """Генерация премиум-поста (превью, без публикации)."""
    if not config.is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа.")
        return

    parts = message.text.split(maxsplit=1)
    category = parts[1] if len(parts) > 1 else "deep_analysis"

    valid = ["deep_analysis", "protocol_plus", "weekly_digest"]
    if category not in valid:
        await message.answer(f"❌ Неверная категория. Доступные: {', '.join(valid)}")
        return

    import random
    topics = [t for t in PREMIUM_TOPICS if t[0] == category]
    topic = random.choice(topics)

    await message.answer("⏳ Генерирую премиум-пост...")
    try:
        content = await content_generator.generate_premium_post(
            category=topic[0],
            title=topic[1],
            description=topic[2],
        )
        await message.answer(
            f"💎 <b>Превью премиум-поста:</b>\n"
            f"Категория: {category}\n"
            f"Тема: {topic[1]}\n\n"
            f"{'─' * 30}\n\n{content}"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка генерации: {e}")


PREMIUM_TOPICS = [
    ("deep_analysis", "Нейропластичность и обучение взрослых", "Детальный разбор механизмов нейропластичности после 25 лет"),
    ("deep_analysis", "Дофаминовая система: полный гайд", "Мезолимбический путь, рецепторы D1/D2, сенсибилизация"),
    ("deep_analysis", "Сон и консолидация памяти", "Роль REM и глубокого сна в обучении, глимфатическая система"),
    ("protocol_plus", "Протокол утренней продуктивности", "Полный стек: свет, движение, питание, работа — с таймингами"),
    ("protocol_plus", "Протокол глубокого сна", "Температура, освещение, добавки, дыхание — полный протокол"),
    ("protocol_plus", "Протокол фокуса на 4+ часа", "Блоки, питание, звук, среда — расширенная версия"),
    ("weekly_digest", "Дайджест недели: 3 открытия", "Обзор ключевых исследований недели с практическими выводами"),
]


@router.message(Command("now_premium"))
async def cmd_now_premium(message: Message):
    """Немедленная публикация премиум-поста."""
    if not config.is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа.")
        return

    if not config.PREMIUM_CHANNEL_ID:
        await message.answer("❌ PREMIUM_CHANNEL_ID не настроен в .env")
        return

    parts = message.text.split(maxsplit=1)
    category = parts[1] if len(parts) > 1 else "deep_analysis"

    valid = ["deep_analysis", "protocol_plus", "weekly_digest"]
    if category not in valid:
        await message.answer(f"❌ Неверная категория. Доступные: {', '.join(valid)}")
        return

    import random
    topic = random.choice([t for t in PREMIUM_TOPICS if t[0] == category])

    await message.answer("⏳ Генерирую премиум-пост...")
    try:
        content = await content_generator.generate_premium_post(
            category=topic[0],
            title=topic[1],
            description=topic[2],
        )

        msg = await bot.send_message(
            chat_id=config.PREMIUM_CHANNEL_ID,
            text=content,
            parse_mode=ParseMode.HTML,
        )

        await message.answer(
            f"✅ Премиум-пост опубликован!\n"
            f"Категория: {category}\n"
            f"Тема: {topic[1]}\n"
            f"Сообщение: {msg.message_id}"
        )
    except Exception as e:
        logger.error(f"Ошибка публикации премиум-поста: {e}")
        await message.answer(f"❌ Ошибка: {e}")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    """Рассылка сообщения всем подписчикам бота (только админ)."""
    if not config.is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа.")
        return

    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        await message.answer("Использование: /broadcast <текст сообщения>")
        return

    body = text[1]
    subscribers = await database.get_active_subscribers()
    sent, blocked = 0, 0

    await message.answer(f"📤 Рассылка {len(subscribers)} подписчикам...")

    for sub in subscribers:
        try:
            await bot.send_message(chat_id=sub["user_id"], text=body, parse_mode=ParseMode.HTML)
            sent += 1
        except TelegramForbiddenError:
            await database.deactivate_subscriber(sub["user_id"])
            blocked += 1
        except Exception as e:
            logger.error(f"Ошибка рассылки {sub['user_id']}: {e}")
        await asyncio.sleep(0.05)

    await message.answer(f"✅ Рассылка завершена:\n• Доставлено: {sent}\n• Заблокировали бота: {blocked}")


@router.message(Command("announce"))
async def cmd_announce(message: Message):
    """Публикация анонса в канал + рассылка подписчикам (только админ)."""
    if not config.is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа.")
        return

    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        await message.answer("Использование: /announce <текст анонса>")
        return

    body = text[1]

    # 1. Публикуем в канал
    try:
        msg = await bot.send_message(
            chat_id=config.CHANNEL_ID,
            text=body,
            parse_mode=ParseMode.HTML,
        )
        await message.answer(f"✅ Анонс опубликован в канале (msg_id: {msg.message_id})")
    except Exception as e:
        logger.error(f"Ошибка публикации анонса в канал: {e}")
        await message.answer(f"❌ Ошибка публикации в канал: {e}")
        return

    # 2. Рассылаем подписчикам
    subscribers = await database.get_active_subscribers()
    sent, blocked = 0, 0

    for sub in subscribers:
        try:
            await bot.send_message(chat_id=sub["user_id"], text=body, parse_mode=ParseMode.HTML)
            sent += 1
        except TelegramForbiddenError:
            await database.deactivate_subscriber(sub["user_id"])
            blocked += 1
        except Exception as e:
            logger.error(f"Ошибка рассылки анонса {sub['user_id']}: {e}")
        await asyncio.sleep(0.05)

    await message.answer(f"📤 Рассылка анонса:\n• Доставлено: {sent}\n• Заблокировали бота: {blocked}")


@router.message(Command("subscribers"))
async def cmd_subscribers(message: Message):
    """Статистика подписчиков бота (только админ)."""
    if not config.is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа.")
        return

    count = await database.get_subscriber_count()
    await message.answer(f"👥 Активных подписчиков бота: {count}")


# ---------- Запуск ----------

async def on_startup():
    """Действия при запуске бота."""
    logger.info("Инициализация базы данных...")
    await database.init_db()
    await database.seed_topics()
    logger.info("База данных готова.")

    logger.info("Настройка планировщика...")
    sched.set_bot(bot)
    scheduler = sched.setup_scheduler()
    scheduler.start()
    logger.info("Планировщик запущен.")

    stats = await database.get_stats()
    logger.info(
        f"SpectrMind Bot запущен!\n"
        f"  Канал: {config.CHANNEL_ID}\n"
        f"  Тем в базе: {stats['topics']}\n"
        f"  Постов опубликовано: {stats['published']}\n"
        f"  Расписание: утро {config.MORNING_HOUR:02d}:{config.MORNING_MINUTE:02d}, "
        f"вечер {config.EVENING_HOUR:02d}:{config.EVENING_MINUTE:02d}"
    )


async def main():
    dp.include_router(router)
    dp.startup.register(on_startup)

    logger.info("Запуск бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
