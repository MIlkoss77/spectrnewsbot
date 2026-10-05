"""Quick diagnostic: check which configured OpenRouter models actually respond."""
import asyncio

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_URL, FALLBACK_MODELS, PROXY_URL

CANDIDATES = [OPENROUTER_MODEL] + list(FALLBACK_MODELS)


async def probe(model: str) -> None:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://spectrmind.ru",
        "X-Title": "SpectrMind Bot",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Ответь одним словом: работает"}],
        "max_tokens": 20,
        "temperature": 0.0,
    }
    try:
        async with httpx.AsyncClient(timeout=45, proxy=PROXY_URL or None) as client:
            resp = await client.post(OPENROUTER_URL, json=payload, headers=headers)
        if resp.status_code >= 400:
            print(f"[FAIL {resp.status_code}] {model}: {resp.text[:200]}")
            return
        data = resp.json()
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        print(f"[OK] {model}: {text.strip()[:60]!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {model}: {type(exc).__name__}: {exc}")


async def main() -> None:
    print(f"Key present: {bool(OPENROUTER_API_KEY)} | proxy: {PROXY_URL or 'none'}")
    for model in CANDIDATES:
        await probe(model)


if __name__ == "__main__":
    asyncio.run(main())
