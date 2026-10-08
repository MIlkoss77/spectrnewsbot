"""Сравнить модели на одной и той же теме и показать реальную стоимость.

Прогоняет один и тот же пост через несколько моделей, чтобы выбрать лучший
русский язык глазами, а не по описаниям. Цена считается по фактическому
расходу токенов из ответа OpenRouter, а не по прикидке.

    python3 tools_compare_models.py --topic "Магний и сон: что показали исследования"
    python3 tools_compare_models.py --rubric myth_buster
    python3 tools_compare_models.py --models openai/gpt-4o-mini,deepseek/deepseek-chat

Черновики складываются в model_comparison/ — файл на модель плюс index.md.
Темы из ротации не расходуются: берётся тема для примера, состояние не меняется.
"""
import argparse
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_URL, PROXY_URL
from content.generator import (
    _banned_hits,
    _build_prompt,
    _clean_text,
    _ensure_hashtags,
    _is_complete,
    count_words,
)
from content.prompts import SYSTEM_PROMPT, get_hashtags, get_min_words, get_prompt
from content.topic_pool import TOPIC_POOL

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_comparison")

# Цена за миллион токенов; заполняется из каталога перед запуском.
PRICES = {}


async def fetch_prices() -> None:
    """Взять актуальные цены из каталога OpenRouter."""
    models_url = OPENROUTER_URL.replace("/chat/completions", "/models")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://spectrmind.ru",
        "X-Title": "SpectrMind Bot",
    }
    try:
        async with httpx.AsyncClient(timeout=45, proxy=PROXY_URL or None) as client:
            resp = await client.get(models_url, headers=headers)
        resp.raise_for_status()
        for item in resp.json().get("data", []):
            pricing = item.get("pricing") or {}
            try:
                PRICES[item.get("id", "")] = (
                    float(pricing.get("prompt", 0)) * 1_000_000,
                    float(pricing.get("completion", 0)) * 1_000_000,
                )
            except (TypeError, ValueError):
                continue
    except Exception as exc:  # noqa: BLE001
        print(f"  цены получить не удалось ({type(exc).__name__}), будут нули")


async def generate_raw(model: str, prompt: str, max_tokens: int = 1600):
    """Один вызов OpenRouter с возвратом текста и расхода токенов."""
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
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.8,
        "max_tokens": max_tokens,
    }
    started = time.monotonic()
    async with httpx.AsyncClient(timeout=180, proxy=PROXY_URL or None) as client:
        resp = await client.post(OPENROUTER_URL, json=payload, headers=headers)
    elapsed = time.monotonic() - started

    if resp.status_code >= 400:
        return None, None, elapsed, f"HTTP {resp.status_code}: {resp.text[:160]}"

    data = resp.json()
    if data.get("error"):
        message = data["error"].get("message") if isinstance(data["error"], dict) else data["error"]
        return None, None, elapsed, f"API: {str(message)[:160]}"

    choices = data.get("choices") or []
    content = (choices[0].get("message") or {}).get("content") if choices else None
    if not isinstance(content, str) or not content.strip():
        return None, None, elapsed, "пустой ответ"

    return _clean_text(content), data.get("usage") or {}, elapsed, ""


def estimate_cost(usage: dict) -> float:
    """Стоимость одного поста в долларах по фактическому расходу."""
    prompt_price, completion_price = PRICES.get(CURRENT_MODEL, (0.0, 0.0))
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    return (prompt_tokens * prompt_price + completion_tokens * completion_price) / 1_000_000


CURRENT_MODEL = ""


async def main() -> int:
    global CURRENT_MODEL

    parser = argparse.ArgumentParser(description="Сравнить модели на одной теме")
    parser.add_argument("--topic", help="Тема поста; по умолчанию берётся из пула рубрики")
    parser.add_argument("--rubric", default="supplement_recap", help="Рубрика для темы по умолчанию")
    parser.add_argument("--models", help="Список id через запятую; по умолчанию основная + 2 кандидата")
    args = parser.parse_args()

    if not OPENROUTER_API_KEY:
        print("OPENROUTER_API_KEY не задан в .env")
        return 2

    models = [m.strip() for m in args.models.split(",")] if args.models else [
        OPENROUTER_MODEL,
        "deepseek/deepseek-chat",
        "google/gemini-2.5-flash",
    ]
    models = [m for m in models if m]

    topic = args.topic
    if not topic:
        pool = TOPIC_POOL.get(args.rubric) or TOPIC_POOL["micro_protocol"]
        topic = pool[0]

    rubric = args.rubric
    prompt = _build_prompt(topic, get_prompt(rubric), get_hashtags(rubric))

    print(f"Тема: {topic}")
    print(f"Рубрика: {rubric}")
    print(f"Прокси: {PROXY_URL or 'нет'}")
    print("Беру цены из каталога...", flush=True)
    await fetch_prices()

    os.makedirs(OUT_DIR, exist_ok=True)
    rows = []

    for model in models:
        CURRENT_MODEL = model
        print(f"\n--- {model} ---", flush=True)
        text, usage, elapsed, error = await generate_raw(model, prompt)

        if error:
            print(f"  ошибка: {error}")
            rows.append((model, 0, 0, elapsed, 0.0, error))
            continue

        final = _ensure_hashtags(text, rubric)
        words = count_words(final)
        cost = estimate_cost(usage)
        complete = _is_complete(text, get_min_words(rubric))
        cliches = _banned_hits(text)

        safe_name = model.replace("/", "_").replace(":", "_")
        path = os.path.join(OUT_DIR, f"{safe_name}.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(f"# {model}\n\nТема: {topic}\nРубрика: {rubric}\n\n---\n\n{final}\n")

        print(f"  слов: {words} | {elapsed:.0f} c | "
              f"токены: {usage.get('prompt_tokens', '?')}→{usage.get('completion_tokens', '?')} | "
              f"${cost:.4f} за пост")
        print(f"  проходит проверку длины: {complete} | штампов: {len(cliches)}")
        if cliches:
            print(f"  штампы: {', '.join(cliches[:4])}")
        print(f"  файл: model_comparison/{safe_name}.md")

        rows.append((model, words, usage.get("completion_tokens", 0), elapsed, cost, ""))

    index = os.path.join(OUT_DIR, "index.md")
    with open(index, "w", encoding="utf-8") as handle:
        handle.write(f"# Сравнение моделей\n\nТема: {topic}\nРубрика: {rubric}\n\n")
        handle.write("| модель | слов | выход, токенов | сек | $ за пост | $ за 30 постов |\n")
        handle.write("|---|---|---|---|---|---|\n")
        for model, words, tokens, elapsed, cost, error in rows:
            if error:
                handle.write(f"| {model} | — | — | {elapsed:.0f} | — | ошибка: {error} |\n")
            else:
                handle.write(f"| {model} | {words} | {tokens} | {elapsed:.0f} | "
                             f"{cost:.4f} | {cost * 30:.2f} |\n")

    print("\nСводка: model_comparison/index.md")
    print("Откройте файлы моделей и сравните язык — цена тут не главное.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
