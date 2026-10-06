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
    print("Значения из .env (то, что реально уйдёт в кнопки):\n")
    show("BOT_USERNAME", config.BOT_USERNAME, "spectrnewsbot")
    show("BOT_LINK", config.BOT_LINK, "t.me/spectrnewsbot")
    show("CHANNEL_LINK", config.CHANNEL_LINK, "t.me/")
    show("SHOW_CHANNEL_BUTTON", str(config.SHOW_CHANNEL_BUTTON))
    show("CTA_EVERY_N_POSTS", str(config.CTA_EVERY_N_POSTS))
    show("SHOW_DIRECT_PAY_BUTTONS", str(config.SHOW_DIRECT_PAY_BUTTONS))
    show("NEUROGUIDE_LINK", config.NEUROGUIDE_LINK)
    show("PAID_CHANNEL_LINK", config.PAID_CHANNEL_LINK)

    print("\nКнопки, которые появятся под CTA-постом:")
    try:
        from scheduler import build_keyboard
        keyboard = build_keyboard(with_pay_buttons=True)
        if keyboard is None:
            print("  (кнопок нет)")
        else:
            for row in keyboard.inline_keyboard:
                for button in row:
                    print(f"  [{button.text}] -> {button.url}")
    except Exception as exc:  # noqa: BLE001
        print(f"  не удалось построить клавиатуру: {type(exc).__name__}: {exc}")
        return 1

    print("\nПроверьте глазами: кнопка с протоколом должна вести на нужный бот.")
    print("Любая ссылка вида 'SpectrMindBot' вместо вашего бота — ошибка в .env,")
    print("потому что .env перебивает значения по умолчанию из config.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
