# 📊 ТЕКУЩИЙ СТАТУС ПРОЕКТА «SPECTR MIND»

> **Дата актуализации:** 12 ноября 2026  
> **Ветка Git:** `master` (`f36a807`)  
> **Тесты (`tools_selfcheck.py`):** 198 passed, 0 failed  
> **Прод-сервер:** `1727109.xorek.cloud` (`150.241.107.202`)

---

## 1. ИНФРАСТРУКТУРА И СЕРВИСЫ (PRODUCTION)

| Сервис | Назначение | Статус | Путь / Управление |
|---|---|---|---|
| `spectrmind-bot.service` | Основной Telegram-бот `@spectrnewsbot` (воронка, автопостинг, триалы, карусели) | **active (running)** | `/opt/spectrmind-bot` (`systemctl restart spectrmind-bot`) |
| PM2 `robokassa` | Обработчик платежей сайта `spectrmind.ru` и отправка welcome-писем (порт `3001`) | **online** | `/var/www/spectrmind_landing_ru/out/server/index.js` (`pm2 restart robokassa`) |
| PM2 `spectr-api`, `spectr-bot` | API и сервис лендинга | **online** | PM2 cluster/fork |
| `nginx.service` | Веб-сервер и reverse proxy | **active (running)** | — |

---

## 2. ЧТО РЕАЛИЗОВАНО И РАБОТАЕТ

### А. Telegram-бот `@spectrnewsbot`
1. **Выдача бесплатного лид-магнита (`/start`):**
   * Учитывает метку источника (`?start=ig`, `?start=yt`, `?start=ig_protocol` и др.) в SQLite (`spectrmind.db`).
   * Выдаёт `SPECTR_Prefrontal_Protocol.pdf` с **единственной кнопкой «📚 Бесплатный канал»** (`@ruspectrmind`), без перегрузки кнопками оплаты на старте.
2. **Автоворонка дожима на 3 касания (`funnel.py`, база `funnel_timers.db`):**
   * Фоновый воркер `funnel_worker` проверяет таймеры каждые 30 секунд.
   * **Шаг 1 (+15 минут):** про выгорание D2 и пептиды `Semax, Selank` → кнопка покупки гайда (**1 990 ₽**).
   * **Шаг 2 (на следующий день ровно в 14:00 МСК):** аденозиновый краш и сон NREM 3 → оффер со скидкой 50% (**1 990 ₽**).
   * **Шаг 3 (+48 часов):** финальный выбор — **«Нейро Протоколы» (1 990 ₽)** или **«Закрытый клуб» (990 ₽/мес)**.
   * Ссылки оплаты подписываются Robokassa на лету с `Shp_user={user_id}`.
3. **Бонусный доступ в SPECTR CLUB на 7 дней (`trial_club.py`):**
   * По ссылке `https://t.me/spectrnewsbot?start=trial7` бот выдаёт **одноразовую персональную инвайт-ссылку** (`member_limit=1`) в закрытый канал `PREMIUM_CHANNEL_ID` (`-1004398718586`) и ставит таймер на 7 дней (1 аккаунт = 1 триал).
   * На **6-й день** (за 24 часа до окончания) присылает напоминание с кнопкой продления за 990 ₽/мес.
   * На **7-й день** автоматически исключает пользователя из канала (`ban` + `unban` без вечного бана) и предлагает вернуться по подписке.
4. **Мобильная генерация каруселей и автопостинг:**
   * Команда `/carousel` генерирует 5 слайдов `1080×1350` в палитре **Cyan Edition** и готовый текст с кодовым словом.
   * Планировщик ежедневно публикует посты в бесплатный канал `@ruspectrmind`.
5. **Админ-команды:**
   * `/subscribers` — статистика подписчиков по источникам трафика.
   * `/funnel` — статистика по шагам и статусам автоворонки.
   * `/trials` — статистика активных, истёкших и продлённых 7-дневных триалов.
   * `/paid USER_ID` — пометить оплатившего клуб (отменяет автоисключение на 7-й день).
   * `/invite` — сгенерировать одноразовую ссылку в `Spectr Private`.

---

### Б. Сайт `spectrmind.ru` и Welcome-письма после оплаты
* **Бекенд:** `/var/www/spectrmind_landing_ru/out/server/index.js` (бэкап сохранён: `index.js.bak_20261112_150555`).
* **Дизайн писем:** все 5 шаблонов (`neuro-hacker`, `spectr-club`, `base-club`, `neuro-master`, `test`) переведены в единый стиль **Cyan Edition** (`#020C16` / `#071826` / `#00E5FF`) на табличной вёрстке со 100% inline CSS. Кодировка UTF-8 проверена тестовой отправкой на Gmail (`250 2.0.0 OK`).
* **Выдача по тарифу `neuro-hacker` (1 990 ₽):**
  * **Шаг 01:** кнопка на папку Google Диска с материалами (`LINKS.drive`).
  * **Шаг 02 (бонус):** кнопка **`АКТИВИРОВАТЬ 7 ДНЕЙ В КЛУБЕ →`** на `https://t.me/spectrnewsbot?start=trial7`.
* **Актуальная ссылка в `SPECTR CLUB` (`LINKS.telegram`):** `https://t.me/+SDVtlMuK9gM1YTQy`.

---

### В. Контент, промпты и продуктовые материалы
* **PDF «Календари циклирования (90 дней)»:** [SPECTR_90_Day_Cycling_Calendars.pdf](file:///c:/Users/Admin/Desktop/spectrmind-bot/SPECTR_90_Day_Cycling_Calendars.pdf) (6 страниц A4, стиль Cyan Edition, схемы `ON/OFF` для `Semax, Selank, P21`, советских адаптогенов, дофамина D2 и сводная карта на 12 недель).
* **Шаблоны концовок Reels/Shorts (`1080×1920`):** [content/outro_templates/](file:///c:/Users/Admin/Desktop/spectrmind-bot/content/outro_templates/) (`outro_ambient_silence.png`, `outro_speech_willpower.png`, `outro_neuro_protocol.png`).
* **Актуализированные брифы:** [MASTER_BRIEF.md](file:///c:/Users/Admin/Desktop/spectrmind-bot/MASTER_BRIEF.md) и [AGENT_BRIEF.md](file:///c:/Users/Admin/Desktop/spectrmind-bot/AGENT_BRIEF.md) (воронка по кодовым словам в комментариях/Direct, палитра Cyan Edition).

---

## 3. ЧТО ОСТАЛОСЬ СДЕЛАТЬ (NEXT STEPS)

1. **Загрузить в Google Диск** (`LINKS.drive`) готовый файл [SPECTR_90_Day_Cycling_Calendars.pdf](file:///c:/Users/Admin/Desktop/spectrmind-bot/SPECTR_90_Day_Cycling_Calendars.pdf), чтобы покупатели тарифа `neuro-hacker` сразу видели его в папке после оплаты.
2. **Контент-спринт Reels / Shorts / Карусели:**
   * Делать упор на формат **документального научного расследования** (архивы СССР, Бехтерева, Анохин, реальные учёные/спикеры в первые 2 сек + кодовое слово `НЕЙРО` / `ТИШИНА` / `ВОЛЯ` в комментариях).
   * Обрабатывать комментарии и Direct через встроенные **Быстрые ответы** Instagram (без затрат на ManyChat).
3. **На сервере (опционально):** подтянуть на `/opt/spectrmind-bot` последний коммит с PDF-генератором (`git pull`), если нужен сам файл локально на VPS.
