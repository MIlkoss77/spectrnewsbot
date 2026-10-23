"""Генератор брендовых изображений для постов SpectrMind.

Использует Pollinations AI (модель FLUX.1):
- 100% бесплатно, без ключей API, без ограничений.
- Brand DNA: Dark obsidian, neon cyan bioluminescence, 35mm cinematic photograph, 8k.
- Интеллектуальный подбор визуала: динамическая генерация объекта через LLM + каталог из 35+ нейро-тем.
- 100% удаление водяных знаков: прецизионный кроп нижнего колонтитула (70-80px).
- Graceful fallback: если сервис недоступен или таймаут, возвращает None, и пост уходит текстом без задержек.
"""
from __future__ import annotations

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

# Базовый брендовый суффикс промпта (SpectrMind Brand DNA)
BRAND_PROMPT_SUFFIX = (
    "cinematic 35mm photograph, luxury commercial quality, "
    "dark obsidian futuristic cognitive laboratory aesthetic, "
    "subtle glowing neon cyan bioluminescent accents, "
    "hyperrealistic, high contrast, deep blacks, award winning photography, "
    "8k, volumetric lighting, photorealistic, no text, no watermark, no logo"
)

# Исчерпывающий каталог тем постов и соответствующих предметных визуалов (35+ категорий)
THEME_MAPPINGS = [
    # 1. Шоколад / флавонолы / какао
    (
        r"(шоколад|какао|флавонол)",
        "artisan broken raw dark obsidian chocolate pieces on rough slate surface, roasted cacao beans, subtle neon cyan organic dust particles, dramatic luxury chiaroscuro lighting",
    ),
    # 2. Холод / контрастный душ / крио / лед
    (
        r"(холод|душ|обливан|лед|крио|айс|моржеван|охлажден)",
        "minimalist matte black luxury cold plunge tub surrounded by wet obsidian stone, pure clear icy water with subtle cyan bioluminescent reflections, cool misty vapor, cinematic macro photography",
    ),
    # 3. Сауна / тепловой шок
    (
        r"(саун|бан|пар|прогрев|тепловой шок)",
        "minimalist luxury dark cedar sauna interior with obsidian stone heater, subtle glowing cyan mist and steam rising in low-angle dramatic ambient lighting",
    ),
    # 4. Кофе / кофеин / эспрессо / аденозин
    (
        r"(кофе|кофеин|чашк|эспрессо|аденозин)",
        "sleek black ceramic cup with dark crema espresso on black reflective obsidian surface, subtle glowing cyan synaptic energy steam rising, cinematic macro photography",
    ),
    # 5. Чай / L-теанин / матча
    (
        r"(чай|зеленый чай|матча|теанин|настой)",
        "minimalist smoked glass teapot with dark infused tea on black slate, delicate cyan bioluminescent vapor rising, Japanese luxury minimalism",
    ),
    # 6. Сон / циркадные ритмы / мелатонин / спальня / NSDR
    (
        r"(сон|ноч|мелатонин|nrem|nsdr|кроват|отдых|бессонниц|циркадн)",
        "futuristic luxury circadian sleep sanctuary, dark obsidian sleeping pod with soft glowing cyan bioluminescent dust particles, calm deep regenerative atmosphere",
    ),
    # 7. Дыхание / легкие / 4-7-8 / box breathing / кислород
    (
        r"(дыхан|легк|4-7-8|box breath|вздох|кислород|гипервентил)",
        "abstract sculptural human silhouette in deep meditation with luminous neon cyan airflow and oxygen pathways glowing through chest, dark obsidian chamber",
    ),
    # 8. Помодоро / таймер / песочные часы / 25 минут / тайм-блоки
    (
        r"(помодоро|pomodoro|песочн|часы|25 минут|таймер|фокус-блок)",
        "sleek luxury hourglass crafted from smoked black crystal on dark obsidian desk, luminous cyan sand particles trickling down, high-end desk aesthetic, cinematic lighting",
    ),
    # 9. Дневник / фрирайтинг / записи перед сном / ручка
    (
        r"(дневник|фрирайтинг|ручк|бумаг|запис.*мысл|блокнот)",
        "luxurious black leather journal open on dark obsidian desk next to a minimal matte black fountain pen, subtle cyan glowing holographic text lines floating above the page",
    ),
    # 10. Прогулка / лес / природа / шаги / шинрин-йоку
    (
        r"(прогулк|лес|природ|шаг|шинрин|ходьб|деревья)",
        "serene misty nocturnal forest with dark towering trees, soft moonlight and luminous cyan bioluminescent flora glowing along a dark stone path, meditative 35mm photograph",
    ),
    # 11. Зрение / глаза / синий свет / экраны / 20-20-20
    (
        r"(зрени|глаз|синий свет|экран.*врем|20-20-20|очк|сетчатк)",
        "minimalist sleek black titanium spectacles resting on a dark obsidian surface beside a glowing geometric cyan light aperture, dramatic luxury optical still life",
    ),
    # 12. Музыка / звук / бинауральные ритмы / 40 Hz / наушники
    (
        r"(звук|музык|бинауральн|40 hz|моцарт|наушник|ритм|герц|акустик)",
        "matte black audiophile over-ear headphones on a sculptural obsidian stand, subtle luminous cyan acoustic soundwaves floating through dark atmospheric mist",
    ),
    # 13. Голодание / автофагия / метаболизм / митохондрии
    (
        r"(голодан|автофаг|метаболизм|митохондр|интервальн|фастинг)",
        "hyperrealistic visual metaphor of cellular autophagy, dark obsidian crystalline cell structure purifying with glowing cyan and emerald energy core, luxury science visualization",
    ),
    # 14. Кишечник / микробиом / ось кишечник-мозг
    (
        r"(кишечник|микробиом|ось|бактери|жкт)",
        "abstract luxury visualization of the gut-brain axis, glowing cyan neural threads connecting luminous biological nodes, deep obsidian space background",
    ),
    # 15. БАДы / ноотропы / магний / креатин / капсулы / пептиды
    (
        r"(бад|пептид|добавк|ноотроп|таблетк|капсул|веществ|магний|креатин|омега|витамин|l-треонат)",
        "minimalist dark amber glass apothecary dropper bottle and sleek black matte capsules arranged on reflective obsidian stone, faint cyan bioluminescent aura",
    ),
    # 16. Тренировки / мышцы / BDNF / спорт / движение
    (
        r"(тренировк|мышц|bdnf|спорт|упражнен|приседан|бег|гир|гантел|физическ)",
        "matte black minimalist dumbbell and biometric grip on textured obsidian floor, subtle neon cyan kinetic energy lines radiating, luxury fitness photography",
    ),
    # 17. Смарт-кольцо / Oura / Whoop / пульс / HRV / трекер
    (
        r"(кольц|oura|whoop|трекер|пульс|hrv|вариабельн|гаджет)",
        "sleek black titanium smart ring resting on a dark obsidian pedestal, subtle glowing cyan biometric pulse sensor illuminating the stone, luxury tech macro",
    ),
    # 18. Дофамин / смартфон / скролл / соцсети / зависимость
    (
        r"(дофамин|d1|d2|смартфон|скролл|экран|соцсет|уведомлен|тикток|рилс|прокрастинац)",
        "human silhouette contemplating edge-to-edge dark obsidian smartphone screen with subtle luminous cyan synaptic neural sparks branching from fingertips into deep darkness",
    ),
    # 19. Префронтальная кора / фокус / внимание / решения
    (
        r"(префронтальн|кора|фокус|решени|внимани|концентр|halt|deep work)",
        "sculptural profile bust of a human head sculpted from dark polished obsidian, with an intricately glowing cyan geometric neural nexus inside the frontal lobe",
    ),
    # 20. Стресс / кортизол / тревога / амигдала / выгорание
    (
        r"(стресс|кортизол|амигдал|тревог|паник|выгоран|нервн)",
        "abstract conceptual sculpture of emotional equilibrium: dark textured obsidian rock balancing serenely amidst glowing violet and calm cyan synaptic ripples",
    ),
    # 21. Книги / чтение / память / обучение / нейропластичность
    (
        r"(книг|чтени|памят|обучен|нейропластичн|знани|библиотек)",
        "open luxury black leather-bound volume on dark obsidian desk, subtle luminous cyan synaptic branches growing from the pages like knowledge trees, cinematic macro",
    ),
    # 22. Тишина / медитация / дзен / спокойствие
    (
        r"(тишин|медитац|дзен|спокойств|замедлен|осознан)",
        "minimalist Zen rock garden with smooth dark obsidian stones, concentric raked dark sand, glowing faint cyan aura of pure mental stillness",
    ),
    # 23. Вода / гидратация / электролиты / стакан
    (
        r"(вод[аыеу]|гидратац|электролит|стакан|жажд|минерал)",
        "heavy smoked crystal tumbler filled with pure mineral water and clear ice cube on black obsidian surface, luminous cyan refractions, luxury commercial still life",
    ),
    # 24. Энергия / усталость / батарея / митохондрии
    (
        r"(энерги|усталост|спад|истощен|батаре|бодрост)",
        "abstract obsidian energy monolith holding a glowing cyan plasma core, symbolic representation of cellular mitochondrial vitality, deep contrast",
    ),
    # 25. Алкоголь / детокс / трезвость
    (
        r"(алкогол|вино|пиво|похмель|трезвост|печен)",
        "heavy black cut-crystal tumbler with crystal-clear spherical ice on dark obsidian slate, dramatic high contrast luxury lighting",
    ),
    # 26. Осанка / эргономика / рабочее место / кресло
    (
        r"(осанк|позвоночник|кресл|рабоч.*стол|эргономик|офис)",
        "architectural dark minimalist executive workspace, sleek obsidian desk, soft atmospheric cyan ambient rim lighting overlooking nocturnal city",
    ),
    # 27. Neuralink / чип / нейроинтерфейс / ИИ
    (
        r"(neuralink|нейротех|чип|будущ|интерфейс|ии|кибернетик)",
        "futuristic minimal neural interface micro-component on human temple with glowing micro cyan circuit threads, dark cyberpunk luxury minimalism",
    ),
    # 28. Исследования / наука / лаборатория / ученые
    (
        r"(исследован|наук|лаборатор|учен|эксперимент|гарвард|стэнфорд)",
        "high-tech neuro-research holographic data visualization of synaptic plasticity, dark minimalist laboratory room, neon cyan glow",
    ),
    # 29. Фаундеры / миллиардеры / лидеры / продуктивность
    (
        r"(маск|цукерберг|безос|альтман|хуберман|миллиардер|фаундер|лидер)",
        "silhouetted high performer working in dark minimalist high-tech office overlooking night skyline, holographic brain analytics, luxury cinematic",
    ),
    # 30. Холодные руки / кисти рук
    (
        r"(холодн.*рук|кист.*рук|охлажден.*рук)",
        "human hands submerged in crystal clear icy water in a dark volcanic obsidian bowl, soft cyan bioluminescent glow around fingertips",
    ),
    # 31. Тайм-боксинг / календарь / расписание
    (
        r"(тайм-боксинг|календар|расписани|слот.*дня|планирован)",
        "holographic minimalist dark scheduling grid floating above an obsidian executive desk, illuminated in elegant neon cyan lines",
    ),
    # 32. Питание / завтрак / нутриенты / глюкоза
    (
        r"(завтрак|питани|прием пищ|нутриент|глюкоз|сахар)",
        "minimalist luxury dark gastronomy still life on matte black ceramics, nutrient-dense organic foods with dramatic cyan accent shadows",
    ),
    # 33. Опрос / голосование / выбор
    (
        r"(опрос|выбор|дилемм|голосован)",
        "two divergent pathways made of polished obsidian stones glowing with subtle cyan and amber luminescence in a dark misty space",
    ),
    # 34. Гипнагогия / метод Дали / тета-состояние
    (
        r"(гипнагоги|дали|тета|границ.*сна)",
        "surreal luxury conceptual art piece with floating obsidian geometric forms suspended in dark atmospheric space, glowing cyan synaptic sparks",
    ),
    # 35. Утро / пробуждение / рассвет
    (
        r"(утр[оа]|рассвет|пробужден)",
        "dark obsidian balcony overlooking early dawn horizon with first subtle rays of morning cyan-gold ambient light piercing the shadows",
    ),
    # 36. Вечер / закат / вечерняя рефлексия
    (
        r"(вечер|закат|отход ко сну|рефлекси)",
        "dim luxury interior with dark textured obsidian walls, soft warm amber and deep cyan low-angle night lighting, peaceful serenity",
    ),
]

# Элегантный fallback — эстетическая когнитивная скульптура (вместо странных голов с проводами)
DEFAULT_SUBJECT = (
    "sleek abstract cognitive sculpture crafted from polished dark obsidian and raw crystalline stone, "
    "subtle glowing neon cyan synaptic threads weaving through cracks, dramatic atmospheric chiaroscuro lighting, luxury high-tech boardroom art piece"
)


def build_theme_subject(text: str) -> str:
    """Определяет физический предмет для визуала на основе текста поста."""
    lowered = text.lower()
    for pattern, subject in THEME_MAPPINGS:
        if re.search(pattern, lowered):
            return subject
    return DEFAULT_SUBJECT


async def _generate_dynamic_subject(text: str) -> Optional[str]:
    """Быстрая попытка через LLM сформулировать точный визуал под пост (таймаут 3.5с)."""
    try:
        from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_URL, PROXY_URL
        if not OPENROUTER_API_KEY:
            return None

        sys_prompt = (
            "You are a visual art director for SpectrMind, a luxury dark-aesthetic cognitive biohacking brand. "
            "Given a Russian post text, extract the core physical object or still-life scene for Flux AI. "
            "Rules:\n"
            "1. Concrete real-world physical object (e.g., broken artisan dark chocolate on slate, cold plunge ice tub, matte black espresso cup, hourglass with black sand, smart ring on obsidian pedestal, leather journal with fountain pen).\n"
            "2. NO text, NO letters, NO words in the image.\n"
            "3. Dark luxury obsidian aesthetic, subtle cyan bioluminescent accents, 35mm macro.\n"
            "4. Output ONLY 1 short English phrase describing the subject (maximum 15 words), nothing else."
        )
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": text[:400]},
            ],
            "temperature": 0.6,
            "max_tokens": 50,
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
                if content and len(content) > 5 and not content.lower().startswith("error"):
                    return content
    except Exception as e:
        logger.debug("Dynamic LLM prompt generation skipped: %s", e)
    return None


def build_image_prompt(topic: str, content_type: str = "") -> str:
    """Синхронная сборка промпта через каталог тем."""
    subject = build_theme_subject(topic)
    return f"{subject}, {BRAND_PROMPT_SUFFIX}"


async def generate_post_image(topic_or_text: str, content_type: str = "") -> Optional[str]:
    """Сгенерировать и сохранить картинку для поста через Pollinations AI.

    Особенности:
    - Двухуровневый каскад: сначала FLUX (быстрые 768x768), при сбое/таймауте — моментальный TURBO.
    - Автоматическая обработка лимита 402 (FREE_LIMIT): парсит время паузы и повторяет запрос.
    - Таймаут 45с для Flux и 20с для Turbo.
    - Кроп водяного знака снизу через Pillow.
    - При абсолютном сбое возвращает None (пост уходит текстом без падений).
    """
    import asyncio

    # 1. Сначала пробуем динамический подбор через LLM; если недоступен — используем каталог тем
    subject = await _generate_dynamic_subject(topic_or_text)
    if not subject:
        subject = build_theme_subject(topic_or_text)

    prompt = f"{subject}, {BRAND_PROMPT_SUFFIX}"
    encoded_prompt = urllib.parse.quote(prompt)

    models_to_try = [
        ("flux", 45.0),
        ("turbo", 20.0),
    ]

    for model_name, req_timeout in models_to_try:
        for attempt in range(2):
            seed = random.randint(10000, 999999)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=768&model={model_name}&seed={seed}"
            timestamp = int(time.time())
            out_file = CACHE_DIR / f"post_{timestamp}_{seed}.jpg"

            logger.info("Generating post image via Pollinations (%s, attempt %d): %s...", model_name, attempt + 1, prompt[:60])
            t0 = time.time()

            try:
                async with httpx.AsyncClient(timeout=req_timeout, follow_redirects=True) as client:
                    resp = await client.get(url, headers={"User-Agent": "SpectrMindBot/1.0"})

                    if resp.status_code == 200 and len(resp.content) > 5000:
                        with open(out_file, "wb") as f:
                            f.write(resp.content)

                        # Безупречная чистота: срезаем нижний водяной знак pollinations.ai (70-80px снизу)
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
                        logger.info("Image successfully generated in %ss (%d bytes, watermark cleanly removed via %s): %s", elapsed, len(resp.content), model_name, out_file.name)
                        _cleanup_old_images()
                        return str(out_file)

                    elif resp.status_code == 402:
                        # Лимит 1 запрос в 45 сек на IP: парсим точное время паузы и ждём
                        body = resp.text
                        m = re.search(r"Retry after (\d+)s", body)
                        wait_sec = min(int(m.group(1)) + 1, 46) if m else 30
                        logger.warning("Pollinations 402 rate-limit hit (%s). Waiting %ds before retry...", model_name, wait_sec)
                        if attempt == 0:
                            await asyncio.sleep(wait_sec)
                            continue
                    else:
                        logger.warning("Pollinations (%s) returned status %s (%d bytes)", model_name, resp.status_code, len(resp.content))
                        break  # переходим к резервной модели turbo
            except Exception as e:
                logger.warning("Pollinations (%s) attempt %d failed (%s)", model_name, attempt + 1, e)
                break  # переходим к следующей модели

    logger.error("All image generation attempts exhausted via Pollinations, posting text-only")
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
