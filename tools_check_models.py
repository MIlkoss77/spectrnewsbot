"""Diagnostic tool for the OpenRouter models the bot uses.

Without arguments: probes the primary model and every fallback, printing
whether each one answers.

    python3 tools_check_models.py

With --free: fetches the live OpenRouter catalogue and lists currently
available free models, which is the reliable way to pick fallbacks instead
of guessing model ids.

    python3 tools_check_models.py --free
"""
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


async def list_free() -> None:
    """List free models from the live catalogue, flagging known candidates."""
    try:
        async with httpx.AsyncClient(timeout=45, proxy=PROXY_URL or None) as client:
            resp = await client.get(MODELS_URL, headers=headers())
        resp.raise_for_status()
        data = resp.json().get("data", [])
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] не удалось получить каталог: {type(exc).__name__}: {exc}")
        return

    free = []
    for item in data:
        pricing = item.get("pricing") or {}
        try:
            is_free = float(pricing.get("prompt", 1)) == 0 and float(pricing.get("completion", 1)) == 0
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


async def main() -> None:
    if not OPENROUTER_API_KEY:
        print("OPENROUTER_API_KEY не задан в .env — проверять нечего.")
        return

    if "--free" in sys.argv:
        await list_free()
        return

    print(f"Key present: {bool(OPENROUTER_API_KEY)} | proxy: {PROXY_URL or 'none'}")
    print(f"Основная модель из .env: {OPENROUTER_MODEL}\n")
    for model in [OPENROUTER_MODEL] + list(FALLBACK_MODELS):
        await probe(model)


if __name__ == "__main__":
    asyncio.run(main())
