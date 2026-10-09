"""Сформировать и проверить ссылку на оплату Robokassa.

Ссылки вида /Merchant/Index/{guid} — это разовые счета из личного кабинета,
они истекают, и кнопка в канале со временем ломается. Правильный способ —
формировать ссылку на лету с подписью SignatureValue: такой адрес не истекает.

Инструмент ничего не отправляет в канал, только печатает ссылку и проверяет,
что Robokassa не отвечает страницей-заглушкой.

    python3 tools_robokassa_link.py --sum 1990 --inv-id 1001

Логин и пароль берутся из .env, имена совпадают с сайтом
(ROBOKASSA_MERCHANT_LOGIN, ROBOKASSA_PASSWORD_1), поэтому вводить их в
терминале не нужно. Если в .env их нет, пароль будет запрошен молча.
"""
import argparse
import getpass
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx

from dotenv import load_dotenv

ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(ENV_FILE)

PAY_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"
ERROR_MARKERS = ("Merchant/Error", "incomprehensible situation", "Page Not Found")

# Имена, под которыми логин и пароль могут лежать в .env. Первый вариант
# совпадает с сайтом, второй — с прежним именем в этом инструменте.
LOGIN_KEYS = ("ROBOKASSA_MERCHANT_LOGIN", "ROBOKASSA_LOGIN")
PASSWORD_KEYS = ("ROBOKASSA_PASSWORD_1", "ROBOKASSA_PASSWORD1")


def read_setting(keys, prompt: str = "") -> str:
    """Взять значение из окружения по любому из имён, иначе спросить молча."""
    for key in keys:
        value = os.getenv(key, "").strip()
        if value:
            return value
    if not prompt:
        return ""
    try:
        return getpass.getpass(prompt).strip()
    except Exception:
        return ""


def build_signature(login: str, out_sum: str, inv_id: str, password1: str,
                    recurring: bool = False) -> str:
    """MD5-подпись по документации Robokassa.

    Строка: MerchantLogin:OutSum:InvId:<модификаторы>:Пароль#1
    """
    base = f"{login}:{out_sum}:{inv_id}"
    if recurring:
        base += ":Recurring=true"
    base += f":{password1}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()


def build_link(login: str, out_sum: str, inv_id: str, password1: str,
               description: str = "", recurring: bool = False) -> str:
    """Собрать ссылку на оплату."""
    signature = build_signature(login, out_sum, inv_id, password1, recurring)
    params = [
        ("MerchantLogin", login),
        ("OutSum", out_sum),
        ("InvId", inv_id),
        ("SignatureValue", signature),
        ("Culture", "ru"),
        ("Encoding", "utf-8"),
    ]
    if description:
        params.append(("Description", description))
    if recurring:
        params.append(("Recurring", "true"))
    query = "&".join(f"{key}={value}" for key, value in params)
    return f"{PAY_URL}?{query}"


async def probe(url: str) -> str:
    """Проверить ссылку запросом: заглушка или форма оплаты."""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as exc:  # noqa: BLE001
        return f"сетевая ошибка {type(exc).__name__}: {exc}"

    body = resp.text[:5000]
    hit = next((marker for marker in ERROR_MARKERS if marker in body), "")
    if hit:
        return (f"❌ ЗАГЛУШКА Robokassa ({hit!r}) по адресу {resp.url}\n"
                f"   Причины: неверный MerchantLogin, неверный Пароль №1, "
                f"магазин не активирован (ошибка 25/26/29) или услуга не подключена.")
    if "SignatureValue" in body or "подпис" in body.lower():
        return f"⚠️ HTTP {resp.status_code}: страница оплаты ответила, но подпись не принята"
    return f"✅ HTTP {resp.status_code}: похоже на форму оплаты ({resp.url})"


def main() -> int:
    parser = argparse.ArgumentParser(description="Ссылка на оплату Robokassa")
    parser.add_argument("--login", help="MerchantLogin; по умолчанию из .env")
    parser.add_argument("--sum", required=True, help="Сумма, например 1990")
    parser.add_argument("--inv-id", default="1", help="Номер заказа (уникальный)")
    parser.add_argument("--description", default="", help="Название товара")
    parser.add_argument("--recurring", action="store_true",
                        help="Подписка: добавить Recurring=true (нужна услуга РП)")
    parser.add_argument("--no-probe", action="store_true", help="Не проверять запросом")
    args = parser.parse_args()

    login = (args.login or read_setting(LOGIN_KEYS)).strip()
    if not login:
        print("Не задан логин магазина.")
        print(f"Добавьте в .env: {LOGIN_KEYS[0]}=Spectrmind")
        return 2

    password1 = read_setting(PASSWORD_KEYS)
    if not password1:
        password1 = read_setting(PASSWORD_KEYS, "Пароль №1 из технических настроек: ")
    if not password1:
        print("Пароль №1 не найден.")
        print(f"Добавьте в .env: {PASSWORD_KEYS[0]}=<пароль из кабинета Robokassa>")
        print("Так значение не попадёт ни в историю команд, ни в список процессов.")
        return 2

    out_sum = f"{float(args.sum):.2f}"
    link = build_link(args.login, out_sum, args.inv_id, password1,
                      args.description, args.recurring)

    print(f"\nMerchantLogin: {args.login}")
    print(f"Сумма: {out_sum} ₽")
    print(f"InvId: {args.inv_id}")
    print(f"Режим: {'подписка (Recurring=true)' if args.recurring else 'разовый платёж'}")
    print(f"\nСсылка:\n{link}\n")

    if not args.no_probe:
        print("Проверка запросом:")
        print(" ", __import__("asyncio").run(probe(link)))

    if args.recurring:
        print("\nДля подписки услуга рекуррентных платежей должна быть подключена")
        print("к магазину, иначе Robokassa вернёт ошибку 34.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
