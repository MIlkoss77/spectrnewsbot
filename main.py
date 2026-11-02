"""Точка входа Spectr Mind Telegram Bot (алиас для bot.py).

Запуск:
    python main.py
или
    python bot.py
"""
import asyncio
from bot import main

if __name__ == "__main__":
    asyncio.run(main())
