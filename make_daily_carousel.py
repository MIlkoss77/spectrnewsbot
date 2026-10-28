#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SPECTR MIND // Скрипт ежедневной генерации каруселей (Cyan Edition)
1. Выбирает тему из пула (советская нейробиология, Бехтерева, сосуды, мозг 35-45+).
2. Генерирует структуру 5 слайдов по нативной воронке продаж через LLM.
3. Рендерит 5 картинок высокого разрешения (1080x1350) в цвете Cyan.
4. Сохраняет готовый текст для поста в Instagram.
5. (Опционально) Отправляет альбом из 5 фото прямо в личку Telegram админу (--send-tg).

Использование:
  python make_daily_carousel.py
  python make_daily_carousel.py --topic "Почему Бехтерева запрещала кофе натощак"
  python make_daily_carousel.py --send-tg
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime
import httpx

from config import BOT_TOKEN, ADMIN_ID
from carousel_tool.carousel_ai import generate_carousel_deck, render_carousel_images


async def send_to_telegram(photo_paths: list, caption_text: str, topic_title: str) -> bool:
    """Отправляет альбом из 5 фото и текст поста админу в Telegram."""
    if not BOT_TOKEN or not ADMIN_ID:
        print("[TG] BOT_TOKEN или ADMIN_ID не настроены в .env — отправка пропущена.")
        return False

    url_media = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup"
    url_msg = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    import json
    media = []
    files = {}

    for idx, f_path in enumerate(photo_paths):
        field_name = f"photo_{idx}"
        files[field_name] = open(f_path, "rb")
        item = {
            "type": "photo",
            "media": f"attach://{field_name}",
        }
        if idx == 0:
            item["caption"] = f"⚡ <b>SPECTR MIND // {topic_title}</b>\nСлайды 1–{len(photo_paths)}"
            item["parse_mode"] = "HTML"
        media.append(item)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url_media,
                data={"chat_id": ADMIN_ID, "media": json.dumps(media)},
                files=files,
            )
            for f in files.values():
                f.close()

            if resp.status_code == 200:
                print(f"[TG] Альбом из {len(photo_paths)} слайдов успешно отправлен админу ({ADMIN_ID})!")
                # Отправляем текст поста
                post_msg = (
                    f"📋 <b>Текст для описания поста в Instagram (скопируй и выкладывай):</b>\n\n"
                    f"{caption_text}"
                )
                await client.post(
                    url_msg,
                    data={"chat_id": ADMIN_ID, "text": post_msg},
                )
                print("[TG] Текст поста отправлен!")
                return True
            else:
                print(f"[TG] Ошибка отправки: {resp.status_code} {resp.text}")
                return False
    except Exception as e:
        for f in files.values():
            try:
                f.close()
            except Exception:
                pass
        print(f"[TG] Исключение при отправке: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="SPECTR MIND Daily Carousel Generator")
    parser.add_argument("--topic", type=str, default=None, help="Пользовательская тема (по умолчанию из пула)")
    parser.add_argument("--output", type=str, default=None, help="Папка для сохранения слайдов")
    parser.add_argument("--send-tg", action="store_true", help="Отправить готовый альбом в Telegram админу")
    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y-%m-%d")
    print("=" * 60)
    print(f"[SPECTR MIND] Запуск генератора каруселей // {date_str}")
    print("=" * 60)

    print("1. Генерирую сценарий карусели и текст поста через AI...")
    deck_data, topic_title, caption = await generate_carousel_deck(args.topic)
    print(f"   -> Тема: «{topic_title}»")

    out_dir = args.output
    if not out_dir:
        slug = "".join(c if c.isalnum() else "_" for c in topic_title[:30]).strip("_")
        out_dir = os.path.join("output_carousels", f"{date_str}_{slug}")

    os.makedirs(out_dir, exist_ok=True)
    print(f"2. Рендерю 5 слайдов в стиле Cyan Edition в {out_dir}...")
    files = render_carousel_images(deck_data, output_dir=out_dir)

    # Сохраняем текст поста рядом со слайдами
    caption_path = os.path.join(out_dir, "caption_instagram.txt")
    with open(caption_path, "w", encoding="utf-8") as f:
        f.write(caption)

    print(f"   -> Успешно создано {len(files)} слайдов:")
    for fp in files:
        print(f"      • {fp}")
    print(f"   -> Текст поста сохранен в: {caption_path}")

    if args.send_tg:
        print("3. Отправляю пак в Telegram...")
        await send_to_telegram(files, caption, topic_title)

    print("=" * 60)
    print("[SPECTR MIND] Готово! Карусель готова к публикации.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
