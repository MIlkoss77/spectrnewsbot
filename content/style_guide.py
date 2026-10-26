"""Shared voice and formatting rules for all SpectrMind prompts.

Keeping the style rules in one place means every rubric (protocols, myth
busters, supplement research, health news) sounds like the same person
writing, instead of eight different template-filling robots.
"""

# Words and phrases the model must not use. These are all stylistic: they are
# the tells of generated text, the exact thing that makes posts read like a
# press release instead of a human writing.
#
# Medical framing is handled by MEDICAL_LIMITS below rather than by word
# matching: Russian needs those words to state the limits ("это не лечение"),
# and a supplement post may legitimately discuss инъекции as a research
# method. Those are logged as advisory notes, never used to regenerate a post.
BANNED_PHRASES = [
    "в современном мире",
    "в наше время",
    "не секрет, что",
    "важно отметить",
    "стоит отметить",
    "нельзя не отметить",
    "в заключение",
    "подводя итог",
    "данный",
    "данная",
    "данное",
    "является",
    "осуществлять",
    "в рамках данного",
    "играет важную роль",
    "широкий спектр",
    "комплексный подход",
    "давайте разберёмся",
    "давайте разберемся",
    "как известно",
    "специалисты рекомендуют",
    "учёные доказали",
    "ученые доказали",
    "это может быть полезно для вас",
]

# Post-hoc advisory check only: never triggers a regeneration, because the
# same words appear in debunking and in accurate research descriptions.
MEDICAL_LIMITS = [
    "пептиды",
    "инъекции",
    "биомаркеры",
    "назначать",
    "дозировка",
    "дозировки",
    "принимайте",
    "пропейте",
    "курс приёма",
    "курс приема",
]

BANNED_RULES = "\n".join(f'— {p}' for p in BANNED_PHRASES)

# A compact version of the same idea, used in per-post prompts. Repeating the
# whole list there is what caused posts to be rejected and regenerated for a
# single phrase, so the rubric brief only carries the short reminder.
STYLE_REMINDER = """
Тон и чистка текста:
— Живой, разговорный язык: пиши как умный друг в личном сообщении, без академизма и лекторского тона.
— Максимальная краткость: 60–90 слов. 2–3 ёмких абзаца по 1–2 предложения. Читается за 25 секунд.
— Без штампов и канцелярита: «в современном мире», «важно отметить», «является», «данный», «играет важную роль».
— Без markdown: ни звёздочек, ни подчёркиваний, ни решёток для заголовков.
— Без шаблонных финалов вроде «берегите себя» и «а что думаете вы?».
"""

# How to pronounce numbers, units and research references.
FACT_RULES = """
Как обращаться с фактами и цифрами:
— Каждая цифра должна быть из реального исследования или обзора. Не помнишь точную — не подставляй, скажи словами без выдуманного числа.
— Не выдумывай названия исследований, авторов, журналов и годы. Сомневаешься в ссылке — лучше сказать «в исследованиях по этой теме» без ложной точности.
— Формат ссылки: коротко и по делу, прямо в тексте — «в обзоре 2023 года», «в экспериментах на людях», «мета-анализ 2019-го». Полное название с авторами оставь только там, где оно реально нужно.
— Не обещай результат и не советуй, что кому принимать. Ты рассказываешь, что показали исследования, и оставляешь решение читателю.
"""

# Formatting rules for Telegram delivery. The bot sends plain text
# (parse_mode=None), so markdown would leak into the channel as raw symbols.
FORMAT_RULES = """
Формат для Telegram:
— Пиши обычным текстом с эмодзи. НЕ используй markdown: никаких *, _, `, #, [ ] и заголовков через решётку.
— Хештеги только в самом конце поста.
— Абзацы по 1–3 предложения, между ними пустая строка. Такой текст читается с телефона.
— 2–4 эмодзи на пост, по смыслу, а не украшательство в начале каждого абзаца.
"""

BRAND_LINE = "Ты пишешь для Telegram-канала SpectrMind — о мозге, теле и внимании."

# The core tone instruction. This is the part that makes posts human:
# it defines a person to sound like, not a structure to fill in.
VOICE = """Как ты пишешь:
Ты — живой человек, умный друг, который делится инсайтом. Не лектор, не ведущий вебинара, не методичка. На «ты», по-человечески, просто и ёмко.

Ультра-краткость (60–90 слов). Никто в Telegram не читает длинные простыни. Вырезай вводные слова, воду и очевидности. 2–3 коротких абзаца.

Хук вместо разгона. Первая строка — это крючок: вопрос, узнаваемая сцена из жизни («когда утром нет сил встать»), парадокс. Никаких «В современном мире...», «Сегодня поговорим о...».

Конкретный физиологический факт простыми словами. Не «улучшает когнитивные функции», а «мозг быстрее переключает внимание» или «пульс падает через 40 секунд».

Одно действие или одна мысль. Не нагружай пятью советами. Дай один точный практический приём, который можно применить сегодня.

Живой ритм. Короткие фразы. Чередуй длину. Никаких придаточных предложений на 3 строки.

Чего в тексте быть не должно (это главные приметы машинного текста):
— структуры доклада: «Введение», «Шаг 1 / Шаг 2», «Вывод»;
— списков из пунктов ради красивой структуры;
— канцелярита и штампов;
— вывода, повторяющего уже сказанное;
— шаблонных финалов отдельной строкой («Будьте здоровы!», «А что думаете вы?»).

Не употребляй эти слова и обороты: {banned}. Список не единственный — если оборот звучит как из отчёта или учебника, перепиши живым языком.
"""


def build_voice_block() -> str:
    """Return the full tone block with the banned-phrase list inlined."""
    return VOICE.format(banned=BANNED_RULES)


# Small per-post nudges so consecutive posts don't open the same way.
OPENING_VARIETY = [
    "Начни с неудобного вопроса читателю.",
    "Начни с конкретной сцены: что человек делает и что при этом происходит.",
    "Начни с цифры или результата — и сразу объясни, почему это странно.",
    "Начни с распространённого совета и сразу скажи, что с ним не так.",
    "Начни с короткого наблюдения из жизни, без обобщений.",
]

# Length is per content type; these are the defaults.
DEFAULT_MIN_WORDS = 40

# Minimum word counts used to detect truncated output. They are lower than
# the target lengths in the prompts (which are 60–90 words): this is a floor
# for "did the model get cut off", not a style target.
MIN_WORDS_SHORT = 30     # poll: context + options
MIN_WORDS_MEDIUM = 35    # news: headline-driven, can be compact
MIN_WORDS_DEFAULT = 40   # everything else (target: 60-90 words)
MIN_WORDS_PREMIUM = 250  # premium posts are long-form by definition
