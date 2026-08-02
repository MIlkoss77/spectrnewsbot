import logging
import random
import re

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_URL, FALLBACK_MODELS, PROXY_URL
from content.prompts import SYSTEM_PROMPT, get_prompt, get_random_content_type

logger = logging.getLogger(__name__)

TIMEOUT = 60


def _clean_text(text: str) -> str:
    """Remove markdown artifacts (asterisks, backticks, etc.) from generated text."""
    text = text.replace("**", "")
    text = text.replace("*", "")
    text = text.replace("__", "")
    text = text.replace("_", "")
    text = text.replace("```", "")
    text = text.replace("`", "")
    text = text.replace("~~", "")
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.splitlines()]
    # Collapse multiple blank lines
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


async def _call_openrouter(model: str, user_prompt: str) -> str | None:
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


async def generate_content(content_type: str | None = None) -> tuple[str, str]:
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
            return content_type, result
        logger.info("Failed with %s, trying next", model)

    raise RuntimeError("All models failed to generate content")
