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

logger = logging.getLogger(__name__)

TIMEOUT = 60

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
        "max_tokens": 800,
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
        raw = data["choices"][0]["message"]["content"].strip()
        return _clean_text(raw)


async def generate_content(content_type: Optional[str] = None) -> Tuple[str, str]:
    """Generate a post. Returns (content_type, post_text).

    Tries the primary model first, then falls back through FALLBACK_MODELS.
    Raises RuntimeError if all models fail.
    """
    if content_type is None:
        content_type = get_random_content_type()

    prompt = get_prompt(content_type)
    models = [OPENROUTER_MODEL] + FALLBACK_MODELS

    for model in models:
        logger.info("Trying model %s for type %s", model, content_type)
        result = await _call_openrouter(model, prompt)
        if result:
            logger.info("Success with %s", model)
            result = _add_rubric_tag(result, content_type)
            return content_type, result
        logger.info("Failed with %s, trying next", model)

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
