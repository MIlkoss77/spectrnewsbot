import random
from dataclasses import dataclass


@dataclass
class ContentType:
    key: str
    label: str
    weight: int  # relative weight for rotation
    emoji: str


CONTENT_TYPES = {
    "micro_protocol": ContentType(
        key="micro_protocol",
        label="Микро-протокол",
        weight=5,
        emoji="\u2699\ufe0f",
    ),
    "myth_buster": ContentType(
        key="myth_buster",
        label="Разбор мифа",
        weight=4,
        emoji="\u274c",
    ),
    "research_digest": ContentType(
        key="research_digest",
        label="Исследование",
        weight=4,
        emoji="\U0001f52c",
    ),
    "morning_routine": ContentType(
        key="morning_routine",
        label="Утренний протокол",
        weight=3,
        emoji="\u2600\ufe0f",
    ),
    "evening_reflection": ContentType(
        key="evening_reflection",
        label="Вечерний совет",
        weight=2,
        emoji="\U0001f319",
    ),
    "poll": ContentType(
        key="poll",
        label="Опрос",
        weight=3,
        emoji="\U0001f4ca",
    ),
}

RUBRIC_TAGS = {
    "micro_protocol": "\u2699\ufe0f ПРОТОКОЛ",
    "myth_buster": "\u274c МИФ",
    "research_digest": "\U0001f52c ФАКТ",
    "morning_routine": "\u2600\ufe0f ПРОТОКОЛ",
    "evening_reflection": "\U0001f319 СОВЕТ",
    "poll": "\U0001f4ca ОПРОС",
}

SYSTEM_PROMPT = """Ты — контент-редактор Telegram-канала SpectrMind о нейронауке и нейропсихологии.

Правила:
- Пиши ТОЛЬКО на русском языке
- Научный стиль, но доступный обычному человеку
- Ссылайся на реальные исследования (Huberman Lab, Stanford, MIT, Nature, PubMed)
- НЕ давай медицинских рекомендаций — только научные факты и общие советы
- НЕ используй слова: пептиды, инъекции, биомаркеры, диагноз, лечение
- НЕ используй markdown-разметку: никаких звёздочек (*), подчёркиваний (_), обратных кавычек (`), решёток для заголовков (#) — только обычный текст и эмодзи
- Используй эмодзи умеренно (2-4 на пост)
- Пост должен быть 200-400 слов
- Структура: заголовок → основной текст → вывод/призыв → хештеги
- В конце: 3-5 хештегов из этого набора: #нейронаука #мозг #продуктивность #нейропсихология #фокус #сон #дофамин #нейропластичность #саморазвитие #энергия
- Начинай пост с тега-рубрики (ПРОТОКОЛ / МИФ / ФАКТ / ОПРОС / СОВЕТ)
- ВАЖНО: ТЕМА указана в начале сообщения. Пиши СТРОГО про неё. Не придумывай свою тему."""

PROMPTS = {
    "micro_protocol": """Напиши пост-микро-протокол для Telegram-канала SpectrMind.

Формат:
[Эмодзи] Заголовок (до 60 символов, цепляющий)

[Введение: почему это важно, 1-2 предложения]
[Пошаговый протокол: 3-5 шагов, каждый с новой строки]
[Научное обоснование: 1-2 предложения, ссылка на исследование]

[Призыв: попробуй сегодня / сохрани пост]

#хештеги""",

    "myth_buster": """Напиши пост-разбор мифа для Telegram-канала SpectrMind.

Формат поста:
[Эмодзи] МИФ: [утверждение]

[Почему многие так думают]
[Что говорит наука: данные исследований]
[Источник]
[Практический вывод]

#хештеги""",

    "research_digest": """Напиши пост-разбор исследования для Telegram-канала SpectrMind.

Формат поста:
[Эмодзи] Заголовок с интригой

[Контекст: почему это исследование важно]
[Что изучали: методика, участники]
[Главные результаты: 2-3 ключевых вывода]
[Что это значит для тебя: практическое применение]
[Источник: название исследования, журнал, год]

#хештеги""",

    "morning_routine": """Напиши пост-утренний протокол для Telegram-канала SpectrMind.

Формат поста:
[Эмодзи] Доброе утро! [Заголовок]

[Почему именно утро важно для мозга]
[Протокол: 3-4 конкретных действия]
[Научное обоснование]
[Призыв: начни завтра]

#хештеги""",

    "evening_reflection": """Напиши пост-вечерний совет для Telegram-канала SpectrMind.

Формат поста:
[Эмодзи] [Заголовок про вечер/восстановление]

[Почему вечер критичен для мозга]
[2-3 конкретных совета с обоснованием]
[Источник]
[Призыв: попробуй сегодня вечером]

#хештеги""",

    "poll": """Напиши пост-опрос для Telegram-канала SpectrMind.

Формат поста:
[Эмодзи] Вопрос-заголовок (короткий, цепляющий)

[Контекст: 2-3 предложения, почему это важно]

Варианты ответа (4 штуки, каждый с новой строки, без нумерации):
Вариант 1
Вариант 2
Вариант 3
Вариант 4

[Призыв: голосуй / напиши свой вариант в комментариях]

#хештеги""",
}


def get_random_content_type() -> str:
    """Pick a content type using weighted random selection."""
    types = list(CONTENT_TYPES.values())
    weights = [t.weight for t in types]
    chosen = random.choices(types, weights=weights, k=1)[0]
    return chosen.key


def get_prompt(content_type: str) -> str:
    """Get the generation prompt for a content type."""
    return PROMPTS.get(content_type, PROMPTS["micro_protocol"])


def get_emoji(content_type: str) -> str:
    """Get the emoji prefix for a content type."""
    ct = CONTENT_TYPES.get(content_type)
    return ct.emoji if ct else "\U0001f9e0"


def get_rubric_tag(content_type: str) -> str:
    """Get the rubric tag for a content type."""
    return RUBRIC_TAGS.get(content_type, "")


# Morning slot types (protocol-first strategy: practice > facts)
MORNING_TYPES = ["micro_protocol", "morning_routine"]
# Midday and evening types (full rotation including facts, myths, polls)
DAY_EVENING_TYPES = ["micro_protocol", "myth_buster", "research_digest", "evening_reflection", "poll"]


def get_content_type_for_slot(hour: int) -> str:
    """Pick a content type based on the time slot.

    Morning (before 10): always protocol (micro_protocol or morning_routine)
    Day/Evening: weighted random from all types
    """
    if hour < 10:
        return random.choice(MORNING_TYPES)
    types = [CONTENT_TYPES[t] for t in DAY_EVENING_TYPES if t in CONTENT_TYPES]
    weights = [t.weight for t in types]
    chosen = random.choices(types, weights=weights, k=1)[0]
    return chosen.key
