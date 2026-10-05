import logging
import random
import re
from typing import Optional, Tuple

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_URL, FALLBACK_MODELS, PROXY_URL
from content.prompts import (
    SYSTEM_PROMPT, PREMIUM_SYSTEM_PROMPT, get_prompt, get_random_content_type,
    get_content_type_for_slot, get_rubric_tag, get_hashtags, get_min_words, CONTENT_TYPES,
    get_premium_content_type, get_premium_prompt, get_premium_rubric_tag,
    get_premium_min_words, PREMIUM_CONTENT_TYPES,
)
from content.style_guide import (
    BANNED_PHRASES,
    MEDICAL_LIMITS,
    OPENING_VARIETY,
    STYLE_REMINDER,
)
from content.topic_pool import get_next_topic, get_next_premium_topic

logger = logging.getLogger(__name__)

TIMEOUT = 60
MAX_GENERATION_RETRIES = 2

# Words that appear in the disabled-medical list but are also needed to
# describe a *refusal* to give medical advice ("это не лечение"). Flagging
# them would make honest posts fail, so the style check ignores them.
BANNED_CHECK_EXCEPTIONS = {"лечение", "лечить", "вылечить", "диагноз"}
CTA_TEXT = (
    "\n\n---\n"
    "\U0001f4a1 Полный гайд по нейро-оптимизации "
    "\u2192 spectrmind.ru"
)


def _clean_text(text: str) -> str:
    """Remove markdown artifacts from generated text.

    The bot posts with parse_mode=None, so any markdown the model emits
    would show up in the channel as literal symbols. Em dashes and Russian
    quotation marks are left alone; only real markdown markers are stripped.
    """
    text = text.replace("```", "")
    text = re.sub(r"`([^`]*)`", r"\1", text)          # inline code
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)    # bold
    text = re.sub(r"(?<!\w)\*([^*\n]+)\*(?!\w)", r"\1", text)  # italic
    text = re.sub(r"__([^_]+)__", r"\1", text)        # bold underscore
    text = text.replace("**", "").replace("~~", "").replace("*", "").replace("`", "")
    # Heading markers like "## Заголовок" — only when followed by a space,
    # so real hashtags (#нейронаука) survive.
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.splitlines()]
    cleaned = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                cleaned.append("")
            prev_blank = True
        else:
            cleaned.append(line)
            prev_blank = False
    return "\n".join(cleaned).strip()


def _banned_hits(text: str) -> list:
    """Return stylistic clichés found in the text (the 'sounds like a bot' tells).

    These trigger one regeneration attempt. Medical vocabulary is not checked
    here on purpose — see MEDICAL_LIMITS and _medical_notes.
    """
    lowered = text.lower()
    hits = []
    for phrase in BANNED_PHRASES:
        if phrase in BANNED_CHECK_EXCEPTIONS:
            continue
        if phrase in lowered:
            hits.append(phrase)
    return hits


def _medical_notes(text: str) -> list:
    """Advisory-only scan for medical framing (never blocks publication)."""
    lowered = text.lower()
    return [phrase for phrase in MEDICAL_LIMITS if phrase in lowered]


def _is_hashtag_line(line: str) -> bool:
    """True for lines that are basically only hashtags."""
    tokens = line.split()
    if not tokens:
        return False
    tags = [t for t in tokens if t.startswith("#")]
    return len(tags) >= max(2, len(tokens) - 1)


def _ensure_hashtags(text: str, content_type: str) -> str:
    """End the post with the rubric's hashtags, replacing whatever the model wrote.

    Left to itself the model mixes hashtags freely, so a supplement post could
    end up tagged #сон. Swapping in the rubric's own set keeps the channel's
    tagging consistent and makes every post findable by rubric.
    """
    tags = get_hashtags(content_type)
    if not tags:
        return text.rstrip()

    lines = text.rstrip().split("\n")
    while lines and (not lines[-1].strip() or _is_hashtag_line(lines[-1])):
        lines.pop()

    body = "\n".join(lines).rstrip()
    return f"{body}\n\n{tags}" if body else tags


def _hashtags_in(text: str) -> list:
    return re.findall(r"#[\w\u0400-\u04FF]+", text)


def count_words(text: str) -> int:
    """Count real words, ignoring the hashtag block and the HTML-ish artifacts.

    Hashtags must not count towards the length floor: a post could otherwise
    pass the completeness check on hashtags alone.
    """
    stripped = re.sub(r"#[\w\u0400-\u04FF]+", " ", text)
    stripped = re.sub(r"[-—–]{3,}", " ", stripped)
    return len(stripped.split())


def _is_complete(text: str, min_words: int = 80) -> bool:
    """Check if generated text looks complete (not truncated)."""
    if not text:
        return False

    word_count = count_words(text)
    if word_count < min_words:
        logger.warning("Text too short: %d words (min %d)", word_count, min_words)
        return False

    # Check if text ends with hashtags or proper punctuation
    stripped = text.rstrip()
    last_line = stripped.split("\n")[-1].strip()

    # Ends with hashtags (common pattern for TG posts)
    if re.search(r"#\S+$", last_line):
        return True

    # Ends with proper sentence-ending punctuation
    if stripped.endswith((".", "!", "?", ":", ")", "\u201d", "\u00ab")):
        return True

    # Last line is a single word without punctuation — likely cut off
    if len(last_line.split()) <= 2 and not last_line.endswith((".", "!", "?")):
        logger.warning("Text appears truncated, last line: %r", last_line[:60])
        return False

    logger.warning("Text completeness uncertain, last 30 chars: %r", stripped[-30:])
    return False


def _trim_incomplete_tail(text: str, min_words: int = 80) -> str:
    """Trim incomplete trailing content, keeping only complete paragraphs."""
    if not text:
        return text

    # Split into paragraphs (double newline separated)
    paragraphs = text.split("\n\n")

    # Find the last paragraph that ends with proper punctuation
    last_complete = len(paragraphs)
    for i in range(len(paragraphs) - 1, -1, -1):
        para = paragraphs[i].strip()
        if para and (para.endswith((".", "!", "?", ")", "\u201d")) or re.search(r"#\S+$", para)):
            last_complete = i + 1
            break

    trimmed = "\n\n".join(paragraphs[:last_complete])

    # If we trimmed too aggressively, return original rather than a stub
    if count_words(trimmed) < min_words:
        logger.warning("Trimming too aggressive (%d words), keeping original", count_words(trimmed))
        return text

    logger.info("Trimmed from %d to %d words", count_words(text), count_words(trimmed))
    return trimmed


def _add_rubric_tag(text: str, content_type: str) -> str:
    """Prepend a short rubric tag to the post if not already present."""
    tag = get_rubric_tag(content_type)
    if not tag:
        return text
    # Compare the rubric word, ignoring case, against the opening line
    first_line = text.split("\n", 1)[0].strip().lower()
    if tag.split()[-1] in first_line:
        return text
    return f"{tag}\n\n{text}"


def _style_variation() -> str:
    """Return a per-post nudge so consecutive posts don't open identically."""
    return f"\n\nДополнительно к тону: {random.choice(OPENING_VARIETY)}"


def _build_prompt(topic: str, base_prompt: str, hashtags: str = "") -> str:
    """Assemble the final user prompt: topic, rubric brief, style, hashtags."""
    parts = [
        f"ТЕМА ПОСТА: {topic}",
        "",
        base_prompt,
        "",
        "Напоминание, оно важнее привычек модели:",
        STYLE_REMINDER.strip(),
    ]
    if hashtags:
        parts += [
            "",
            f"В самом конце поста поставь эти хештеги одной строкой: {hashtags}",
        ]
    parts += [
        "",
        "Тему сверху не пересказывай дословно и не копируй её формулировку как заголовок — "
        "перепиши её живой фразой своими словами.",
        "Пиши строго про указанную тему.",
        _style_variation(),
    ]
    return "\n".join(parts)


async def _generate_with_fallback(
    topic: str,
    content_type: str,
    base_prompt: str,
    system_prompt: str,
    min_words: int,
    max_tokens: int,
    premium: bool = False,
) -> Tuple[str, str]:
    """Shared generation pipeline: retries, fallbacks, style and tag checks."""
    hashtags = get_hashtags(content_type)
    prompt = _build_prompt(topic, base_prompt, hashtags)
    models = [OPENROUTER_MODEL] + list(FALLBACK_MODELS)
    kind = "premium type" if premium else "type"

    async def attempt_generation(model: str) -> Optional[str]:
        return await _call_openrouter(
            model, prompt, system_prompt=system_prompt, max_tokens=max_tokens
        )

    def finish(text: str, model: str, note: str = "") -> Tuple[str, str]:
        text = _trim_incomplete_tail(text, min_words) if note == "trimmed" else text
        text = _ensure_hashtags(text, content_type)
        medical = _medical_notes(text)
        if medical:
            logger.info("Medical-framing note for %s: %s (published as is)",
                        content_type, ", ".join(medical[:4]))
        if premium:
            tag = get_premium_rubric_tag(content_type)
            if tag and tag.split()[-1] not in text.split("\n", 1)[0].strip().lower():
                text = f"{tag}\n\n{text}"
        else:
            text = _add_rubric_tag(text, content_type)
        logger.info("Post ready [%s] via %s%s (%d words)",
                    content_type, model, f" [{note}]" if note else "", count_words(text))
        return content_type, text

    for model in models:
        for attempt in range(MAX_GENERATION_RETRIES + 1):
            logger.info("Trying model %s for %s %s, topic: %s (attempt %d)",
                        model, kind, content_type, topic[:40], attempt + 1)
            result = await attempt_generation(model)
            if not result:
                logger.info("Failed with %s (API error), trying next model", model)
                break  # API error — move to next model

            if not _is_complete(result, min_words):
                logger.warning("Incomplete text from %s (attempt %d), retrying",
                               model, attempt + 1)
                continue

            hits = _banned_hits(result)
            if hits:
                # Cliches are the main "written by a bot" tell. Retry once to
                # clean them up, then publish anyway rather than post nothing.
                logger.warning("Cliché check: %s in text from %s (attempt %d)",
                               ", ".join(hits[:4]), model, attempt + 1)
                if attempt < MAX_GENERATION_RETRIES:
                    continue

            return finish(result, model)

        logger.info("All attempts exhausted for %s, trying next model", model)

    # Last resort: accept a partially truncated post rather than skip the day.
    logger.warning("All models produced imperfect text, falling back to trimmed result")
    for model in models:
        result = await attempt_generation(model)
        if result and count_words(result) >= min_words:
            return finish(result, model, note="trimmed")

    raise RuntimeError("All models failed to generate content")


async def generate_content(content_type: Optional[str] = None) -> Tuple[str, str]:
    """Generate a free-channel post. Returns (content_type, post_text).

    Uses the topic pool for explicit topic assignment (no repeats), tries
    the primary model first and then FALLBACK_MODELS, validates length and
    style, and retries when the output is truncated or full of cliches.
    Raises RuntimeError if all models fail.
    """
    if content_type is None:
        content_type = get_random_content_type()

    topic = get_next_topic(content_type)
    return await _generate_with_fallback(
        topic=topic,
        content_type=content_type,
        base_prompt=get_prompt(content_type),
        system_prompt=SYSTEM_PROMPT,
        min_words=get_min_words(content_type),
        max_tokens=1600,
    )


async def generate_for_slot(hour: int) -> Tuple[str, str]:
    """Generate content appropriate for the given hour (MSK).

    Morning (before 10): protocol rubrics get double weight, the rest of
    the rotation (habits, supplements, health news, brain trivia) stays possible.
    Day/Evening: weighted random rotation.
    """
    content_type = get_content_type_for_slot(hour)
    return await generate_content(content_type)


def add_cta(text: str) -> str:
    """Append CTA link to spectrmind.ru."""
    return text + CTA_TEXT


async def generate_premium_content(content_type: Optional[str] = None) -> Tuple[str, str]:
    """Generate a premium post. Returns (content_type, post_text).

    Uses the premium topic pool, premium prompts and higher token limits.
    """
    if content_type is None:
        content_type = get_premium_content_type()

    topic = get_next_premium_topic(content_type)
    return await _generate_with_fallback(
        topic=topic,
        content_type=content_type,
        base_prompt=get_premium_prompt(content_type),
        system_prompt=PREMIUM_SYSTEM_PROMPT,
        min_words=get_premium_min_words(),
        max_tokens=2500,
        premium=True,
    )


async def generate_for_premium_slot(hour: int) -> Tuple[str, str]:
    """Generate premium content for the given hour."""
    content_type = get_premium_content_type()
    return await generate_premium_content(content_type)


async def check_api_health() -> list:
    """Probe every configured model with a tiny request.

    Returns a list of (status, model, detail) tuples. Used by /diagnose so a
    dead proxy or a wrong model id can be found without reading server logs.
    """
    results = []
    candidates = [OPENROUTER_MODEL] + list(FALLBACK_MODELS)
    for model in candidates:
        try:
            text = await _call_openrouter(
                model, "Ответь одним словом: работает", max_tokens=20
            )
        except Exception as exc:  # noqa: BLE001 - report any transport failure
            results.append(("error", model, f"{type(exc).__name__}: {exc}"[:120]))
            continue
        if text:
            results.append(("ok", model, text.replace("\n", " ")[:60]))
        else:
            results.append(("fail", model, "нет ответа или ошибка API"))
    return results


async def _call_openrouter(model: str, user_prompt: str, system_prompt: str = None, max_tokens: int = 1600) -> Optional[str]:
    """Call OpenRouter API and return generated text or None on failure."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://spectrmind.ru",
        "X-Title": "SpectrMind Bot",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.8,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT, proxy=PROXY_URL or None) as client:
        resp = await client.post(OPENROUTER_URL, json=payload, headers=headers)

        if resp.status_code == 429:
            logger.warning("Rate-limited by %s", model)
            return None
        if resp.status_code >= 400:
            logger.error("OpenRouter %s returned %d: %s", model, resp.status_code, resp.text[:300])
            return None

        data = resp.json()
        choice = data["choices"][0]
        finish_reason = choice.get("finish_reason", "unknown")
        logger.info("Model %s finish_reason: %s", model, finish_reason)

        # If truncated by token limit, treat as failure to trigger retry
        if finish_reason == "length":
            logger.warning("Output truncated by token limit for %s", model)
            return None

        raw = choice["message"]["content"].strip()
        return _clean_text(raw)

