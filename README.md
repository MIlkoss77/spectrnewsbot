# SpectrMind Telegram Bot

Бесплатный бот для автоматической генерации и публикации постов о нейронауке и нейропсихологии в Telegram-канал SpectrMind.

## Возможности

- 5 типов контента: микро-протоколы, разбор мифов, исследования, утренние рутины, вечерние советы
- Автопостинг 1 раз в день по расписанию
- Бесплатный API OpenRouter (без подписок)
- Fallback-цепочка из 4 бесплатных моделей ИИ
- Ручной постинг через команды

## Быстрый старт

### 1. Создай бота

Открой [@BotFather](https://t.me/BotFather) в Telegram:
```
/newbot
Имя: SpectrMind Content Bot
Username: spectrmind_content_bot
```
Сохрани токен.

### 2. Получи API-ключ OpenRouter

Зарегистрируйся на [openrouter.ai](https://openrouter.ai):
1. Перейди в Settings → API Keys
2. Создай ключ (бесплатно, без привязки карты)
3. Сохрани ключ

### 3. Узнай ID канала

1. Добавь бота админом в канал SpectrMind
2. Перес любое сообщение из канала боту [@userinfobot](https://t.me/userinfobot)
3. Скопируй числовой ID (например `-1001234567890`)

### 4. Настрой окружение

```bash
cp .env.example .env
```

Заполни `.env`:
```
BOT_TOKEN=123456:ABC-DEF...
OPENROUTER_API_KEY=sk-or-v1-...
CHANNEL_ID=@spectrmind
ADMIN_ID=123456789
```

### 5. Установи зависимости и запусти

```bash
pip install -r requirements.txt
python bot.py
```

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Приветствие |
| `/generate` | Сгенерировать пост (превью) |
| `/generate research_digest` | Сгенерировать конкретный тип |
| `/post` | Опубликовать в канал (админ) |
| `/post myth_buster` | Опубликовать конкретный тип |
| `/types` | Список типов контента |
| `/schedule` | Текущее расписание |
| `/help` | Справка |

## Типы контента

| Ключ | Эмодзи | Описание | Вес |
|---|---|---|---|
| `micro_protocol` | ⚙️ | Практические советы | 5 |
| `myth_buster` | ❌ | Разбор мифов | 4 |
| `research_digest` | 🔬 | Разбор исследований | 4 |
| `morning_routine` | ☀️ | Утренние протоколы | 3 |
| `evening_reflection` | 🌙 | Вечерние советы | 2 |

## Расписание (по умолчанию)

- **09:00** МСК — ежедневный пост

Измени через переменную `POST_TIMES` в `.env` (можно указать несколько времён через запятую).

## Бесплатные модели (fallback)

1. `meta-llama/llama-3.1-8b-instruct:free`
2. `google/gemma-2-9b-it:free`
3. `mistralai/mistral-7b-instruct:free`
4. `qwen/qwen-2-7b-instruct:free`

Если основная модель недоступна, бот автоматически переключается на следующую.

## Деплой (бесплатно)

### Railway.app

1. Залей репозиторий на GitHub
2. Подключи на [railway.app](https://railway.app)
3. Добавь переменные окружения
4. Railway автоматически запустит `python bot.py`

### Render.com

1. Создай Background Worker
2. Build: `pip install -r requirements.txt`
3. Start: `python bot.py`
4. Добавь переменные окружения
