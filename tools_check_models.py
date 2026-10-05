"""Diagnostic tool for the OpenRouter models the bot uses.

Without arguments: probes the primary model and every fallback, printing
whether each one answers.

    python3 tools_check_models.py

With --free: fetches the live OpenRouter catalogue and lists currently
available free models, which is the reliable way to pick fallbacks instead
of guessing model ids.

    python3 tools_check_models.py --free

With --pricing: prints price per million tokens for the given models, taken
from the live catalogue, so a model can be chosen on real numbers.

    python3 tools_check_models.py --pricing openai/gpt-4o-mini,anthropic/claude-3.5-haiku
"""
from __future__ import annotations

import asyncio
import sys

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_URL, FALLBACK_MODELS, PROXY_URL

MODELS_URL = OPENROUTER_URL.replace("/chat/completions", "/models")

# Candidate fallbacks worth trying once the catalogue is known. Only ids that
# are actually present in the live catalogue are reported.
FALLBACK_CANDIDATES = [
    "google/gemma-3-27b-it:free",
    "google/gemma-3-12b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "qwen/qwen3-235b-a22b:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "deepseek/deepseek-r1:free",
    "mistralai/mistral-small-3.2-24b-instruct:free",
    "openai/gpt-oss-20b:free",
    "z-ai/glm-4.5-air:free",
]


def headers() -> dict:
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://spectrmind.ru",
        "X-Title": "SpectrMind Bot",
    }


async def probe(model: str) -> None:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Ответь одним словом: работает"}],
        "max_tokens": 20,
        "temperature": 0.0,
    }
    try:
        async with httpx.AsyncClient(timeout=45, proxy=PROXY_URL or None) as client:
            resp = await client.post(OPENROUTER_URL, json=payload, headers=headers())
        if resp.status_code >= 400:
            print(f"[FAIL {resp.status_code}] {model}: {resp.text[:200]}")
            return
        data = resp.json()
        if data.get("error"):
            message = data["error"].get("message") if isinstance(data["error"], dict) else data["error"]
            print(f"[FAIL api] {model}: {str(message)[:160]}")
            return
        choices = data.get("choices") or []
        content = (choices[0].get("message") or {}).get("content") if choices else None
        if not isinstance(content, str) or not content.strip():
            print(f"[FAIL empty] {model}: ответ без текста (finish_reason="
                  f"{choices[0].get('finish_reason') if choices else 'нет choices'})")
            return
        print(f"[OK] {model}: {content.strip()[:60]!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {model}: {type(exc).__name__}: {exc}")


async def fetch_catalog() -> list:
    """Fetch the live OpenRouter model catalogue."""
    async with httpx.AsyncClient(timeout=45, proxy=PROXY_URL or None) as client:
        resp = await client.get(MODELS_URL, headers=headers())
    resp.raise_for_status()
    return resp.json().get("data", [])


def _price_per_million(pricing: dict, key: str) -> float | None:
    """Convert OpenRouter per-token pricing to USD per million tokens."""
    try:
        return float(pricing.get(key, 0)) * 1_000_000
    except (TypeError, ValueError):
        return None


def _fmt_price(value: float | None) -> str:
    if value is None:
        return "?"
    if value == 0:
        return "бесплатно"
    return f"${value:.3f}"


async def list_free() -> None:
    """List free models from the live catalogue, flagging known candidates."""
    try:
        data = await fetch_catalog()
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] не удалось получить каталог: {type(exc).__name__}: {exc}")
        return

    free = []
    for item in data:
        pricing = item.get("pricing") or {}
        try:
            is_free = (float(pricing.get("prompt", 1)) == 0
                       and float(pricing.get("completion", 1)) == 0)
        except (TypeError, ValueError):
            is_free = False
        if is_free or item.get("id", "").endswith(":free"):
            free.append(item.get("id", ""))

    free.sort()
    print(f"Бесплатных моделей в каталоге: {len(free)}\n")

    available = set(free)
    print("Из моих кандидатов доступны:")
    for candidate in FALLBACK_CANDIDATES:
        mark = "OK " if candidate in available else "нет"
        print(f"  [{mark}] {candidate}")

    print("\nВсе бесплатные модели (первые 60):")
    for model_id in free[:60]:
        print(f"  {model_id}")


async def show_pricing(model_ids: list) -> None:
    """Print context window and price per million tokens for given models.

    Prices come from the live catalogue, so the choice is based on real
    numbers instead of remembered ones.
    """
    try:
        data = await fetch_catalog()
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] не удалось получить каталог: {type(exc).__name__}: {exc}")
        return

    by_id = {item.get("id", ""): item for item in data}
    print(f"{'модель':<46} {'вход':>12} {'выход':>12} {'контекст':>10}")
    print("-" * 84)
    for model_id in model_ids:
        item = by_id.get(model_id)
        if not item:
            print(f"{model_id:<46} {'НЕТ В КАТАЛОГЕ':>12}")
            continue
        pricing = item.get("pricing") or {}
        context = item.get("context_length") or item.get("top_provider", {}).get("context_length")
        print(f"{model_id:<46} {_fmt_price(_price_per_million(pricing, 'prompt')):>12} "
              f"{_fmt_price(_price_per_million(pricing, 'completion')):>12} "
              f"{str(context or '?'):>10}")

    print("\nЦены — за 1 миллион токенов, из живого каталога OpenRouter.")
    print("Пост на 350 слов ≈ 1.5 тыс. токенов вывода: считайте по колонке «выход».")


async def main() -> None:
    if not OPENROUTER_API_KEY:
        print("OPENROUTER_API_KEY не задан в .env — проверять нечего.")
        return

    if "--free" in sys.argv:
        await list_free()
        return

    if "--pricing" in sys.argv:
        index = sys.argv.index("--pricing")
        raw = sys.argv[index + 1] if len(sys.argv) > index + 1 else ""
        model_ids = [m.strip() for m in raw.split(",") if m.strip()]
        if not model_ids:
            print("Укажите модели: --pricing model/a,model/b")
            return
        await show_pricing(model_ids)
        return

    print(f"Key present: {bool(OPENROUTER_API_KEY)} | proxy: {PROXY_URL or 'none'}")
    print(f"Основная модель из .env: {OPENROUTER_MODEL}\n")
    for model in [OPENROUTER_MODEL] + list(FALLBACK_MODELS):
        await probe(model)


if __name__ == "__main__":
    asyncio.run(main())
