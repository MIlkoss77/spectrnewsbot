"""Проверить платёжные ссылки и ссылки под постом так, как их видит читатель.

Робокасса отвечает своей страницей-заглушкой на битый или несуществующий
счёт, и это выглядит как «500» у пользователя. Скрипт делает реальный запрос
и показывает, что именно вернулось.

    python3 tools_check_payments.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx

import config

# Признаки страницы-заглушки Robokassa вместо формы оплаты.
ERROR_MARKERS = (
    "Merchant/Error",
    "incomprehensible situation",
    "Page Not Found",
    "statusCode=500",
    "statusCode=404",
)

TIMEOUT = 30


def describe_url(name: str, url: str) -> None:
    """Показать ссылку целиком, чтобы были видны лишние символы."""
    if not url:
        print(f"  {name}: НЕ ЗАДАНА в .env — соответствующая кнопка не появится")
        return
    stripped = url.strip()
    notes = []
    if url != stripped:
        notes.append("ПО КРАЯМ ПРОБЕЛЫ — Telegram такую ссылку не откроет")
    if any(ord(ch) < 33 or ord(ch) == 160 for ch in url):
        notes.append("ЕСТЬ УПРАВЛЯЮЩИЕ СИМВОЛЫ")
    if not url.startswith("https://"):
        notes.append("НЕ HTTPS")
    suffix = f"  <-- {', '.join(notes)}" if notes else ""
    print(f"  {name} ({len(url)} симв.): {url}{suffix}")


async def probe(name: str, url: str) -> None:
    if not url or not url.startswith("http"):
        return
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as exc:  # noqa: BLE001
        print(f"  {name}: сетевая ошибка {type(exc).__name__}: {exc}")
        return

    body = resp.text[:4000]
    hit = next((marker for marker in ERROR_MARKERS if marker in body), "")
    final = str(resp.url)

    print(f"  {name}: HTTP {resp.status_code}"
          + (f", итоговый адрес {final}" if final.rstrip('/') != url.rstrip('/') else ""))

    if hit:
        print(f"    ❌ Robokassa вернула страницу-заглушку ({hit!r}).")
        print("       Это значит: счёт по этой ссылке недействителен, удалён или истёк.")
        print("       Возьмите актуальную ссылку в личном кабинете Robokassa.")
    elif resp.status_code >= 400:
        print(f"    ❌ Код {resp.status_code}. Ссылка не работает.")
    else:
        lower = body.lower()
        if "robokassa" in lower and ("оплат" in lower or "payment" in lower or "сумм" in lower):
            print("    ✅ Похоже на страницу оплаты.")
        else:
            print("    ⚠️ Ответ получен, но на форму оплаты не похоже — проверьте глазами.")


async def probe_static_form() -> None:
    """Проверить, жив ли документированный способ оплаты по подписанной ссылке.

    Документация Robokassa описывает оплату через /Merchant/Index.aspx с
    параметрами MerchantLogin, OutSum, InvId и SignatureValue. В отличие от
    счёта из личного кабинета, такая ссылка формируется на лету и не истекает.
    Здесь используется демо-магазин из документации, чтобы понять, отвечает ли
    этот адрес формой оплаты.
    """
    import hashlib

    login, password1 = "demo", "password_1"
    out_sum, inv_id = "990.00", "1"
    signature = hashlib.md5(f"{login}:{out_sum}:{inv_id}:{password1}".encode()).hexdigest()
    url = (
        "https://auth.robokassa.ru/Merchant/Index.aspx"
        f"?MerchantLogin={login}&OutSum={out_sum}&InvId={inv_id}"
        f"&SignatureValue={signature}&Culture=ru"
    )
    print("  демо-ссылка /Merchant/Index.aspx (по документации):")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as exc:  # noqa: BLE001
        print(f"    сетевая ошибка {type(exc).__name__}: {exc}")
        return

    body = resp.text[:4000].lower()
    hit = next((m for m in ERROR_MARKERS if m.lower() in body), "")
    if hit:
        print(f"    HTTP {resp.status_code}, заглушка ({hit!r}) — магазин demo недоступен")
    elif "signature" in body or "подпис" in body:
        print(f"    HTTP {resp.status_code}: страница оплаты ответила (подпись demo отклонена, это норма)")
    else:
        print(f"    HTTP {resp.status_code}: ответ получен, на форму оплаты "
              f"{'похоже' if 'оплат' in body or 'payment' in body else 'не похоже'}")
    print(f"    итоговый адрес: {resp.url}")


async def main() -> int:
    print("Ссылки из .env:\n")
    describe_url("PAID_CHANNEL_LINK", config.PAID_CHANNEL_LINK)
    describe_url("NEUROGUIDE_LINK", config.NEUROGUIDE_LINK)
    describe_url("CHANNEL_LINK", config.CHANNEL_LINK)
    describe_url("BOT_LINK", config.BOT_LINK)

    print("\nРеальные запросы по ссылкам из .env:\n")
    for name in ("PAID_CHANNEL_LINK", "NEUROGUIDE_LINK"):
        await probe(name, getattr(config, name))

    print("\nПроверка альтернативного формата:\n")
    await probe_static_form()

    print("\nЧто это значит:")
    print("  • если ссылка из .env ведёт на /Merchant/Error — счёт недействителен,")
    print("    истёк или удалён. Возьмите актуальную ссылку в личном кабинете")
    print("    Robokassa либо формируйте ссылку на лету (см. README).")
    print("  • ссылка вида /Merchant/Index/{guid} — это счёт из личного кабинета,")
    print("    у него есть срок жизни, поэтому для постоянных кнопок он не годится.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
