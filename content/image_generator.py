"""Генератор брендовых изображений для постов SpectrMind.

Поддерживает многоуровневый каскад генерации:
1. OpenAI DALL-E 3: ультра-реалистичные фото премиум-качества без водяных знаков (при наличии OPENAI_API_KEY).
2. Pollinations AI (FLUX.1): бесплатно или с Pollen API Key, прецизионное удаление водяного знака через Pillow.
3. Brand Fallback Assets: локальная библиотека брендовых фото в content/brand_assets.
   Если внешние сервисы временно недоступны или лимитированы, пост гарантированно выходит с соответствующим фото.

Стилистика (SpectrMind Visual DNA):
- Quiet luxury, минималистичная предметная и архитектурная фотография (стиль Kinfolk, Leica M11, Hasselblad).
- Натуральные текстуры: матовая керамика, темный сланец, копченое стекло, фактурная бумага, темное дерево, чистая вода.
- Chiaroscuro освещение: глубокие естественные тени, мягкий утренний свет из окна.
- Категорически БЕЗ неоновых мутаций, биолюминесценции, фантастических лабораторий и проводов.
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import re
import time
import urllib.parse
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "post_images"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

BRAND_ASSETS_DIR = Path(__file__).parent / "brand_assets"
BRAND_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Премиальный суффикс промпта: реальная журнальная фотография вместо sci-fi графики
BRAND_PROMPT_SUFFIX = (
    "editorial still-life photograph, quiet luxury, minimal dark aesthetic, "
    "natural dramatic morning chiaroscuro lighting, deep rich charcoal and obsidian tones, "
    "tactile textures, Leica M11 35mm f/1.4, shallow depth of field, award-winning architectural photography, "
    "ultra-photorealistic, 8k, elegant composition, Kinfolk style, no text, no watermark, no logos"
)

# Каталог тем постов и предметных визуалов (36 категорий реальных физических сцен)
THEME_MAPPINGS = [
    # 1. Шоколад / флавонолы / какао
    (
        r"(шоколад|какао|флавонол)",
        "artisan broken raw dark chocolate pieces on rough dark slate, roasted cacao beans, soft morning directional light, luxury macro still life",
    ),
    # 2. Холод / контрастный душ / крио / лед
    (
        r"(холод|душ|обливан|лед|крио|айс|моржеван|охлажден)",
        "minimalist dark granite cold plunge tub with crystal clear ice water, soft cool morning mist, luxury Nordic spa aesthetic, serene architectural photography",
    ),
    # 3. Сауна / тепловой шок
    (
        r"(саун|бан|пар|прогрев|тепловой шок)",
        "minimalist dark cedar sauna interior with dark stones, gentle warm steam, soft amber ambient light, Scandinavian luxury wellness",
    ),
    # 4. Кофе / кофеин / эспрессо / аденозин
    (
        r"(кофе|кофеин|чашк|эспрессо|аденозин)",
        "matte black ceramic cup of rich dark coffee on textured dark oak table, soft morning sunlight, long gentle shadows, minimalist editorial still-life",
    ),
    # 5. Чай / L-теанин / матча
    (
        r"(чай|зеленый чай|матча|теанин|настой)",
        "smoked glass teapot with dark steeped green tea on rough slate, delicate natural steam, Japanese wabi-sabi minimalism, soft natural lighting",
    ),
    # 6. Сон / циркадные ритмы / мелатонин / спальня / NSDR
    (
        r"(сон|ноч|мелатонин|nrem|nsdr|кроват|отдых|бессонниц|циркадн)",
        "luxury minimalist bedroom interior in deep shadows, textured dark charcoal linen bedding, soft warm ambient amber light glowing in the distance, peaceful stillness",
    ),
    # 7. Дыхание / легкие / 4-7-8 / box breathing / кислород
    (
        r"(дыхан|легк|4-7-8|box breath|вздох|кислород|гипервентил)",
        "abstract sculptural stone art piece symbolizing deep breath, smooth dark river stones, morning light, calm serene meditation studio",
    ),
    # 8. Помодоро / таймер / песочные часы / 25 минут / тайм-блоки
    (
        r"(помодоро|pomodoro|песочн|часы|25 минут|таймер|фокус-блок)",
        "sleek luxury hourglass crafted from smoked glass with fine dark sand, resting on a minimalist dark stone executive desk, crisp focus, soft side lighting",
    ),
    # 9. Дневник / фрирайтинг / записи перед сном / ручка
    (
        r"(дневник|фрирайтинг|ручк|бумаг|запис.*мысл|блокнот)",
        "open black leather-bound notebook and minimalist matte black fountain pen on dark oak desk, warm morning window rays, editorial still-life",
    ),
    # 10. Прогулка / лес / природа / шаги / шинрин-йоку
    (
        r"(прогулк|лес|природ|шаг|шинрин|ходьб|деревья)",
        "atmospheric misty forest at dawn, towering dark pine trees, soft golden sunbeams piercing through morning fog, contemplative 35mm landscape photography",
    ),
    # 11. Зрение / глаза / синий свет / экраны / 20-20-20
    (
        r"(зрени|глаз|синий свет|экран.*врем|20-20-20|очк|сетчатк)",
        "sleek minimalist black matte glasses resting on a dark slate surface beside an open book, soft warm reading lamp light, luxury optical still life",
    ),
    # 12. Музыка / звук / бинауральные ритмы / 40 Hz / наушники
    (
        r"(звук|музык|бинауральн|40 hz|моцарт|наушник|ритм|герц|акустик)",
        "matte black audiophile over-ear headphones resting on a sculptural dark wood stand, dark moody acoustic listening room, warm subtle accent light",
    ),
    # 13. Голодание / автофагия / метаболизм / митохондрии
    (
        r"(голодан|автофаг|метаболизм|митохондр|интервальн|фастинг)",
        "minimalist clear heavy crystal water carafe and glass on raw dark slate, clean reflection, morning sunlight, architectural still life",
    ),
    # 14. Кишечник / микробиом / ось кишечник-мозг
    (
        r"(кишечник|микробиом|ось|бактери|жкт)",
        "minimalist dark ceramic bowl with fresh fermented organic berries and clean wooden spoon on dark linen, natural soft light, tactile macro",
    ),
    # 15. БАДы / ноотропы / магний / креатин / капсулы / пептиды
    (
        r"(бад|пептид|добавк|ноотроп|таблетк|капсул|веществ|магний|креатин|омега|витамин|l-треонат)",
        "minimalist dark amber glass apothecary dropper bottle and sleek black capsules on textured slate, soft natural studio lighting, luxury wellness editorial",
    ),
    # 16. Тренировки / мышцы / BDNF / спорт / движение
    (
        r"(тренировк|мышц|bdnf|спорт|упражнен|приседан|бег|гир|гантел|физическ)",
        "minimalist matte black cast iron dumbbell on raw dark concrete floor, dramatic natural side light, quiet luxury fitness aesthetic",
    ),
    # 17. Смарт-кольцо / Oura / Whoop / пульс / HRV / трекер
    (
        r"(кольц|oura|whoop|трекер|пульс|hrv|вариабельн|гаджет)",
        "sleek black titanium smart ring resting on a dark basalt stone pedestal, soft natural rim light, macro product photography, crisp focus",
    ),
    # 18. Дофамин / смартфон / скролл / соцсети / зависимость
    (
        r"(дофамин|d1|d2|смартфон|скролл|экран|соцсет|уведомлен|тикток|рилс|прокрастинац)",
        "matte black smartphone face down on a dark textured wooden nightstand next to a warm dimmed reading lamp, peaceful disconnection",
    ),
    # 19. Префронтальная кора / фокус / внимание / решения
    (
        r"(префронтальн|кора|фокус|решени|внимани|концентр|halt|deep work)",
        "minimalist architectural sculpture of smooth dark marble and raw stone balancing gracefully, soft dramatic shadows, gallery aesthetic",
    ),
    # 20. Стресс / кортизол / тревога / амигдала / выгорание
    (
        r"(стресс|кортизол|амигдал|тревог|паник|выгоран|нервн)",
        "smooth dark river stones stacked in perfect zen balance on dark water surface with gentle ripples, peaceful serene atmosphere",
    ),
    # 21. Книги / чтение / память / обучение / нейропластичность
    (
        r"(книг|чтени|памят|обучен|нейропластичн|знани|библиотек)",
        "heavy open hardbound book with rich off-white textured paper on dark walnut library table, soft focused desk lamp lighting",
    ),
    # 22. Тишина / медитация / дзен / спокойствие
    (
        r"(тишин|медитац|дзен|спокойств|замедлен|осознан)",
        "minimalist Zen rock garden with smooth dark river stones, dark fine raked gravel, peaceful quiet luxury, serene morning shadows",
    ),
    # 23. Вода / гидратация / электролиты / стакан
    (
        r"(вод[аыеу]|гидратац|электролит|стакан|жажд|минерал)",
        "heavy smoked crystal tumbler filled with pure chilled water and a clear ice cube on dark slate, natural water drops, luxury editorial still-life",
    ),
    # 24. Энергия / усталость / батарея / митохондрии
    (
        r"(энерги|усталост|спад|истощен|батаре|бодрост)",
        "sleek minimalist architectural space with sunlight piercing deep darkness, clean geometric lines, quiet energizing atmosphere",
    ),
    # 25. Алкоголь / детокс / трезвость
    (
        r"(алкогол|вино|пиво|похмель|трезвост|печен)",
        "heavy cut-crystal tumbler with crystal-clear spherical ice on dark slate, dramatic high contrast luxury lighting",
    ),
    # 26. Осанка / эргономика / рабочее место / кресло
    (
        r"(осанк|позвоночник|кресл|рабоч.*стол|эргономик|офис)",
        "architectural dark minimalist executive workspace, sleek black oak desk, ergonomic silhouette, soft window light overlooking morning skyline",
    ),
    # 27. Neuralink / чип / нейроинтерфейс / ИИ
    (
        r"(neuralink|нейротех|чип|будущ|интерфейс|ии|кибернетик)",
        "sculptural precision titanium micro-device on textured dark stone pedestal, subtle macro details, luxury industrial design",
    ),
    # 28. Исследования / наука / лаборатория / ученые
    (
        r"(исследован|наук|лаборатор|учен|эксперимент|гарвард|стэнфорд)",
        "minimalist research studio with stacked architectural books and clean prism on dark slate, natural morning light, quiet intellectual study",
    ),
    # 29. Фаундеры / миллиардеры / лидеры / продуктивность
    (
        r"(маск|цукерберг|безос|альтман|хуберман|миллиардер|фаундер|лидер)",
        "solitary thinker silhouette in dark minimalist penthouse office at dawn, quiet contemplation, architectural luxury",
    ),
    # 30. Холодные руки / кисти рук
    (
        r"(холодн.*рук|кист.*рук|охлажден.*рук)",
        "hands warming around a hot dark ceramic mug on textured wooden table, soft morning window light, cozy quiet moment",
    ),
    # 31. Тайм-боксинг / календарь / расписание
    (
        r"(тайм-боксинг|календар|расписани|слот.*дня|планирован)",
        "minimalist black desk calendar and fountain pen on textured dark stone surface, clean geometric morning shadows",
    ),
    # 32. Питание / завтрак / нутриенты / глюкоза
    (
        r"(завтрак|питани|прием пищ|нутриент|глюкоз|сахар)",
        "minimalist luxury dark gastronomy still life on matte black ceramic plate, wholesome avocado and poached egg, soft natural morning light",
    ),
    # 33. Опрос / голосование / выбор
    (
        r"(опрос|выбор|дилемм|голосован)",
        "two elegant smooth dark stone pathways diverging on clean dark sand, subtle directional lighting, minimal zen landscape",
    ),
    # 34. Гипнагогия / метод Дали / тета-состояние
    (
        r"(гипнагоги|дали|тета|границ.*сна)",
        "surreal minimal architectural interior with gentle ambient dusk light casting long shadows across textured dark wall",
    ),
    # 35. Утро / пробуждение / рассвет
    (
        r"(утр[оа]|рассвет|пробужден)",
        "dark minimalist interior overlooking an early dawn horizon, soft first golden rays of sunlight illuminating a dark textured sill",
    ),
    # 36. Вечер / закат / вечерняя рефлексия
    (
        r"(вечер|закат|отход ко сну|рефлекси)",
        "dimly lit luxury living room with dark textured walls, warm glowing candle in a heavy glass holder, cozy deep shadows, serene evening calm",
    ),
]

# Эстетичный дефолтный предмет: минималистичный рабочий стол с блокнотом и ручкой
DEFAULT_SUBJECT = (
    "minimalist executive desk setup, premium matte black notebook and sleek fountain pen on textured dark stone surface, "
    "soft directional morning window light, clean geometric lines, tactile craftsmanship, quiet luxury"
)

# Соответствие тем для библиотеки резервных фото (brand assets)
FALLBACK_ASSET_MAPPINGS = [
    (r"(кофе|эспрессо|чай|аденозин)", "coffee.jpg"),
    (r"(фокус|таймер|песочн|внимани|работа|помодоро|deep work)", "focus.jpg"),
    (r"(сон|ноч|вечер|отдых|восстановлен|мелатонин)", "sleep.jpg"),
    (r"(утр|рассвет|пробужден|энерги|бодрост)", "morning.jpg"),
]


def build_theme_subject(text: str) -> str:
    """Определяет физический предмет для визуала на основе текста поста."""
    lowered = text.lower()
    for pattern, subject in THEME_MAPPINGS:
        if re.search(pattern, lowered):
            return subject
    return DEFAULT_SUBJECT


async def _generate_dynamic_subject(text: str) -> Optional[str]:
    """Быстрая попытка через LLM сформулировать точный предметный визуал под пост (таймаут 3.5с)."""
    try:
        from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_URL, PROXY_URL
        if not OPENROUTER_API_KEY:
            return None

        sys_prompt = (
            "You are a visual art director for SpectrMind, a luxury dark-aesthetic cognitive biohacking brand. "
            "Given a Russian post text, formulate a concrete physical object or architectural still-life scene for editorial photography. "
            "Rules:\n"
            "1. Real physical tactile objects only (e.g. matte black espresso cup on slate, cold plunge ice tub, dark amber apothecary bottle, hourglass with dark sand, leather journal with fountain pen, dumbbells on concrete).\n"
            "2. NEVER mention bioluminescence, sci-fi, glowing, futuristic, laboratory, neon, cyber, laser, cyborg, wires, or holographic.\n"
            "3. Focus on natural textures: matte ceramic, slate, smoked glass, dark wood, linen, clear water, stone.\n"
            "4. Output ONLY 1 short English phrase describing the subject (maximum 12 words), no quotes, no markdown."
        )
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": text[:400]},
            ],
            "temperature": 0.5,
            "max_tokens": 40,
        }
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://spectrmind.ru",
            "X-Title": "SpectrMind Bot",
        }
        async with httpx.AsyncClient(timeout=3.5, proxy=PROXY_URL or None) as client:
            resp = await client.post(OPENROUTER_URL, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                content = re.sub(r'["`*]', '', content).strip()
                # Фильтруем любые случайные sci-fi слова
                if any(bad in content.lower() for bad in ["bioluminescent", "neon", "cyber", "laboratory", "holographic"]):
                    return None
                if content and len(content) > 5 and not content.lower().startswith("error"):
                    return content
    except Exception as e:
        logger.debug("Dynamic LLM prompt generation skipped: %s", e)
    return None


def build_image_prompt(topic: str, content_type: str = "") -> str:
    """Синхронная сборка промпта через каталог тем."""
    subject = build_theme_subject(topic)
    return f"{subject}, {BRAND_PROMPT_SUFFIX}"


def get_brand_fallback_image(topic_or_text: str = "", content_type: str = "") -> Optional[str]:
    """Вернуть наиболее подходящее локальное изображение из библиотеки бренда (Zero-Fail)."""
    if not BRAND_ASSETS_DIR.exists():
        return None

    lowered = f"{topic_or_text} {content_type}".lower()
    for pattern, filename in FALLBACK_ASSET_MAPPINGS:
        if re.search(pattern, lowered):
            p = BRAND_ASSETS_DIR / filename
            if p.exists() and p.stat().st_size > 1000:
                logger.info("Using matching brand fallback image: %s", p.name)
                return str(p)

    # Если точного совпадения нет — берем любое доступное изображение из библиотеки
    existing = [p for p in BRAND_ASSETS_DIR.glob("*.jpg") if p.stat().st_size > 1000]
    if existing:
        chosen = random.choice(existing)
        logger.info("Using general brand fallback image: %s", chosen.name)
        return str(chosen)
    return None


async def _generate_openai_image(prompt: str) -> Optional[str]:
    """Генерация через OpenAI DALL-E 3 (премиум-качество, без водяных знаков)."""
    from config import OPENAI_API_KEY
    if not OPENAI_API_KEY:
        return None

    try:
        url = "https://api.openai.com/v1/images/generations"
        payload = {
            "model": "dall-e-3",
            "prompt": prompt[:950],
            "n": 1,
            "size": "1024x1024",
            "quality": "standard",
            "response_format": "url",
        }
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        logger.info("Generating post image via OpenAI DALL-E 3: %s...", prompt[:60])
        t0 = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                img_url = data["data"][0]["url"]
                img_resp = await client.get(img_url, timeout=30.0)
                if img_resp.status_code == 200 and len(img_resp.content) > 5000:
                    timestamp = int(time.time())
                    out_file = CACHE_DIR / f"post_dalle_{timestamp}.jpg"
                    with open(out_file, "wb") as f:
                        f.write(img_resp.content)
                    elapsed = round(time.time() - t0, 1)
                    logger.info("Image generated via OpenAI DALL-E 3 in %ss: %s", elapsed, out_file.name)
                    return str(out_file)
            else:
                logger.warning("OpenAI DALL-E 3 returned status %d: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.warning("OpenAI DALL-E 3 generation failed: %s", e)
    return None


async def _generate_pollinations_image(prompt: str, api_key: Optional[str] = None) -> Optional[str]:
    """Генерация через Pollinations AI (FLUX) с умным повтором и удалением водяного знака."""
    encoded_prompt = urllib.parse.quote(prompt)
    resolutions = [768, 512]

    for res in resolutions:
        for attempt in range(2):
            seed = random.randint(10000, 999999)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={res}&height={res}&model=flux&seed={seed}"
            if api_key:
                url += f"&key={urllib.parse.quote(api_key)}"

            timestamp = int(time.time())
            out_file = CACHE_DIR / f"post_{timestamp}_{seed}.jpg"
            logger.info("Generating via Pollinations FLUX (%dx%d, attempt %d): %s...", res, res, attempt + 1, prompt[:60])
            t0 = time.time()

            try:
                headers = {"User-Agent": "SpectrMindBot/1.0"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
                    resp = await client.get(url, headers=headers)

                    if resp.status_code == 200 and len(resp.content) > 5000:
                        with open(out_file, "wb") as f:
                            f.write(resp.content)

                        # Кроп нижнего водяного знака pollinations.ai (70-80px снизу)
                        try:
                            from PIL import Image
                            with Image.open(out_file) as img:
                                w, h = img.size
                                if h > 100:
                                    crop_bottom = max(70, int(h * 0.08))
                                    clean_img = img.crop((0, 0, w, h - crop_bottom))
                                    clean_img.save(out_file, quality=95)
                        except ImportError:
                            logger.error("CRITICAL: Pillow is not installed on server! Run: pip install pillow")
                        except Exception as e_crop:
                            logger.warning("Could not crop watermark: %s", e_crop)

                        elapsed = round(time.time() - t0, 1)
                        logger.info("Image successfully generated in %ss (%d bytes, cropped): %s", elapsed, len(resp.content), out_file.name)
                        return str(out_file)

                    elif resp.status_code == 402:
                        # Лимит 1 запрос в 45 сек на IP: парсим точное время паузы и ждём
                        body = resp.text
                        m = re.search(r"Retry after (\d+)s", body)
                        wait_sec = min(int(m.group(1)) + 1, 46) if m else 30
                        logger.warning("Pollinations 402 rate-limit hit. Waiting %ds before retry...", wait_sec)
                        if attempt == 0:
                            await asyncio.sleep(wait_sec)
                            continue
                    else:
                        logger.warning("Pollinations returned status %s (%d bytes)", resp.status_code, len(resp.content))
                        break  # переходим к следующему разрешению/попытке
            except Exception as e:
                logger.warning("Pollinations attempt %d failed (%s)", attempt + 1, e)
                break

    return None


async def generate_post_image(topic_or_text: str, content_type: str = "") -> Optional[str]:
    """Сгенерировать и сохранить изображение для поста SpectrMind.

    Каскадная стратегия:
    1. Формирование реалистичного промпта (динамический LLM-анализ или каталог тем).
    2. Попытка через OpenAI DALL-E 3 (если задан OPENAI_API_KEY).
    3. Попытка через Pollinations FLUX (с Pollen Key или бесплатный каскад).
    4. При любых сетевых сбоях — локальный fallback из библиотеки brand_assets (100% гарантия).
    """
    from config import IMAGE_PROVIDER, OPENAI_API_KEY, POLLEN_API_KEY

    # 1. Формируем предмет для съемки
    subject = await _generate_dynamic_subject(topic_or_text)
    if not subject:
        subject = build_theme_subject(topic_or_text)

    prompt = f"{subject}, {BRAND_PROMPT_SUFFIX}"

    image_path = None

    # 2. Попытка генерации через OpenAI DALL-E 3 (если включено или доступен ключ)
    if OPENAI_API_KEY and IMAGE_PROVIDER in ("auto", "openai"):
        image_path = await _generate_openai_image(prompt)
        if image_path:
            _cleanup_old_images()
            return image_path

    # 3. Попытка через Pollinations (с Pollen API Key или бесплатно)
    if not image_path and IMAGE_PROVIDER in ("auto", "pollen", "pollinations"):
        image_path = await _generate_pollinations_image(prompt, api_key=POLLEN_API_KEY or None)
        if image_path:
            _cleanup_old_images()
            return image_path

    # 4. Zero-Fail Fallback: достаем подходящее изображение из библиотеки бренда
    logger.warning("Online generation unavailable. Activating brand fallback image...")
    fallback_path = get_brand_fallback_image(topic_or_text, content_type)
    if fallback_path:
        return fallback_path

    logger.error("All image generation strategies exhausted, including fallback")
    return None


def _cleanup_old_images(max_age_days: int = 3) -> None:
    """Удалить старые временные картинки, чтобы не засорять диск."""
    try:
        now = time.time()
        max_age_sec = max_age_days * 86400
        for p in CACHE_DIR.glob("post_*.jpg"):
            if now - p.stat().st_mtime > max_age_sec:
                try:
                    p.unlink()
                except OSError:
                    pass
    except Exception:
        pass
