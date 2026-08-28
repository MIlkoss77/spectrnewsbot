# SpectrMind Telegram Bot

Бот для автоматического ведения Telegram-канала SpectrMind о нейронауке и когнитивной продуктивности.

## Что делает

- **Автопостинг** по расписанию (2-4 поста/день)
- **Генерация контента** через OpenRouter (MiMo, GPT, Gemini, Claude и др.)
- **Лид-магнит** — чек-лист «7 утренних ошибок» при /start
- **4 категории постов:**
  - 🌅 Микро-протоколы (утро 8:00)
  - 🔬 Разборы исследований (вечер 19:00)
  - ❌ Разборы мифов (вт, чт, сб 13:00)
  - ⚡ Протоколы продуктивности (пт, вс 13:00)

## Расписание

| Время | Пост | Дни |
|-------|------|-----|
| 08:00 | Микро-протокол | Каждый день |
| 13:00 | Миф | Вт, Чт, Сб |
| 13:00 | Протокол | Пт, Вс |
| 19:00 | Исследование | Каждый день |

## Установка на VPS

### 1. Подготовка сервера

```bash
# Подключаемся к VPS
ssh root@ваш-сервер

# Обновляем систему (Ubuntu/Debian)
apt update && apt upgrade -y

# Устанавливаем Python 3.11+
apt install python3 python3-pip python3-venv -y
```

### 2. Копируем проект

```bash
# Создаём директорию
mkdir -p /opt/spectrmind-bot
cd /opt/spectrmind-bot

# Копируем файлы с локальной машины (или через git)
scp -r C:\Users\Admin\spectrmind-bot/* root@ваш-сервер:/opt/spectrmind-bot/
```

### 3. Устанавливаем зависимости

```bash
cd /opt/spectrmind-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Настраиваем переменные окружения

```bash
cp .env.example .env
nano .env
```

Заполняем:

```env
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
CHANNEL_ID=@spectrmind
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxx
MODEL=xiaomi/mimo-v2.5-pro
TIMEZONE=Europe/Moscow
MORNING_POST_HOUR=8
MORNING_POST_MINUTE=0
EVENING_POST_HOUR=19
EVENING_POST_MINUTE=0
```

### 5. Получаем BOT_TOKEN

1. Открываем Telegram, ищем @BotFather
2. Отправляем `/newbot`
3. Называем бота (например, `SpectrMind Bot`)
4. Копируем токен в `.env`

### 6. Получаем CHANNEL_ID

1. Добавляем бота в канал как **администратора** (право на отправку сообщений)
2. Если канал публичный с username `@spectrmind` — пишем `CHANNEL_ID=@spectrmind`
3. Если канал приватный — пересылаем любое сообщение канала боту @userinfobot

### 7. Получаем OPENROUTER_API_KEY

1. Идём на https://openrouter.ai/keys
2. Регистрируемся (можно через Google/GitHub)
3. Нажимаем «Create Key»
4. Копируем ключ в `.env`
5. Пополнять баланс НЕ нужно — используются бесплатные модели

**Бесплатные модели** (pricing = 0, указать в `.env` в переменной `MODEL`):
- `google/gemma-4-31b-it:free` — Gemma 4 31B (рекомендуется, лучший русский)
- `nvidia/nemotron-3-ultra-550b-a55b:free` — Nemotron 3 Ultra 550B (самая мощная)
- `nvidia/nemotron-3-super-120b-a12b:free` — Nemotron 3 Super 120B (баланс)
- `openai/gpt-oss-20b:free` — OpenAI open-source 21B

Все бесплатные модели: https://openrouter.ai/models?q=free

### 8. Запускаем

```bash
# Тестовый запуск
python3 bot.py

# Если всё работает — запускаем как сервис (см. ниже)
```

### 9. Автозапуск через systemd

```bash
cat > /etc/systemd/system/spectrmind-bot.service << 'EOF'
[Unit]
Description=SpectrMind Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/spectrmind-bot
ExecStart=/opt/spectrmind-bot/venv/bin/python3 bot.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Активируем и запускаем
systemctl daemon-reload
systemctl enable spectrmind-bot
systemctl start spectrmind-bot

# Проверяем статус
systemctl status spectrmind-bot

# Смотрим логи
journalctl -u spectrmind-bot -f
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие + выдача чек-листа (лид-магнит) |
| `/help` | Список команд |
| `/stats` | Статистика: опубликовано, черновики, темы |
| `/schedule` | Текущее расписание постов |
| `/preview [категория]` | Превью поста без публикации |
| `/now [категория]` | Немедленная публикация в канал |

Категории: `micro_protocol`, `research`, `myth`, `protocol`

## Как добавить свои темы

Темы хранятся в SQLite (`spectrmind.db`). Можно добавить через Python:

```python
import asyncio
import aiosqlite

async def add_topic():
    async with aiosqlite.connect("spectrmind.db") as db:
        await db.execute(
            "INSERT INTO topics (category, title, description) VALUES (?, ?, ?)",
            ("research", "Креатин и когнитивные функции", "Мета-анализ: 5г креатина в день улучшает рабочую память")
        )
        await db.commit()

asyncio.run(add_topic())
```

## Структура проекта

```
spectrmind-bot/
├── .env.example          # Шаблон переменных
├── requirements.txt      # Зависимости Python
├── config.py             # Конфигурация
├── database.py           # SQLite: темы, посты, логи
├── content_generator.py  # Генерация через OpenRouter
├── scheduler.py          # APScheduler: расписание
├── bot.py                # Основной файл бота
└── README.md             # Этот файл
```

## Стоимость

- **VPS:** от 300 ₽/мес (TimeWeb, Selectel, Beget)
- **OpenRouter API:** $0 (бесплатные модели Gemma/Nemotron)
- **Telegram Bot API:** бесплатно

Итого: **~300 ₽/мес** на всё (только VPS).

## Что дальше

После запуска бота можно добавить:
- Автопостинг в 2 канала (публичный + закрытый клуб)
- Онбординг-цепочка для новых подписчиков
- Кнопки «Купить гайд» под продающими постами
- Интеграция с ManyChat для квиза «Твой тип рассеянности»
