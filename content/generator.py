import logging
import random
import re
from typing import Optional, Tuple

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_URL, FALLBACK_MODELS, PROXY_URL
from content.prompts import (
    SYSTEM_PROMPT, get_prompt, get_random_content_type,
    get_content_type_for_slot, get_rubric_tag, CONTENT_TYPES,
)
from content.topic_pool import get_next_topic

logger = logging.getLogger(__name__)

TIMEOUT = 60
MAX_GENERATION_RETRIES = 2

CTA_TEXT = (
    "\n\n---\n"
    "\U0001f4a1 Полный гайд по нейро-оптимизации "
    "\u2192 spectrmind.ru"
)


def _clean_text(text: str) -> str:
    """Remove markdown artifacts from generated text."""
    text = text.replace("**", "")
    text = text.replace("*", "")
    text = text.replace("__", "")
    text = text.replace("_", "")
    text = text.replace("```", "")
    text = text.replace("`", "")
    text = text.replace("~~", "")
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


def _is_complete(text: str) -> bool:
    """Check if generated text looks complete (not truncated)."""
    if not text:
        return False

    # Must have at least 100 words for a viable post
    word_count = len(text.split())
    if word_count < 100:
        logger.warning("Text too short: %d words", word_count)
        return False

    # Check if text ends with hashtags or proper punctuation
    stripped = text.rstrip()
    last_line = stripped.split("\n")[-1].strip()

    # Ends with hashtags (common pattern for TG posts)
    if re.search(r"#\S+$", last_line):
        return True

    # Ends with proper sentence-ending punctuation
    if stripped.endswith((".", "!", "?", ":", ")")):
        return True

    # Last line is a single word without punctuation — likely cut off
    if len(last_line.split()) <= 2 and not last_line.endswith((".", "!", "?")):
        logger.warning("Text appears truncated, last line: %r", last_line[:60])
        return False

    logger.warning("Text completeness uncertain, last 30 chars: %r", stripped[-30:])
    return False


def _trim_incomplete_tail(text: str) -> str:
    """Trim incomplete trailing content, keeping only complete paragraphs."""
    if not text:
        return text

    # Split into paragraphs (double newline separated)
    paragraphs = text.split("\n\n")

    # Find the last paragraph that ends with proper punctuation
    last_complete = len(paragraphs)
    for i in range(len(paragraphs) - 1, -1, -1):
        para = paragraphs[i].strip()
        if para and (para.endswith((".", "!", "?")) or re.search(r"#\S+$", para)):
            last_complete = i + 1
            break

    trimmed = "\n\n".join(paragraphs[:last_complete])

    # If we trimmed too aggressively (less than 100 words), return original
    if len(trimmed.split()) < 100:
        logger.warning("Trimming too aggressive (%d words), keeping original", len(trimmed.split()))
        return text

    logger.info("Trimmed from %d to %d words", len(text.split()), len(trimmed.split()))
    return trimmed


def _add_rubric_tag(text: str, content_type: str) -> str:
    """Prepend rubric tag to the post if not already present."""
    tag = get_rubric_tag(content_type)
    if not tag:
        return text
    # Check if tag is already in the first line
    first_line = text.split("\n", 1)[0].strip().upper()
    if tag.split()[-1] in first_line:
        return text
    return f"{tag}\n\n{text}"


async def _call_openrouter(model: str, user_prompt: str) -> Optional[str]:
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
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 1600,
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


async def generate_content(content_type: Optional[str] = None) -> Tuple[str, str]:
    """Generate a post. Returns (content_type, post_text).

    Uses topic pool for explicit topic assignment (no repeats).
    Tries the primary model first, then falls back through FALLBACK_MODELS.
    Validates completeness and retries if truncated.
    Raises RuntimeError if all models fail.
    """
    if content_type is None:
        content_type = get_random_content_type()

    # Get specific topic from pool (round-robin, no repeats)
    topic = get_next_topic(content_type)

    base_prompt = get_prompt(content_type)
    prompt = f"ТЕМА ПОСТА: {topic}\n\n{base_prompt}\n\nПиши СТРОГО про указанную тему выше."

    models = [OPENROUTER_MODEL] + FALLBACK_MODELS

    for model in models:
        for attempt in range(MAX_GENERATION_RETRIES + 1):
            logger.info("Trying model %s for type %s, topic: %s (attempt %d)",
                        model, content_type, topic[:40], attempt + 1)
            result = await _call_openrouter(model, prompt)
            if not result:
                logger.info("Failed with %s (API error), trying next model", model)
                break  # API error — move to next model

            if _is_complete(result):
                logger.info("Success with %s (complete)", model)
                result = _add_rubric_tag(result, content_type)
                return content_type, result

            # Text incomplete — retry same model
            logger.warning("Incomplete text from %s (attempt %d), retrying",
                           model, attempt + 1)

        # All attempts with this model failed, try next
        logger.info("All attempts exhausted for %s, trying next model", model)

    # Last resort: take the best result we got and trim incomplete tail
    logger.warning("All models produced incomplete text, using trimmed result")
    for model in models:
        result = await _call_openrouter(model, prompt)
        if result:
            result = _trim_incomplete_tail(result)
            if len(result.split()) >= 100:
                result = _add_rubric_tag(result, content_type)
                return content_type, result

    raise RuntimeError("All models failed to generate content")


async def generate_for_slot(hour: int) -> Tuple[str, str]:
    """Generate content appropriate for the given hour (MSK).

    Morning (before 10): protocol types only.
    Day/Evening: weighted random rotation.
    """
    content_type = get_content_type_for_slot(hour)
    return await generate_content(content_type)


def add_cta(text: str) -> str:
    """Append CTA link to spectrmind.ru."""
    return text + CTA_TEXT
