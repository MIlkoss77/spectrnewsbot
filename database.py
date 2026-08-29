import aiosqlite
import config

DB_PATH = config.DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                used_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER,
                post_type TEXT NOT NULL,
                content TEXT NOT NULL,
                published INTEGER DEFAULT 0,
                published_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS post_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER,
                channel_msg_id INTEGER,
                status TEXT,
                error TEXT,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)
        await db.commit()


async def seed_topics():
    """Заполняет базу стартовыми темами из стратегии SpectrMind."""
    async with aiosqlite.connect(DB_PATH) as db:
        count = await db.execute("SELECT COUNT(*) FROM topics")
        row = await count.fetchone()
        if row[0] > 0:
            return

        topics = [
            # Микро-протоколы (утро)
            ("micro_protocol", "Утренний ресет дофамина",
             "5 действий первых 30 минут после пробуждения для запуска дофаминовой системы"),
            ("micro_protocol", "Холодный душ: протокол",
             "30 секунд льда = +250% к базовому дофамину на 3-4 часа"),
            ("micro_protocol", "Правило «без телефона первый час»",
             "Почему первый час решает чей будет день — твой или чужой"),
            ("micro_protocol", "Утренний свет и циркадные ритмы",
             "10 минут естественного света = синхронизация внутренних часов"),
            ("micro_protocol", "Дыхание 4-7-8 для фокуса",
             "Техника, которая переключает нервную систему из стресса в рабочее состояние"),
            ("micro_protocol", "Движение до экрана: 7 минут",
             "Минимальная доза физнагрузки, которая запускает BDNF"),
            ("micro_protocol", "Стакан воды до кофе",
             "Дегидратация после сна крадёт 20% когнитивных функций"),

            # Разборы исследований (вечер)
            ("research", "Дофаминовый детокс: что говорит наука",
             "Разбор исследований о дофаминовых рецепторах и привыкании"),
            ("research", "Глубокий сон и память: связь",
             "Как глубокая фаза сна консолидирует воспоминания"),
            ("research", "23 минуты на переключение контекста",
             "Исследование UC Irvine о стоимости мультизадачности"),
            ("research", "Ультрадианные ритмы: 90 минут",
             "Почему мозг работает циклами и как это использовать"),
            ("research", "Холодовое воздействие и нейропластичность",
             "Stanford: как холод активирует коричневый жир и нейроны"),
            ("research", "Магний и глубокий сон",
             "Мета-анализ: магний L-треонат vs глицинат для качества сна"),
            ("research", "Кофеин: период полувыведения 5-6 часов",
             "Математика кофе: почему капучино в 15:00 крадёт сон"),
            ("research", "Нейропластичность после 30",
             "Мозг теряет 1% плотности в год, но нейропластичность сохраняется всю жизнь"),
            ("research", "Синий свет и мелатонин",
             "Механизм: сетчатка → супрахиазматическое ядро → подавление мелатонина"),
            ("research", "Эффект интервального голодания на мозг",
             "Автофагия и когнитивные функции: что показывают клинические данные"),
            ("research", "Эго-деплеция: миф или реальность",
             "Replication crisis и сила воли как исчерпаемый ресурс"),

            # Мифы и заблуждения
            ("myth", "Мотивация — ловушка",
             "Почему мотивация = дофаминовый всплеск, а всплеск всегда = спад"),
            ("myth", "8 часов сна: обязательно ли всем",
             "Генетические вариации (DEC2) и индивидуальная норма сна"),
            ("myth", "Мультизадачность продуктивна",
             "Мозг не многозадачен — он переключается, теряя 23 минуты на каждом"),
            ("myth", "Сила воли — вопрос характера",
             "Дисциплинированные люди не борются — они убирают триггеры"),
            ("myth", "Аффирмации всегда работают",
             "Почему мозг отвергает фальшивые утверждения и что работает лучше"),

            # Протоколы продуктивности
            ("protocol", "Блоки 90/15",
             "Как строить день по ультрадианным ритмам: 90 мин работы → 15 мин отдых"),
            ("protocol", "Правило 2 минут",
             "Мелкие задачи типа C: <2 минут = делай сразу, не откладывай"),
            ("protocol", "HALT-проверка",
             "4 состояния (голод, злость, одиночество, усталость) в которых нельзя решать"),
            ("protocol", "Матрица решений A/B/C",
             "Система категоризации решений по критичности и срокам"),
            ("protocol", "Правило 10/10/10",
             "Как принимать решения: что подумаешь через 10 минут, 10 месяцев, 10 лет"),
        ]

        await db.executemany(
            "INSERT INTO topics (category, title, description) VALUES (?, ?, ?)",
            topics
        )
        await db.commit()


async def get_random_topic(category: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM topics WHERE category = ? ORDER BY used_count ASC, RANDOM() LIMIT 1",
            (category,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
    return None


async def save_post(topic_id: int, post_type: str, content: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO posts (topic_id, post_type, content) VALUES (?, ?, ?)",
            (topic_id, post_type, content)
        )
        await db.execute(
            "UPDATE topics SET used_count = used_count + 1 WHERE id = ?",
            (topic_id,)
        )
        await db.commit()
        return cursor.lastrowid


async def mark_published(post_id: int, channel_msg_id: int = None, status: str = "ok", error: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE posts SET published = 1, published_at = CURRENT_TIMESTAMP WHERE id = ?",
            (post_id,)
        )
        await db.execute(
            "INSERT INTO post_log (post_id, channel_msg_id, status, error) VALUES (?, ?, ?, ?)",
            (post_id, channel_msg_id, status, error)
        )
        await db.commit()


async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM posts WHERE published = 1")
        published = (await cur.fetchone())[0]
        cur = await db.execute("SELECT COUNT(*) FROM posts WHERE published = 0")
        drafts = (await cur.fetchone())[0]
        cur = await db.execute("SELECT COUNT(*) FROM topics")
        topics = (await cur.fetchone())[0]
        cur = await db.execute(
            "SELECT COUNT(*) FROM post_log WHERE status = 'error' AND posted_at > datetime('now', '-7 days')"
        )
        errors_week = (await cur.fetchone())[0]
    return {"published": published, "drafts": drafts, "topics": topics, "errors_week": errors_week}


async def add_subscriber(user_id: int, username: str = None, first_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO subscribers (user_id, username, first_name)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
               username = excluded.username,
               first_name = excluded.first_name,
               is_active = 1""",
            (user_id, username, first_name),
        )
        await db.commit()


async def get_active_subscribers() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT user_id, username, first_name FROM subscribers WHERE is_active = 1"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_subscriber_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM subscribers WHERE is_active = 1"
        )
        row = await cursor.fetchone()
        return row[0]


async def deactivate_subscriber(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscribers SET is_active = 0 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()
