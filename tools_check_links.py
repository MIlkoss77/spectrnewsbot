"""Show the exact links the bot puts under posts, and flag wrong ones.

A button pointing at the wrong bot silently sends readers to someone else's
account, so the configured values are printed literally.

    python3 tools_check_links.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config  # noqa: E402


def show(name: str, value: str, expected: str = "") -> None:
    mark = ""
    if not value:
        mark = "  <-- ПУСТО"
    elif expected and expected not in value:
        mark = f"  <-- ожидалось вхождение {expected!r}"
    print(f"  {name} = {value or '(не задано)'}{mark}")


def main() -> int:
    print("Готовность Robokassa:")
    login = config.ROBOKASSA_MERCHANT_LOGIN
    password = config.ROBOKASSA_PASSWORD_1
    print(f"  ROBOKASSA_MERCHANT_LOGIN = {login or '(не задан)'}")
    print(f"  ROBOKASSA_PASSWORD_1     = "
          f"{'задан, ' + str(len(password)) + ' симв.' if password else '(не задан)'}")
    print(f"  подпись ссылок работает: {config.robokassa_ready()}")
    if not config.robokassa_ready():
        print("  ^^ Если тут False, кнопки оплаты ведут на старые ссылки из кабинета,")
        print("     а они просрочены и дают 500. Проверьте имена переменных в .env:")
        print("     ROBOKASSA_MERCHANT_LOGIN и ROBOKASSA_PASSWORD_1")

    print("\nЧто реально уйдёт в кнопки (с подписью, если она настроена):")
    try:
        from scheduler import build_keyboard
        from config import build_lead_magnet_keyboard

        print("  Кнопки под бесплатным гайдом (/start):")
        guide = build_lead_magnet_keyboard(user_id=555)
        if guide is None:
            print("    (кнопок нет)")
        else:
            for row in guide.inline_keyboard:
                print(f"    [{row[0].text}] -> {row[0].url}")

        print("\n  Кнопки под CTA-постом в канале:")
        post = build_keyboard(with_pay_buttons=True)
        if post is None:
            print("    (кнопок нет)")
        else:
            for row in post.inline_keyboard:
                print(f"    [{row[0].text}] -> {row[0].url}")
    except Exception as exc:  # noqa: BLE001
        print(f"  не удалось построить клавиатуры: {type(exc).__name__}: {exc}")
        return 1

    print("\nЗначения из .env (как есть):\n")
    show("BOT_USERNAME", config.BOT_USERNAME, "spectrnewsbot")
    show("BOT_LINK", config.BOT_LINK, "t.me/spectrnewsbot")
    show("CHANNEL_LINK", config.CHANNEL_LINK, "t.me/")
    show("SHOW_CHANNEL_BUTTON", str(config.SHOW_CHANNEL_BUTTON))
    show("CTA_EVERY_N_POSTS", str(config.CTA_EVERY_N_POSTS))
    show("SHOW_DIRECT_PAY_BUTTONS", str(config.SHOW_DIRECT_PAY_BUTTONS))
    show("NEUROGUIDE_LINK (запасная)", config.NEUROGUIDE_LINK)
    show("PAID_CHANNEL_LINK (запасная)", config.PAID_CHANNEL_LINK)

    print("\nЗапасные ссылки используются только если подпись не настроена.")
    print("Ссылка вида /Merchant/Index/{guid} со временем истекает и даёт 500.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
