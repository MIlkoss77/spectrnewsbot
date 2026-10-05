"""Offline self-check for the SpectrMind content pipeline.

Runs the whole generation path with a stubbed OpenRouter call, so the
prompt/validation/rotation logic can be verified without network access.

Usage:
    python tools_selfcheck.py
"""
import asyncio
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from content import generator, topic_pool  # noqa: E402
import config  # noqa: E402
from content.prompts import (  # noqa: E402
    CONTENT_TYPES, PREMIUM_CONTENT_TYPES, PROMPTS, PREMIUM_PROMPTS, RUBRIC_TAGS,
    SYSTEM_PROMPT, PREMIUM_SYSTEM_PROMPT, DAY_EVENING_TYPES, get_content_type_for_slot,
    get_hashtags, get_min_words,
)

STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".selfcheck_state")

# Captured before any test replaces generator._call_openrouter with a stub.
ORIGINAL_CALL_OPENROUTER = generator._call_openrouter

PASSED = []
FAILED = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(name)
        print(f"  ok   {name}")
    else:
        FAILED.append(f"{name}{': ' + detail if detail else ''}")
        print(f"  FAIL {name}{': ' + detail if detail else ''}")


# A realistic, cliché-free post used to exercise the happy path.
GOOD_POST = """Кофе сразу после пробуждения кажется логичным. Кофеин блокирует аденозин — вещество, которое создаёт ощущение сонливости, и на короткое время это действительно работает.

Проблема в том, что аденозин никуда не девается. Он просто ждёт, пока кофеин перестанет занимать рецепторы, и потом накрывает сильнее.

В исследованиях по сну эффект заметнее у тех, кто пьёт кофе в первые 30 минут после подъёма: они дольше засыпают вечером и чаще просыпаются ночью. Отсрочка первой чашки на 60–90 минут помогает мягче.

Попробуйте на этой неделе подождать с кофе до конца первого рабочего часа. Заметили разницу к вечеру?

#нейронаука #сон #кофеин"""

SHORT_POST = "Короткий обрывок текста без концовки"

# Structured poll output, as the poll prompt requests it.
POLL_POST = """ВОПРОС: Как вы засыпаете чаще всего?

Засыпание — маркер состояния нервной системы.

ВАРИАНТЫ:
Быстро, за 10 минут
20-30 минут
Дольше часа
По-разному

Голосуй и напиши в комментариях, что помогает именно тебе."""

# Long-form fixture for the premium pipeline (needs >= 250 real words).
PREMIUM_POST = """Сколько часов вы спите в будни? Большинство отвечает «семь» и удивляется, почему к четвергу голова работает хуже, чем в понедельник. Разница между семью часами и восемью кажется мелочью, но именно на этом промежутке меняется работа памяти.

В экспериментах с ограничением сна участников делили на группы: одним давали спать по восемь часов, другим по шесть, третьим по четыре. Каждые сутки все проходили тесты на внимание и запоминание слов. Через две недели группа с восемью часами держала результат, группа с шестью теряла около четверти точности, группа с четырьмя падала почти вдвое.

Самое интересное в другом. Участники из группы шести часов оценивали своё состояние как нормальное. Они привыкли к новой планке и перестали замечать снижение. Это называют субъективной адаптацией: ощущение бодрости восстанавливается быстрее, чем реальные когнитивные функции.

Механизм связан с консолидацией памяти. Во время медленноволнового сна гиппокамп проигрывает дневной опыт и передаёт его в кору, где воспоминания закрепляются. Сократите сон на пару часов, и последний цикл, где как раз преобладает быстрый сон с медленными волнами, просто не состоится. Информация за день остаётся в промежуточном хранилище и частично теряется.

Что это значит на практике. Недельный долг по сну нельзя закрыть одной длинной ночью в субботу: исследования показывают, что внимание после отсыпания восстанавливается, а метаболические показатели и точность работы с текстом отстают. Устойчивее работает сдвиг времени отхода ко сну на тридцать минут и фиксированное время подъёма без исключений на выходных.

Есть и ограничение, о котором честно говорят сами авторы. Часть этих работ проводилась в лабораториях, где люди спали под датчиками в непривычных условиях, а участники были молодыми и здоровыми. Переносить выводы на всех подряд нельзя: индивидуальная потребность во сне колеблется от шести до девяти часов, и редкие люди переносят недосып заметно легче остальных.

Проверьте на себе простым способом. Если через пять минут после будильника вы снова засыпаете, а к обеду нужен второй кофе, чтобы просто читать, вы, скорее всего, недосыпаете. Попробуйте две недели ложиться на полчаса раньше, не меняя время подъёма, и посмотрите на разницу в конце второй недели.

#нейронаука #сон #память #исследования"""

STATS = {"calls": 0}


async def fake_good(model, user_prompt, system_prompt=None, max_tokens=1600):
    STATS["calls"] += 1
    return GOOD_POST


async def fake_short(model, user_prompt, system_prompt=None, max_tokens=1600):
    STATS["calls"] += 1
    return SHORT_POST


async def fake_poll(model, user_prompt, system_prompt=None, max_tokens=1600):
    STATS["calls"] += 1
    return POLL_POST


async def fake_premium(model, user_prompt, system_prompt=None, max_tokens=1600):
    STATS["calls"] += 1
    return PREMIUM_POST


class FakeResponse:
    def __init__(self, status_code=200, payload=None, bad_json=False):
        self.status_code = status_code
        self._payload = payload
        self._bad_json = bad_json

    @property
    def text(self):
        """The generator logs this on error responses."""
        if self._payload is None:
            return ""
        return json.dumps(self._payload, ensure_ascii=False)

    def json(self):
        if self._bad_json:
            raise ValueError("not json")
        return self._payload


class FakeClient:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, *args, **kwargs):
        return self._response


def patch_response(response):
    generator.httpx.AsyncClient = lambda **kwargs: FakeClient(response)


class FakeBot:
    """Records what the publisher would send to Telegram."""

    def __init__(self):
        self.messages = []
        self.polls = []

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)
        return None

    async def send_poll(self, **kwargs):
        self.polls.append(kwargs)
        return None


async def main() -> int:
    print("1. Prompt and content-type wiring")
    for key in CONTENT_TYPES:
        check(f"prompt exists for {key}", key in PROMPTS)
        check(f"rubric tag exists for {key}", key in RUBRIC_TAGS)
        check(f"hashtags exist for {key}", bool(get_hashtags(key)))
        check(f"topic pool exists for {key}", bool(topic_pool.TOPIC_POOL.get(key)),
              "pool missing")
    for key in PREMIUM_CONTENT_TYPES:
        check(f"premium prompt exists for {key}", key in PREMIUM_PROMPTS)
    for key in DAY_EVENING_TYPES:
        check(f"rotation lists {key}", key in CONTENT_TYPES)

    print("\n2. Off-topic rubrics are reachable in the 09:00 slot")
    seen = set()
    for _ in range(4000):
        seen.add(get_content_type_for_slot(9))
    for key in ("supplement_recap", "health_news", "brain_curiosity"):
        check(f"{key} can be picked at 09:00", key in seen)
    check("protocols stay dominant at 09:00",
          len([1 for _ in range(2000) if get_content_type_for_slot(9) in ("micro_protocol", "morning_routine")]) > 600)

    print("\n3. Style rules actually reach the model prompt")
    check("system prompt bans cliches", "в современном мире" in SYSTEM_PROMPT)
    check("medical limits are enforced verbatim on supplements",
          "НЕ называешь дозы" in PROMPTS["supplement_recap"]
          and "пропейте курс" in PROMPTS["supplement_recap"])
    check("premium prompt has voice block", "умный друг" in PREMIUM_SYSTEM_PROMPT)
    check("supplement brief forbids dosing",
          "дозы" in PROMPTS["supplement_recap"] and "пропейте курс" in PROMPTS["supplement_recap"])

    print("\n4. Text cleaning keeps Russian punctuation")
    raw = "## Заголовок\n\nТекст **жирный** и *курсив*, `код`, тире — вот такое, кавычки «ёлочки».\n\n#хештег"
    cleaned = generator._clean_text(raw)
    check("heading markers removed", "## " not in cleaned)
    check("asterisks removed", "*" not in cleaned)
    check("backticks removed", "`" not in cleaned)
    check("em dash preserved", "—" in cleaned)
    check("guillemets preserved", "«ёлочки»" in cleaned)
    check("hashtag preserved", "#хештег" in cleaned)

    print("\n5. Completeness thresholds per rubric")
    check("poll is treated as short-form", get_min_words("poll") < get_min_words("micro_protocol"),
          f"poll={get_min_words('poll')} protocol={get_min_words('micro_protocol')}")
    check("news is shorter than research", get_min_words("health_news") < get_min_words("research_digest"))
    check("premium needs long-form", generator.get_premium_min_words() > get_min_words("research_digest"))
    check("hashtags do not count as words",
          generator.count_words("Текст один два.\n\n#бады #исследования #здоровье") == 3,
          str(generator.count_words("Текст один два.\n\n#бады #исследования #здоровье")))
    check("short text rejected", not generator._is_complete(SHORT_POST))
    check("good text accepted", generator._is_complete(GOOD_POST))
    check("truncated tail trimmed", generator._trim_incomplete_tail(
        GOOD_POST + "\n\nИ тут модель оборвалась на полуслов") != GOOD_POST + "\n\nИ тут модель оборвалась на полуслов")

    print("\n6. Cliché detection")
    check("clean post has no hits", generator._banned_hits(GOOD_POST) == [])
    check("cliche detected", "в современном мире" in generator._banned_hits("В современном мире это важно."))
    check("cancelerit detected", "является" in generator._banned_hits("Сон является важным фактором."))
    check("honest refusal is not a style hit", generator._banned_hits("Это не лечение и не диагноз.") == [])
    check("medical framing is advisory only",
          "дозировки" in generator._medical_notes("Дозировки подбирают индивидуально."))
    check("medical words do not block publishing", generator._banned_hits("Дозировки подбирают индивидуально.") == [])

    print("\n7. Hashtag normalisation")
    tagged = generator._ensure_hashtags("Текст без хештегов.", "supplement_recap")
    check("hashtags appended", "#бады" in tagged)
    replaced = generator._ensure_hashtags(GOOD_POST, "supplement_recap")
    check("model hashtags replaced by rubric set", "#бады" in replaced and "#сон" not in replaced)
    check("replacement does not leave duplicates", replaced.count("#бады") == 1)
    check("body text preserved", "Кофеин блокирует аденозин" in replaced)

    print("\n8. Full generation path (stubbed API)")
    if os.path.isdir(STATE_DIR):
        shutil.rmtree(STATE_DIR)
    os.makedirs(STATE_DIR, exist_ok=True)
    topic_pool.POOL_STATE_FILE = os.path.join(STATE_DIR, "topic_state.json")
    topic_pool.RECENT_TOPICS_FILE = os.path.join(STATE_DIR, "recent_topics.json")

    generator._call_openrouter = fake_good
    ctype, text = await generator.generate_content("supplement_recap")
    check("returns requested rubric", ctype == "supplement_recap")
    check("rubric tag prepended", text.split("\n", 1)[0].strip().lower().startswith("\U0001f9ea"))
    check("hashtags present", "#бады" in text)
    check("word count sane", len(text.split()) > 60)

    generator._call_openrouter = fake_poll
    ctype, poll = await asyncio.wait_for(generator.generate_content("poll"), timeout=30)
    check("poll rubric returns a PollPost", ctype == "poll" and isinstance(poll, generator.PollPost))
    check("poll has question and options", bool(poll.question) and len(poll.options) == 4)

    generator._call_openrouter = fake_short
    failed = False
    try:
        await generator.generate_content("brain_curiosity")
    except RuntimeError:
        failed = True
    check("stub short output exhausts retries and raises", failed)

    generator._call_openrouter = fake_premium
    ctype, text = await asyncio.wait_for(generator.generate_premium_content(), timeout=30)
    check("premium generation works", ctype in PREMIUM_CONTENT_TYPES)
    check("premium tag lowercase", "глубокий разбор" in text.lower() or "протокол+" in text.lower()
          or "дайджест" in text.lower())
    check("premium hashtags present", "#" in text.rstrip().split("\n")[-1])

    print("\n9. Topic rotation avoids identical topics")
    topics = [topic_pool.get_next_topic("health_news") for _ in range(12)]
    check("no duplicates in first rotation", len(set(topics)) == len(topics),
          f"{len(set(topics))}/{len(topics)} unique")
    state = json.load(open(topic_pool.POOL_STATE_FILE, encoding="utf-8"))
    check("rotation state persisted", "health_news" in state)

    print("\n10. Markdown never reaches a post")
    check("clean post stays clean",
          not re.search(r"(?<!\w)\*|`|^\s*#\s", generator._clean_text(GOOD_POST), re.M))

    print("\n11. Broken API responses never crash generation")
    # Sections 8-9 replaced _call_openrouter on the module with stubs, so the
    # real function has to be taken from source, not from the patched module.
    real_call = ORIGINAL_CALL_OPENROUTER
    real_client = generator.httpx.AsyncClient
    try:
        # OpenRouter can answer 200 with null content (observed with
        # deepseek/deepseek-v4-flash on the production server).
        patch_response(FakeResponse(200, {"choices": [{"message": {"content": None},
                                                      "finish_reason": "stop"}]}))
        check("null content returns None", await real_call("m", "p") is None)

        patch_response(FakeResponse(200, {"error": {"message": "model not found"}}))
        check("200 with error object returns None", await real_call("m", "p") is None)

        patch_response(FakeResponse(200, {}))
        check("missing choices returns None", await real_call("m", "p") is None)

        patch_response(FakeResponse(404, {"error": {"message": "no endpoints"}}))
        check("404 returns None", await real_call("m", "p") is None)

        patch_response(FakeResponse(200, None, bad_json=True))
        check("non-JSON returns None", await real_call("m", "p") is None)

        patch_response(FakeResponse(200, {"choices": [{"message": {"content": ""},
                                                      "finish_reason": "content_filter"}]}))
        check("refused completion returns None", await real_call("m", "p") is None)

        patch_response(FakeResponse(200, {"choices": [{
            "message": {"content": [{"type": "text", "text": "Частичный ответ."}]},
            "finish_reason": "stop"}]}))
        check("list content is joined", (await real_call("m", "p")) == "Частичный ответ.")
    finally:
        generator.httpx.AsyncClient = real_client
        generator._call_openrouter = real_call

    print("\n12. Poll rendering goes through send_poll, not text")
    poll_text = """ВОПРОС: Сколько часов вы спите в среднем?

Сон — базовая функция, от которой зависит почти всё остальное.

ВАРИАНТЫ:
До 6 часов
6-7 часов
7-8 часов
Больше 9 часов

Голосуй и расскажи в комментариях, как у тебя с режимом."""

    poll = generator._parse_poll_text(poll_text, "poll")
    check("poll parsed", poll is not None)
    check("question extracted", poll.question == "Сколько часов вы спите в среднем?",
          repr(poll.question))
    check("four options extracted", len(poll.options) == 4, str(poll.options))
    check("options have no bullets or emoji",
          all(not re.match(r"^[-•*\d.\s]", o) for o in poll.options), str(poll.options))
    check("invitation line is not an option",
          not any("комментар" in o.lower() for o in poll.options))
    check("intro captured", "базовая функция" in poll.intro)
    check("hashtags attached to poll", "#" in poll.hashtags)

    broken = generator._parse_poll_text("Просто текст без структуры опроса.", "poll")
    check("malformed poll rejected", broken is None)
    few = generator._parse_poll_text("ВОПРОС: Тест?\n\nВАРИАНТЫ:\nДа\n", "poll")
    check("poll with one option rejected", few is None)
    check("question detection rejects short lines",
          not generator._is_question_line("Да"))
    check("question detection accepts a question",
          generator._is_question_line("Сколько часов вы спите?"))

    print("\n13. Publisher sends polls and attaches CTA buttons")
    import scheduler as sched

    bot = FakeBot()
    await sched.send_post(bot, "poll", poll, with_cta=False)
    check("one context message sent", len(bot.messages) == 1)
    check("one poll sent", len(bot.polls) == 1)
    check("poll carries question", bot.polls[0]["question"] == poll.question)
    check("poll carries 4 options", len(bot.polls[0]["options"]) == 4)
    check("poll is anonymous single-choice",
          bot.polls[0]["is_anonymous"] is True and bot.polls[0]["allows_multiple_answers"] is False)

    bot = FakeBot()
    await sched.send_post(bot, "micro_protocol", GOOD_POST, with_cta=True)
    check("text post uses send_message", len(bot.messages) == 1 and not bot.polls)
    check("CTA text attached", "21-дневный протокол" in bot.messages[0]["text"])
    check("buttons attached to text post", bot.messages[0]["reply_markup"] is not None)

    bot = FakeBot()
    await sched.send_post(bot, "micro_protocol", GOOD_POST, with_cta=False)
    check("no CTA when not a CTA post", "21-дневный протокол" not in bot.messages[0]["text"])

    print("\n14. CTA buttons and rotation")
    kb = sched.build_keyboard(with_pay_buttons=True)
    kb_urls = [btn.url for row in kb.inline_keyboard for btn in row]
    check("CTA keyboard leads to the bot", config.BOT_LINK in kb_urls)
    check("free-channel invite is off by default",
          config.CHANNEL_LINK not in kb_urls and config.SHOW_CHANNEL_BUTTON is False)

    # Same call with the channel button switched on — the flag is read from
    # config at import time, so patch it on the scheduler module.
    sched.SHOW_CHANNEL_BUTTON = True
    try:
        kb_on = sched.build_keyboard(with_pay_buttons=True)
        urls_on = [btn.url for row in kb_on.inline_keyboard for btn in row]
        check("channel button appears when enabled", config.CHANNEL_LINK in urls_on)
    finally:
        sched.SHOW_CHANNEL_BUTTON = False

    plain_kb = sched.build_keyboard(with_pay_buttons=False)
    check("plain posts carry no keyboard at all", plain_kb is None,
          repr(plain_kb))

    texts = {config.get_cta_text(i) for i in range(len(config.CTA_VARIANTS))}
    check("CTA variants differ", len(texts) == len(config.CTA_VARIANTS))
    check("CTA variants mention the pain",
          all(any(w in t for w in ("тревог", "сон", "стресс", "голов")) for t in texts))
    check("CTA variants name the bot", all(config.BOT_USERNAME in t for t in texts))
    check("CTA offers the 21-day protocol", all("21-дневный" in t for t in texts))
    check("CTA cycles", config.get_cta_text(len(config.CTA_VARIANTS)) == config.get_cta_text(0))

    print("\n15. Startup post is silent by default")
    check("STARTUP_POST defaults to false", config.STARTUP_POST is False)

    bot = FakeBot()
    await sched.send_post(bot, "micro_protocol", GOOD_POST, with_cta=False, with_buttons=False)
    check("bare post has no text CTA", "21-дневный" not in bot.messages[0]["text"])
    check("bare post has no buttons", bot.messages[0]["reply_markup"] is None)

    bot = FakeBot()
    await sched.send_post(bot, "micro_protocol", GOOD_POST, with_cta=False, with_buttons=True)
    check("plain scheduled post also has no keyboard", bot.messages[0]["reply_markup"] is None)

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        for line in FAILED:
            print(f"  - {line}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
