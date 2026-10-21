"""Генератор брендовых изображений для постов SpectrMind.

Использует Pollinations AI (модель FLUX.1):
- 100% бесплатно, без ключей API, без ограничений.
- Brand DNA: Dark obsidian, neon cyan bioluminescence, 35mm cinematic photograph, 8k.
- Graceful fallback: если сервис недоступен или таймаут, возвращает None, и пост уходит текстом без ошибок.
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
    "dark obsidian futuristic cognitive laboratory, deep space background, "
    "subtle glowing neon cyan neural synaptic connections, "
    "hyperrealistic, high contrast, deep blacks, award winning photography, "
    "8k, volumetric lighting, photorealistic, no text, no watermark, no logo"
)

# Шаблоны визуалов под ключевые слова тем
THEME_MAPPINGS = [
    (
        r"(дофамин|d1|d2|смартфон|скролл|тихий|яма)",
        "human profile silhouette contemplating smartphone screen with glowing cyan dopamine neural synaptic pathways branching in brain, dark futuristic obsidian room",
    ),
    (
        r"(сон|ноч|мелатонин|nrem|аденозин|утро|пробужден|кроват|отдых)",
        "futuristic cognitive sleep optimization pod, peaceful human resting in dark obsidian chamber with soft glowing cyan bioluminescent dust particles, deep recovery",
    ),
    (
        r"(кофе|кофеин|чашк|напиток|бодрост)",
        "sleek black glass cup with dark espresso on black reflective obsidian surface, glowing cyan synaptic energy mist rising, cinematic macro luxury photography",
    ),
    (
        r"(префронтальн|кора|фокус|решени|внимани|концентр|halt)",
        "close-up profile portrait of focused thinker with holographic cyan neural mapping of prefrontal cortex, dark sleek high-tech laboratory",
    ),
    (
        r"(бад|пептид|добавк|ноотроп|таблетк|капсул|веществ)",
        "minimalist dark obsidian cognitive laboratory, amber glass vials with glowing cyan liquid, high-end biohacking aesthetics, sleek dark lighting",
    ),
    (
        r"(стресс|кортизол|амигдал|тревог|паник|пульс)",
        "abstract human brain with glowing violet and cyan neural pulses, neurobiology of emotional regulation, dark deep obsidian background",
    ),
    (
        r"(исследован|наук|лаборатор|учен|эксперимент)",
        "high-tech neuro-research holographic data visualization of synaptic plasticity, dark minimalist laboratory room, neon cyan glow",
    ),
    (
        r"(neuralink|нейротех|чип|будущ|интерфейс|ии)",
        "futuristic minimal neural interface implant on human temple with glowing micro cyan circuit threads, dark cyberpunk luxury minimalism",
    ),
    (
        r"(маск|цукерберг|безос|альтман|хуберман|миллиардер)",
        "silhouetted high performer working in dark minimalist high-tech office overlooking night skyline, holographic brain analytics, luxury cinematic",
    ),
]


def build_image_prompt(topic: str, content_type: str = "") -> str:
    """Создает английский промпт на основе темы и Brand DNA."""
    lowered = topic.lower()
    subject = None

    for pattern, prompt_subject in THEME_MAPPINGS:
        if re.search(pattern, lowered):
            subject = prompt_subject
            break

    if not subject:
        subject = (
            "futuristic human head with luminous cyan neural network and synaptic pathways, "
            "minimalist dark obsidian cognitive laboratory"
        )

    return f"{subject}, {BRAND_PROMPT_SUFFIX}"


async def generate_post_image(topic: str, content_type: str = "") -> Optional[str]:
    """Сгенерировать и сохранить картинку для поста через Pollinations Flux.

    Возвращает путь к сохраненному файлу или None при ошибке/таймауте.
    """
    prompt = build_image_prompt(topic, content_type)
    encoded_prompt = urllib.parse.quote(prompt)
    seed = random.randint(10000, 999999)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true&seed={seed}"

    timestamp = int(time.time())
    out_file = CACHE_DIR / f"post_{timestamp}_{seed}.jpg"

    logger.info("Generating post image via Pollinations Flux: %s...", prompt[:60])
    t0 = time.time()

    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "SpectrMindBot/1.0"})
            if resp.status_code == 200 and len(resp.content) > 5000:
                with open(out_file, "wb") as f:
                    f.write(resp.content)
                elapsed = round(time.time() - t0, 1)
                logger.info("Image successfully generated in %ss (%d bytes): %s", elapsed, len(resp.content), out_file.name)
                _cleanup_old_images()
                return str(out_file)
            else:
                logger.warning("Pollinations returned status %s or small content: %d bytes", resp.status_code, len(resp.content))
                return None
    except Exception as e:
        logger.warning("Failed to generate image via Pollinations (will post text-only): %s", e)
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
