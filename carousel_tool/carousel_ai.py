# -*- coding: utf-8 -*-
"""
SPECTR MIND // CAROUSEL AI ENGINE
Автоматическая генерация 5-слайдовых каруселей Instagram (Cyan Edition)
на базе фундаментальной советской нейробиологии (Бехтерева, сосуды, мозг 35-45+).
"""

import os
import json
import re
import logging
from typing import Dict, List, Tuple, Optional
import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, PROXY_URL
from carousel_tool.spectr_carousel_generator import SpectrCarouselGenerator

logger = logging.getLogger(__name__)

# ==============================================================================
# ЗОЛОТОЙ ПУЛ ТЕМ SPECTR MIND (ЦА 35-45+, СССР, НЕЙРОБИОЛОГИЯ, ЗДОРОВЬЕ, СОСУДЫ)
# ==============================================================================
SOVIET_NEURO_TOPICS = [
    {
        "title": "Янтарная кислота для сосудов мозга: секрет Академгородка",
        "category": "ФАРМАКОЛОГИЯ СССР // АТФ",
        "focus": "Цикл Кребса, мгновенное снятие гипоксии нейронов, почему ее давали космонавтам при перегрузках",
    },
    {
        "title": "Почему Бехтерева запрещала кофе натощак: спазм сосудов мозга",
        "category": "НЕЙРОБИОЛОГИЯ // АРХИВ СССР",
        "focus": "Спазм капилляров коры на 25%, блокада аденозина, утренний выброс кортизола и протокол горячей воды",
    },
    {
        "title": "3 советских продукта для защиты памяти и миелиновой оболочки после 40 лет",
        "category": "ПИЩА ДЛЯ МОЗГА // 40+",
        "focus": "Желтки всмятку (фосфатидилхолин), печень трески (фосфолипиды + омега), квашеная капуста (ось кишечник-мозг)",
    },
    {
        "title": "Тест префронтальной коры за 15 секунд: симптом «Куда я шел?»",
        "category": "КЛИНИЧЕСКИЙ ТЕСТ // ПФК",
        "focus": "Истощение запаса АТФ, накопление глутамата в синапсах, перезапуск внимания через 60-секундный холодовой термогенез",
    },
    {
        "title": "Секрет полярников СССР: почему на Севере не ломается дофамин",
        "category": "СОВЕТСКАЯ НАУКА // СЕВЕР",
        "focus": "Холодовой термогенез, выброс норадреналина на +530%, защита от выгорания и сброс дофаминовой ямы",
    },
    {
        "title": "Глимфатическая система: как ночной сон на боку вымывает токсины из мозга",
        "category": "НЕЙРОБИОЛОГИЯ СНА // 40+",
        "focus": "Вымывание бета-амилоида ликвором, фаза глубокого сна, почему ужин за 3 часа блокирует очищение таламуса",
    },
    {
        "title": "Сахарный удар по синапсам: почему сладкий завтрак выключает внимание",
        "category": "МЕТАБОЛИЗМ // ДОФАМИН",
        "focus": "Инсулиновый пик, реактивная гипогликемия, почему префронтальная кора засыпает через 45 минут после каши",
    },
    {
        "title": "Дыхание советских подводников 4-4-4-4: сброс кортизола за 90 секунд",
        "category": "КОСМИЧЕСКАЯ МЕДИЦИНА // ВНС",
        "focus": "Стимуляция блуждающего нерва (nervus vagus), выравнивание CO2, расширение сосудов коры при панике и стрессе",
    },
    {
        "title": "Ацетилхолиновая яма после 35 лет: почему забываются имена и слова",
        "category": "НЕЙРОМЕДИАТОРЫ // ПАМЯТЬ",
        "focus": "Падение синтеза холина на 15% за десятилетие, восстановление плотности рецепторов через лецитин и сон",
    },
    {
        "title": "Магний и тормозной медиатор ГАМК: как в СССР лечили ночную тревожность",
        "category": "СОСУДЫ И СОН // ГАМК",
        "focus": "Снятие гипервозбуждения амигдалы, глубокая фаза медленного сна, расслабление сосудистой стенки",
    },
]

STATE_FILE = "recent_carousel_topics.json"


def get_next_carousel_topic() -> Dict[str, str]:
    """Возвращает следующую неиспользованную тему из пула."""
    used = []
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                used = json.load(f)
        except Exception:
            used = []

    for item in SOVIET_NEURO_TOPICS:
        if item["title"] not in used:
            used.append(item["title"])
            if len(used) >= len(SOVIET_NEURO_TOPICS):
                used = [item["title"]]
            try:
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(used, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return item

    used = [SOVIET_NEURO_TOPICS[0]["title"]]
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(used, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return SOVIET_NEURO_TOPICS[0]


SYSTEM_PROMPT = """Ты — ведущий научный редактор проекта Spectr Mind.
Специализация: фундаментальная советская нейробиология, Институт мозга Бехтеревой, сосуды мозга, управление префронтальной корой (ПФК), биохакинг для аудитории 35–45+ лет.
Стиль: авторитетный, кинематографичный (A24 / советский научный детектив), доказательный.

Твоя задача: написать сценарий Instagram-карусели СТРОГО ИЗ 5 СЛАЙДОВ по нативной воронке продаж.
ОБЯЗАТЕЛЬНО возвращай валидный JSON строго с этими ключами:
{
  "topic": "Название темы",
  "meta": {
    "issue_code": "VOL. 09 // NEURO-DOSSIER",
    "classification": "SPECTR LAB // ARCHIVE"
  },
  "slides": [
    {
      "type": "cover",
      "badge": "НЕЙРОБИОЛОГИЯ // АРХИВ СССР",
      "title": "ПОЧЕМУ ПРЕПАРАТ ЗА 50 РУБЛЕЙ *ПЕРЕЗАПУСКАЕТ* СОСУДЫ МОЗГА",
      "subtitle": "Как советские ученые снимали кислородное голодание нейронов за 120 секунд без стимуляторов."
    },
    {
      "type": "content",
      "badge": "ФАКТ №01 // МИТОХОНДРИИ КОРЫ",
      "title": "ДЕФИЦИТ АТФ: ПОЧЕМУ МОЗГ *ВЫКЛЮЧАЕТСЯ* ПОСЛЕ ОБЕДА",
      "body": "Префронтальная кора потребляет до *25% всей глюкозы* организма. При гипоксии выработка клеточной энергии АТФ падает в 4 раза.\\n\\nВместо фокуса в синапсах накапливается глутамат — мозг впадает в *сонливый ступор* и требует сладкого.",
      "metrics": [
        {"value": "-40%", "label": "Падение клеточного АТФ"},
        {"value": "45 МИН", "label": "Развитие гипоксии"},
        {"value": "+180%", "label": "Выброс кортизола"}
      ],
      "callout": "КЛИНИЧЕСКИЙ ФАКТ: Мозг весит 2% от массы тела, но спазм микрососудов лишает его 50% рабочей памяти."
    },
    {
      "type": "content",
      "badge": "ФАКТ №02 // СОВЕТСКИЙ ПРОТОКОЛ",
      "title": "АРХИВ АКАДЕМГОРОДКА: СТИМУЛЯЦИЯ *ЦИКЛА КРЕБСА*",
      "body": "В советской космической медицине янтарную кислоту использовали для операторов при перегрузках.\\n\\nОна отдает электроны напрямую в дыхательную цепь митохондрий, форсируя синтез АТФ на *340% быстрее*, чем глюкоза.",
      "metrics": [
        {"value": "120 СЕК", "label": "Запуск клеточного дыхания"},
        {"value": "+340%", "label": "Скорость синтеза АТФ"}
      ],
      "callout": "ИСТОЧНИК: Исследования Института биофизики АН СССР и протоколы Института мозга."
    },
    {
      "type": "protocol",
      "badge": "ПРАКТИКА // 3 ШАГА ПЕРЕЗАПУСКА",
      "title": "3 ШАГА ЗАЩИТЫ *СОСУДОВ МОЗГА* ПРИ СПАЗМЕ",
      "steps": [
        {
          "code": "01 // ВОДА",
          "heading": "400 мл горячей воды (45°C)",
          "text": "Смывает застой желчи, снимает спазм сосудов шеи и восстанавливает *приток крови* к коре."
        },
        {
          "code": "02 // КИСЛОТА",
          "heading": "Янтарная кислота (100–200 мг)",
          "text": "Принимается строго после еды. Запускает *митохондрии нейронов* и снимает туман за 15 минут."
        },
        {
          "code": "03 // ДЫХАНИЕ",
          "heading": "Квадратное дыхание 4-4-4-4 (2 мин)",
          "text": "Выравнивает уровень CO2, расширяет мозговые артерии и доставляет *глюкозу* в синапсы."
        }
      ]
    },
    {
      "type": "cta",
      "badge": "БЕСПЛАТНЫЙ ПРОТОКОЛ В TELEGRAM",
      "title": "ЗАБЕРИ ПОЛНЫЙ НЕЙРО-ПРОТОКОЛ В НАШЕМ *TELEGRAM-БОТЕ*",
      "body": "Мы упаковали подробные таблицы советских адаптогенов, схему утреннего перезапуска и вечерний чек-лист сна в закрытый 4-страничный PDF-файл.",
      "lead_magnet_title": "Гайд «Нейро-Стек: Управление ПФК»",
      "cta_button": "ССЫЛКА В ШАПКЕ ПРОФИЛЯ -> @SPECTRNEWSBOT",
      "footer_note": "Или напиши кодовое слово *НЕЙРО* в комментарии — пришлем прямую ссылку на выдачу PDF в Директ за 5 секунд."
    }
  ],
  "caption": "Текст описания для Instagram поста..."
}

ВАЖНЕЙШИЕ ПРАВИЛА:
1. Ключи на каждом слайде ОБЯЗАТЕЛЬНЫ: 'type', 'badge', 'title', 'body', 'subtitle', 'metrics', 'callout', 'steps', 'code', 'heading', 'text', 'lead_magnet_title', 'cta_button', 'footer_note'.
2. На слайде 4 в 'steps' ДОЛЖНО быть ровно 3 шага с 'code' вида '01 // ТЕГ' (где ТЕГ — одно слово капсом: ВОДА, ХОЛОД, ДЫХАНИЕ, СОН, АТФ).
3. ОТВЕТЬ ТОЛЬКО ВАЛИДНЫМ JSON БЕЗ ЛИШНЕГО ТЕКСТА."""


def normalize_deck(deck: Dict, topic_title: str) -> Dict:
    """
    Гарантирует 100% заполненность и корректность всех полей для SpectrCarouselGenerator.
    Если LLM использовал альтернативные ключи или что-то пропустил — нормализатор всё исправит.
    """
    slides = deck.get("slides", [])
    if not isinstance(slides, list) or len(slides) < 4:
        return _get_fallback_deck({"title": topic_title})

    # Слайд 1: Cover
    s1 = slides[0]
    s1["type"] = "cover"
    s1["title"] = s1.get("title") or s1.get("heading") or s1.get("header") or f"{topic_title.upper()}: АРХИВ СССР"
    s1["subtitle"] = s1.get("subtitle") or s1.get("sub_title") or s1.get("description") or "Как советские ученые снимали кислородное голодание нейронов без стимуляторов."
    s1["badge"] = s1.get("badge") or "НЕЙРОБИОЛОГИЯ // АРХИВ СССР"
    s1["bg_image"] = "carousel_tool/assets/cyan_brain_bg.jpg"

    # Слайд 2: Content (Факт 1)
    if len(slides) > 1:
        s2 = slides[1]
        s2["type"] = "content"
        s2["badge"] = s2.get("badge") or "ФАКТ №01 // СОСУДИСТЫЙ СПАЗМ"
        s2["title"] = s2.get("title") or s2.get("heading") or s2.get("header") or "КАК СПАЗМ КАПИЛЛЯРОВ *БЛОКИРУЕТ* МОЗГ"
        s2["body"] = s2.get("body") or s2.get("text") or s2.get("description") or s2.get("content") or (
            "Префронтальная кора потребляет до *25% всей глюкозы* организма. "
            "При малейшем спазме сосудов синапсы испытывают резкий дефицит кислорода, а уровень кортизола взлетает до пика тревоги."
        )
        if not s2.get("metrics") or not isinstance(s2.get("metrics"), list):
            s2["metrics"] = [
                {"value": "-25%", "label": "Снижение кровотока"},
                {"value": "90 МИН", "label": "Время спазма"},
                {"value": "+180%", "label": "Скачок кортизола"},
            ]
        if not s2.get("callout"):
            s2["callout"] = "КЛИНИЧЕСКИЙ ФАКТ: Мозг не отличает эмоциональный стресс от спазма капилляров — реакция одинакова."

    # Слайд 3: Content (Факт 2)
    if len(slides) > 2:
        s3 = slides[2]
        s3["type"] = "content"
        s3["badge"] = s3.get("badge") or "ФАКТ №02 // СОВЕТСКИЙ ПРОТОКОЛ"
        s3["title"] = s3.get("title") or s3.get("heading") or s3.get("header") or "АРХИВ БЕХТЕРЕВОЙ: ПЕРЕЗАПУСК *БЕЗ ХИМИИ*"
        s3["body"] = s3.get("body") or s3.get("text") or s3.get("description") or s3.get("content") or (
            "В Институте мозга АМН СССР эту проблему решали через стимуляцию *блуждающего нерва* и дыхательную гипоксию. "
            "Это естественным образом расширяет артерии коры за 120 секунд."
        )
        if not s3.get("metrics") or not isinstance(s3.get("metrics"), list):
            s3["metrics"] = [
                {"value": "120 СЕК", "label": "Снятие спазма"},
                {"value": "+530%", "label": "Эндогенный норадреналин"},
            ]
        if not s3.get("callout"):
            s3["callout"] = "ИСТОЧНИК: Исследования Института экспериментальной медицины АМН СССР (Бехтерева Н.П.)."

    # Слайд 4: Protocol
    if len(slides) > 3:
        s4 = slides[3]
        s4["type"] = "protocol"
        s4["badge"] = s4.get("badge") or "ПРАКТИКА // 3 ШАГА ПЕРЕЗАПУСКА"
        s4["title"] = s4.get("title") or s4.get("heading") or s4.get("header") or "3 ШАГА ЗАЩИТЫ *СОСУДОВ МОЗГА* УТРОМ"
        raw_steps = s4.get("steps") or s4.get("items") or s4.get("protocol") or []
        if not raw_steps or not isinstance(raw_steps, list) or len(raw_steps) < 2:
            s4["steps"] = [
                {"code": "01 // ВОДА", "heading": "400 мл горячей воды (45°C)", "text": "Смывает застой желчи, снимает спазм сосудов шеи и разжижает *приток крови* к коре."},
                {"code": "02 // ХОЛОД", "heading": "Умывание ледяной водой (15°C)", "text": "Холодовой шок лица включает окулокардиальный рефлекс, гасит *амигдалу* и проясняет ум за 30 секунд."},
                {"code": "03 // ДЫХАНИЕ", "heading": "Квадратное дыхание 4-4-4-4 (2 мин)", "text": "Мягкая гиперкапния расширяет мозговые артерии, доставляя *кислород* напрямую в синапсы."},
            ]
        else:
            norm_steps = []
            for s_idx, st in enumerate(raw_steps[:3]):
                if isinstance(st, dict):
                    c = st.get("code") or f"0{s_idx+1} // ШАГ"
                    h = st.get("heading") or st.get("title") or f"Шаг {s_idx+1}"
                    t = st.get("text") or st.get("description") or st.get("body") or "Снятие спазма сосудов и возвращение ясности ума."
                    norm_steps.append({"code": c, "heading": h, "text": t})
            if len(norm_steps) < 3:
                norm_steps.append({"code": "03 // ДЫХАНИЕ", "heading": "Диафрагмальное дыхание (2 мин)", "text": "Снимает спазм сосудов коры за счет мягкого накопления *углекислого газа*."})
            s4["steps"] = norm_steps

    # Слайд 5: CTA
    if len(slides) > 4:
        s5 = slides[4]
        s5["type"] = "cta"
        s5["badge"] = s5.get("badge") or "БЕСПЛАТНЫЙ ПРОТОКОЛ В TELEGRAM"
        s5["title"] = s5.get("title") or s5.get("heading") or s5.get("header") or "ЗАБЕРИ ПОЛНЫЙ НЕЙРО-ПРОТОКОЛ В НАШЕМ *TELEGRAM-БОТЕ*"
        s5["body"] = s5.get("body") or s5.get("text") or s5.get("description") or (
            "Мы упаковали подробные таблицы советских адаптогенов, схему утреннего перезапуска и вечерний чек-лист сна в закрытый 4-страничный PDF-файл."
        )
        s5["lead_magnet_title"] = s5.get("lead_magnet_title") or "Гайд «Нейро-Стек: Управление ПФК»"
        s5["cta_button"] = s5.get("cta_button") or "ССЫЛКА В ШАПКЕ ПРОФИЛЯ -> @SPECTRNEWSBOT"
        s5["footer_note"] = s5.get("footer_note") or "Или напиши кодовое слово *НЕЙРО* в комментарии — пришлем прямую ссылку на выдачу PDF в Директ за 5 секунд."

    deck["slides"] = slides[:5]
    return deck


def _get_fallback_deck(topic_info: Dict[str, str]) -> Dict:
    """Резервный высококачественный шаблон карусели, если API недоступен."""
    t_title = topic_info.get("title", "Янтарная кислота для сосудов мозга")
    return {
        "topic": t_title,
        "meta": {
            "issue_code": "VOL. 09 // SOVIET NEURO-ARCHIVE",
            "classification": "SPECTR LAB // CLINICAL DOSSIER",
        },
        "slides": [
            {
                "type": "cover",
                "badge": topic_info.get("category", "НЕЙРОБИОЛОГИЯ // АРХИВ СССР"),
                "title": f"ЯНТАРНАЯ КИСЛОТА: СЕКРЕТ *АКАДЕМГОРОДКА* ДЛЯ СОСУДОВ МОЗГА",
                "subtitle": "Как советские ученые снимали кислородное голодание нейронов за 120 секунд без стимуляторов.",
                "bg_image": "carousel_tool/assets/cyan_brain_bg.jpg",
            },
            {
                "type": "content",
                "badge": "ФАКТ №01 // МИТОХОНДРИИ КОРЫ",
                "title": "ДЕФИЦИТ АТФ: ПОЧЕМУ МОЗГ *ВЫКЛЮЧАЕТСЯ* ПОСЛЕ ОБЕДА",
                "body": "Префронтальная кора потребляет до *25% всей глюкозы* организма. При гипоксии выработка клеточной энергии АТФ падает в 4 раза.\n\nВместо фокуса в синапсах накапливается глутамат — мозг впадает в *сонливый ступор* и требует сладкого.",
                "metrics": [
                    {"value": "-40%", "label": "Падение клеточного АТФ"},
                    {"value": "45 МИН", "label": "Развитие гипоксии"},
                    {"value": "+180%", "label": "Выброс кортизола"},
                ],
                "callout": "КЛИНИЧЕСКИЙ ФАКТ: Мозг весит 2% от массы тела, но спазм микрососудов лишает его 50% рабочей памяти.",
            },
            {
                "type": "content",
                "badge": "ФАКТ №02 // СОВЕТСКИЙ ПРОТОКОЛ",
                "title": "АРХИВ АКАДЕМГОРОДКА: СТИМУЛЯЦИЯ *ЦИКЛА КРЕБСА*",
                "body": "В советской космической медицине янтарную кислоту использовали для операторов при перегрузках.\n\nОна отдает электроны напрямую в дыхательную цепь митохондрий, форсируя синтез АТФ на *340% быстрее*, чем глюкоза.",
                "metrics": [
                    {"value": "120 СЕК", "label": "Запуск клеточного дыхания"},
                    {"value": "+340%", "label": "Скорость синтеза АТФ"},
                ],
                "callout": "ИСТОЧНИК: Исследования Института биофизики АН СССР и протоколы Института мозга.",
            },
            {
                "type": "protocol",
                "badge": "ПРАКТИКА // 3 ШАГА ПЕРЕЗАПУСКА",
                "title": "3 ШАГА ЗАЩИТЫ *СОСУДОВ МОЗГА* ПРИ СПАЗМЕ",
                "steps": [
                    {
                        "code": "01 // ВОДА",
                        "heading": "400 мл горячей воды (45°C)",
                        "text": "Смывает застой желчи, снимает спазм сосудов шеи и восстанавливает *приток крови* к коре.",
                    },
                    {
                        "code": "02 // КИСЛОТА",
                        "heading": "Янтарная кислота (100–200 мг)",
                        "text": "Принимается строго после еды. Запускает *митохондрии нейронов* и снимает туман за 15 минут.",
                    },
                    {
                        "code": "03 // ДЫХАНИЕ",
                        "heading": "Квадратное дыхание 4-4-4-4 (2 мин)",
                        "text": "Выравнивает уровень CO2, расширяет мозговые артерии и доставляет *глюкозу* в синапсы.",
                    },
                ],
            },
            {
                "type": "cta",
                "badge": "БЕСПЛАТНЫЙ ПРОТОКОЛ В TELEGRAM",
                "title": "ЗАБЕРИ ПОЛНЫЙ НЕЙРО-ПРОТОКОЛ В НАШЕМ *TELEGRAM-БОТЕ*",
                "body": "Мы упаковали таблицы советских адаптогенов, схему утреннего перезапуска и вечерний чек-лист сна в закрытый 4-страничный PDF-файл.",
                "lead_magnet_title": "Гайд «Нейро-Стек: Управление ПФК»",
                "cta_button": "ССЫЛКА В ШАПКЕ ПРОФИЛЯ -> @SPECTRNEWSBOT",
                "footer_note": "Или напиши кодовое слово *НЕЙРО* в комментарии — пришлем прямую ссылку на выдачу PDF в Директ за 5 секунд.",
            },
        ],
        "caption": (
            "🧠 ПОЧЕМУ ПРЕПАРАТ ЗА 50 РУБЛЕЙ СНИМАЕТ ТУМАН В ГОЛОВЕ БЫСТРЕЕ КОФЕ?\n\n"
            "После 35 лет нейроны префронтальной коры особенно чувствительны к гипоксии: малейший спазм капилляров — и концентрация падает в разы.\n\n"
            "В советском Академгородке эту проблему решали через янтарную кислоту — естественный субстрат клеточного дыхания митохондрий.\n\n"
            "📌 Листай карусель — там подробная схема и дозировки.\n\n"
            "🎁 Полный 4-страничный PDF «Нейро-Стек: Управление префронтальной корой» с таблицами советских адаптогенов уже в нашем Telegram-боте.\n\n"
            "👉 Ссылка в шапке профиля или пиши слово НЕЙРО в комментарии — вышлем прямую ссылку в Директ!\n\n"
            "#нейробиология #мозг #сосуды #память #бехтерева #биохакинг #здоровье #янтарнаякислота"
        ),
    }


async def generate_carousel_deck(custom_topic: Optional[str] = None) -> Tuple[Dict, str, str]:
    """
    Генерирует данные карусели через LLM или fallback-генератор,
    нормализует структуру и гарантирует отсутствие пустых слайдов.
    Возвращает: (deck_data, topic_title, post_caption)
    """
    if custom_topic and custom_topic.strip():
        topic_info = {
            "title": custom_topic.strip(),
            "category": "НЕЙРОБИОЛОГИЯ // АРХИВ СССР",
            "focus": custom_topic.strip(),
        }
    else:
        topic_info = get_next_carousel_topic()

    topic_title = topic_info["title"]
    user_prompt = (
        f"Тема карусели: «{topic_title}»\n"
        f"Категория: {topic_info.get('category', 'НЕЙРОБИОЛОГИЯ // АРХИВ')}\n"
        f"Ключевой фокус: {topic_info.get('focus', '')}\n\n"
        f"Сгенерируй полный JSON из 5 слайдов со всеми полями: cover, content (факт 1 с 3 метриками), content (факт 2 с 2 метриками), protocol (3 шага с кодами '01 // ТЕГ'), cta (оффер на гайд в боте)."
    )

    deck_data = None
    post_caption = ""

    if OPENROUTER_API_KEY:
        try:
            model = "meta-llama/llama-3.3-70b-instruct"
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://spectrmind.ru",
                "X-Title": "SpectrMind Carousel Generator",
            }
            client_kwargs = {"timeout": 45.0}
            if PROXY_URL:
                client_kwargs["proxy"] = PROXY_URL

            async with httpx.AsyncClient(**client_kwargs) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.6,
                        "max_tokens": 2000,
                    },
                )
                if resp.status_code == 200:
                    raw_content = resp.json()["choices"][0]["message"]["content"]
                    cleaned = re.sub(r"^```(?:json)?", "", raw_content.strip(), flags=re.MULTILINE)
                    cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE).strip()
                    parsed = json.loads(cleaned)
                    if "slides" in parsed and len(parsed["slides"]) >= 4:
                        deck_data = parsed
                        post_caption = parsed.get("caption", "")
        except Exception as e:
            logger.warning("LLM carousel generation failed: %s", e)

    if not deck_data:
        deck_data = _get_fallback_deck(topic_info)
        post_caption = deck_data.get("caption", "")

    # Прогоняем через нормализатор — это гарантирует заполнение всех слайдов!
    deck_data = normalize_deck(deck_data, topic_title)
    if not post_caption or len(post_caption.strip()) < 100:
        post_caption = (
            f"🧠 {topic_title.upper()}: АРХИВ СОВЕТСКОЙ НЕЙРОБИОЛОГИИ\n\n"
            f"После 35 лет нейроны префронтальной коры особенно чувствительны к микрососудистому спазму и дефициту АТФ. "
            f"В советском Академгородке и Институте мозга им. Бехтеревой эту проблему решали через естественные физиологические субстраты клеточного дыхания.\n\n"
            f"📌 В карусели — пошаговая доказательная схема из 3 шагов.\n\n"
            f"🎁 Полный 4-страничный PDF «Нейро-Стек: Управление префронтальной корой» с таблицами советских адаптогенов уже ждет в нашем Telegram-боте.\n\n"
            f"👉 Ссылка в шапке профиля или пиши кодовое слово НЕЙРО в комментарии — вышлем прямую ссылку в Директ за 5 секунд!\n\n"
            f"#нейробиология #мозг #сосуды #память #бехтерева #биохакинг #здоровье #продуктивность #концентрация"
        )

    return deck_data, topic_title, post_caption


def render_carousel_images(deck_data: Dict, output_dir: str) -> List[str]:
    """Рендерит слайды в формате Cyan Edition и сохраняет в output_dir."""
    gen = SpectrCarouselGenerator(theme="cyan")
    return gen.render_deck(deck_data, output_dir=output_dir)
