#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SPECTR MIND — Генератор брендированных Instagram-каруселей (1080x1350, 4:5)
Стилистика:
  1. 'journal' — Глянцевый нейрожурнал (Dark Editorial / A24 / Chiaroscuro / Film Grain)
  2. 'clinic'  — Рассылка премиальной нейроклиники (Swiss Clinical Grid / Dossier / EEG Waveforms)

Использование из командной строки:
  python spectr_carousel_generator.py \
      --font-primary path/to/HeadingFont.ttf \
      --font-secondary path/to/BodyFont.ttf \
      --theme clinic \
      --input slides.json \
      --output ./out_slides

Использование внутри Python / Telegram-бота (spectrmind-bot):
  from spectr_carousel_generator import SpectrCarouselGenerator
  gen = SpectrCarouselGenerator(
      font_primary="fonts/CormorantGaramond-Bold.ttf",
      font_secondary="fonts/Inter-Regular.ttf",
      theme="journal"
  )
  files = gen.render_deck(deck_data, output_dir="./output")
"""

import os
import re
import math
import json
import random
import argparse
from typing import List, Dict, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# ==============================================================================
# ЦВЕТОВЫЕ ПАЛИТРЫ И ТЕМЫ (SPECTR MIND VISUAL IDENTITY)
# ==============================================================================
THEMES = {
    "cyan": {
        "name": "SPECTR NEURO-CYAN // CLINICAL DOSSIER",
        "bg_base": (2, 12, 22),           # Глубокий полуночный обсидиан / темный индиго
        "bg_Card": (7, 24, 38),           # Плашка досье / темное циановое стекло
        "bg_card": (7, 24, 38),           # Алиас для совместимости
        "glow_primary": (0, 215, 255),    # Неоновый биолюминесцентный циан (#00E5FF)
        "glow_secondary": (0, 135, 195),  # Глубокий лазурный свет
        "text_main": (245, 250, 255),     # Ледяной белый (максимальный контраст и четкость)
        "text_muted": (142, 182, 206),    # Холодный лабораторный серебристо-голубой
        "accent": (0, 229, 255),          # Фирменный #00E5FF Electric Cyan
        "accent_bg": (10, 48, 72),        # Выделитель протокола / фон плашек
        "border": (20, 68, 96),           # Линии швейцарской модульной сетки
        "grid_line": (8, 26, 38),         # Миллиметровая сетка клиники
        "badge_bg": (6, 34, 52),
        "badge_fg": (0, 229, 255),
        "button_bg": (0, 229, 255),
        "button_fg": (2, 12, 22),         # Темный обсидиан на неоновой кнопке
        "grain_intensity": 5,
        "is_dark": True,
    },
    "journal": {
        "name": "NEURO JOURNAL // DARK EDITORIAL",
        "bg_base": (10, 11, 14),           # Глубокий обсидиан
        "bg_Card": (18, 20, 26),           # Карточка / вставка
        "bg_card": (18, 20, 26),
        "glow_primary": (212, 145, 74),    # Теплый янтарный свет (Chiaroscuro)
        "glow_secondary": (64, 110, 142),  # Холодный лабораторный циан
        "text_main": (242, 239, 233),      # Теплый журнальный белый
        "text_muted": (148, 152, 161),     # Приглушенный серо-стальной
        "accent": (229, 169, 92),          # Золотисто-янтарный акцент
        "accent_bg": (45, 34, 22),         # Плашка под акцент
        "border": (48, 52, 62),            # Тонкие журнальные линии
        "grid_line": (22, 25, 32),         # Фоновая миллиметровка
        "badge_bg": (28, 31, 38),
        "badge_fg": (229, 169, 92),
        "button_bg": (229, 169, 92),
        "button_fg": (10, 11, 14),
        "grain_intensity": 10,
        "is_dark": True,
    },
    "clinic": {
        "name": "PREMIUM NEURO-CLINIC // SWISS DISPATCH",
        "bg_base": (244, 241, 234),        # Стерильная архивная бумага / молочный кварц
        "bg_Card": (235, 231, 222),        # Плашка досье
        "bg_card": (235, 231, 222),
        "glow_primary": (215, 208, 195),   # Мягкий градиент бумаги
        "glow_secondary": (225, 220, 210),
        "text_main": (17, 19, 23),         # Глубокий графит / типографская краска
        "text_muted": (102, 106, 115),     # Лабораторный серый
        "accent": (196, 54, 38),           # Медицинский киноварь / био-маркер
        "accent_bg": (238, 214, 208),      # Выделитель протокола
        "border": (198, 193, 182),         # Линии швейцарской модульной сетки
        "grid_line": (232, 228, 219),      # Миллиметровая сетка клиники
        "badge_bg": (17, 19, 23),
        "badge_fg": (244, 241, 234),
        "button_bg": (196, 54, 38),
        "button_fg": (244, 241, 234),
        "grain_intensity": 6,
        "is_dark": False,
    }
}


class SpectrCarouselGenerator:
    """
    Движок рендеринга каруселей для Instagram (1080x1350px).
    Принимает основной (font_primary) и дополнительный (font_secondary) шрифты.
    """

    WIDTH = 1080
    HEIGHT = 1350
    MARGIN_X = 76
    MARGIN_TOP = 72
    MARGIN_BOTTOM = 76

    def __init__(
        self,
        font_primary: Optional[str] = None,
        font_secondary: Optional[str] = None,
        font_mono: Optional[str] = None,
        theme: str = "cyan",
        brand_handle: str = "@SPECTRMIND.RU",
        brand_domain: str = "SPECTRMIND.RU",
        bot_handle: str = "@SPECTRNEWSBOT",
    ):
        self.theme_key = theme if theme in THEMES else "cyan"
        self.palette = THEMES[self.theme_key]
        self.brand_handle = brand_handle
        self.brand_domain = brand_domain
        self.bot_handle = bot_handle

        self.font_primary_path = self._resolve_font(font_primary, role="primary")
        self.font_secondary_path = self._resolve_font(font_secondary, role="secondary")
        self.font_mono_path = self._resolve_font(font_mono, role="mono")

    # --------------------------------------------------------------------------
    # РАБОТА СО ШРИФТАМИ
    # --------------------------------------------------------------------------
    def _resolve_font(self, custom_path: Optional[str], role: str = "primary") -> str:
        """Проверяет переданный путь к шрифту или подбирает системный с кириллицей."""
        if custom_path and os.path.isfile(custom_path):
            return custom_path

        candidates = {
            "primary": [
                "/usr/share/fonts/truetype/noto/NotoSerifDisplay-CondensedExtraBold.ttf",
                "/usr/share/fonts/truetype/noto/NotoSerifDisplay-ExtraCondensedBold.ttf",
                "/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                "C:/Windows/Fonts/georgia.ttf",
                "C:/Windows/Fonts/timesbd.ttf",
            ],
            "secondary": [
                "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
                "/usr/share/fonts/truetype/noto/NotoSans-SemiCondensedBold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "C:/Windows/Fonts/segoeui.ttf",
                "C:/Windows/Fonts/arial.ttf",
            ],
            "mono": [
                "/usr/share/fonts/truetype/noto/NotoSansMono-SemiCondensedExtraBold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                "C:/Windows/Fonts/consola.ttf",
            ],
        }

        for path in candidates.get(role, []):
            if os.path.isfile(path):
                return path

        for root_dir in ["/usr/share/fonts", "C:/Windows/Fonts"]:
            if os.path.isdir(root_dir):
                for r, _, files in os.walk(root_dir):
                    for f in files:
                        if f.lower().endswith(".ttf"):
                            return os.path.join(r, f)
        return ""

    def _font(self, role: str, size: int) -> ImageFont.FreeTypeFont:
        path = {
            "primary": self.font_primary_path,
            "secondary": self.font_secondary_path,
            "mono": self.font_mono_path,
        }.get(role, self.font_secondary_path)
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            return ImageFont.load_default()

    # --------------------------------------------------------------------------
    # ГЕНЕРАЦИЯ ФОНА, СВЕТА CHIAROSCURO, СЕТКИ И ПЛЕНОЧНОГО ЗЕРНА
    # --------------------------------------------------------------------------
    def _create_canvas(self, slide_idx: int, bg_image_path: Optional[str] = None) -> Image.Image:
        p = self.palette
        base = Image.new("RGB", (self.WIDTH, self.HEIGHT), p["bg_base"])

        # 1. Направленное свечение Chiaroscuro / Биолюминесцентная аура
        glow_layer = Image.new("RGB", (self.WIDTH, self.HEIGHT), p["bg_base"])
        g_draw = ImageDraw.Draw(glow_layer)

        cx = int(self.WIDTH * (0.75 if slide_idx % 2 == 0 else 0.28))
        cy = int(self.HEIGHT * (0.22 if slide_idx == 0 else 0.40))
        radius = 700

        glow_intensity = 0.35 if self.theme_key == "cyan" else (0.28 if p["is_dark"] else 0.45)
        for r in range(radius, 0, -20):
            ratio = 1.0 - (r / radius)
            col = tuple(
                int(p["bg_base"][i] + (p["glow_primary"][i] - p["bg_base"][i]) * (ratio ** 2.0) * glow_intensity)
                for i in range(3)
            )
            g_draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)

        base = Image.blend(base, glow_layer, 0.88)

        # 2. Фоновое изображение (с сохранением насыщенности циана и плавным переходом сверху для текста)
        if bg_image_path and os.path.isfile(bg_image_path):
            try:
                bg_img = Image.open(bg_image_path).convert("RGB")
                iw, ih = bg_img.size
                scale = max(self.WIDTH / iw, self.HEIGHT / ih)
                nw, nh = int(iw * scale), int(ih * scale)
                bg_img = bg_img.resize((nw, nh), Image.Resampling.LANCZOS)

                # Выравнивание: центрируем по горизонтали, по вертикали смещаем чуть вниз для баланса
                left = (nw - self.WIDTH) // 2
                top = max(0, min(nh - self.HEIGHT, int((nh - self.HEIGHT) * 0.25)))
                bg_img = bg_img.crop((left, top, left + self.WIDTH, top + self.HEIGHT))
                bg_img = ImageEnhance.Contrast(bg_img).enhance(1.12)

                # В теме cyan сохраняем полную насыщенность биолюминесценции
                if self.theme_key != "cyan":
                    bg_img = ImageEnhance.Color(bg_img).enhance(0.45)

                # Маска: сверху ~420px темный фон для 100% читаемости заголовка, снизу сияющая графика
                mask = Image.new("L", (self.WIDTH, self.HEIGHT), 255)
                m_draw = ImageDraw.Draw(mask)
                fade_h = int(self.HEIGHT * 0.42)
                for y in range(fade_h):
                    alpha = int(255 * ((y / fade_h) ** 2.2))
                    m_draw.line([(0, y), (self.WIDTH, y)], fill=alpha)

                base = Image.composite(bg_img, base, mask)
            except Exception:
                pass
        elif self.theme_key == "cyan":
            # Если фонового изображения нет, рисуем фирменные биолюминесцентные волны синапсов
            base = self._draw_cyan_waves(base, slide_idx)

        # 3. Лабораторная миллиметровая сетка (тонкие линии)
        draw = ImageDraw.Draw(base)
        grid_step = 90
        for x in range(self.MARGIN_X, self.WIDTH - self.MARGIN_X + 1, grid_step):
            draw.line([(x, self.MARGIN_TOP), (x, self.HEIGHT - self.MARGIN_BOTTOM)], fill=p["grid_line"], width=1)
        for y in range(self.MARGIN_TOP, self.HEIGHT - self.MARGIN_BOTTOM + 1, grid_step):
            draw.line([(self.MARGIN_X, y), (self.WIDTH - self.MARGIN_X, y)], fill=p["grid_line"], width=1)

        # 4. Аналоговое зерно (Film Grain)
        base = self._apply_film_grain(base, intensity=p["grain_intensity"])
        return base

    def _draw_cyan_waves(self, base: Image.Image, slide_idx: int) -> Image.Image:
        """Рисует процедурные биолюминесцентные циановые волны (ритмы мозга/синаптические ленты)."""
        w, h = self.WIDTH, self.HEIGHT
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)

        phase = slide_idx * 1.45
        waves_config = [
            {"y_ratio": 0.67, "amp1": 70, "f1": 0.0026, "amp2": 32, "f2": 0.0058, "thick": 28, "alpha": 22, "core_alpha": 85},
            {"y_ratio": 0.75, "amp1": 85, "f1": 0.0033, "amp2": 40, "f2": 0.0050, "thick": 38, "alpha": 18, "core_alpha": 70},
            {"y_ratio": 0.59, "amp1": 55, "f1": 0.0040, "amp2": 25, "f2": 0.0075, "thick": 20, "alpha": 25, "core_alpha": 95},
        ]

        for cfg in waves_config:
            pts_top = []
            pts_bot = []
            pts_center = []
            for x in range(-20, w + 30, 8):
                y_c = h * cfg["y_ratio"] + math.sin(x * cfg["f1"] + phase) * cfg["amp1"] + math.cos(x * cfg["f2"] + phase * 0.7) * cfg["amp2"]
                t = cfg["thick"] * (0.65 + 0.35 * math.sin(x * 0.0035 + phase))
                pts_top.append((x, y_c - t))
                pts_bot.append((x, y_c + t))
                pts_center.append((x, y_c))

            # Полупрозрачная лента
            d.polygon(pts_top + pts_bot[::-1], fill=(0, 190, 240, cfg["alpha"]))
            # Яркая центральная световая нить
            d.line(pts_center, fill=(0, 229, 255, cfg["core_alpha"]), width=2)
            d.line(pts_center, fill=(210, 250, 255, cfg["core_alpha"] // 2), width=1)

        base_rgba = base.convert("RGBA")
        blended = Image.alpha_composite(base_rgba, overlay)
        return blended.convert("RGB")

    @staticmethod
    def _crop_center(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
        w, h = img.size
        scale = max(target_w / w, target_h / h)
        nw, nh = int(w * scale), int(h * scale)
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        left = (nw - target_w) // 2
        top = (nh - target_h) // 2
        return img.crop((left, top, left + target_w, top + target_h))

    @staticmethod
    def _apply_film_grain(img: Image.Image, intensity: int = 12) -> Image.Image:
        if intensity <= 0:
            return img
        if HAS_NUMPY:
            arr = np.array(img, dtype=np.int16)
            noise = np.random.normal(0, intensity, (img.height, img.width, 1)).astype(np.int16)
            arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
            return Image.fromarray(arr)
        return img

    # --------------------------------------------------------------------------
    # ДЕКОРАТИВНЫЕ ЭЛЕМЕНТЫ НЕЙРОЖУРНАЛА И КЛИНИКИ (ЭЭГ, СХЕМЫ МОЗГА, ШТАМПЫ)
    # --------------------------------------------------------------------------
    def _draw_chrome_frame(
        self,
        draw: ImageDraw.ImageDraw,
        slide_idx: int,
        total_slides: int,
        issue_code: str = "ISSUE №04 // PFC-PROTOCOL",
        classification: str = "CLINICAL NEUROBIOLOGY",
    ):
        """Рисует журнальную/клиническую рамку, колонтитулы, кроссхейры и номер слайда."""
        p = self.palette
        mx, mt, mb = self.MARGIN_X, self.MARGIN_TOP, self.MARGIN_BOTTOM
        w, h = self.WIDTH, self.HEIGHT

        draw.rectangle([mx, mt, w - mx, h - mb], outline=p["border"], width=1)
        tick = 14
        for cx, cy in [(mx, mt), (w - mx, mt), (mx, h - mb), (w - mx, h - mb)]:
            draw.line([(cx - tick, cy), (cx + tick, cy)], fill=p["accent"], width=2)
            draw.line([(cx, cy - tick), (cx, cy + tick)], fill=p["accent"], width=2)

        header_h = 64
        draw.line([(mx, mt + header_h), (w - mx, mt + header_h)], fill=p["border"], width=1)

        f_meta = self._font("mono", 18)
        draw.text((mx + 24, mt + 20), f"SPECTR MIND  //  {issue_code}", font=f_meta, fill=p["text_muted"])

        slide_str = f"{slide_idx + 1:02d} / {total_slides:02d}"
        sw = draw.textlength(slide_str, font=f_meta)
        draw.text((w - mx - 24 - sw, mt + 20), slide_str, font=f_meta, fill=p["accent"])

        sep_x = w - mx - 48 - int(sw)
        draw.line([(sep_x, mt), (sep_x, mt + header_h)], fill=p["border"], width=1)

        cls_w = draw.textlength(classification, font=f_meta)
        draw.text((sep_x - 24 - cls_w, mt + 20), classification, font=f_meta, fill=p["text_muted"])

        footer_h = 74
        fy = h - mb - footer_h
        draw.line([(mx, fy), (w - mx, fy)], fill=p["border"], width=1)

        bx = mx + 24
        by = fy + 20
        random.seed(1042 + slide_idx)
        for _ in range(22):
            bw = random.choice([2, 3, 5])
            draw.rectangle([bx, by, bx + bw, by + 34], fill=p["text_muted"])
            bx += bw + random.choice([2, 4])

        draw.text((bx + 16, fy + 24), f"{self.brand_handle}   •   TG: {self.bot_handle}", font=f_meta, fill=p["text_muted"])

        if slide_idx < total_slides - 1:
            swipe_txt = "ЛИСТАЙ ПРОТОКОЛ  →"
            stw = draw.textlength(swipe_txt, font=f_meta)
            draw.text((w - mx - 24 - stw, fy + 24), swipe_txt, font=f_meta, fill=p["accent"])
        else:
            end_txt = "ФИНАЛ ПРОТОКОЛА  [●]"
            stw = draw.textlength(end_txt, font=f_meta)
            draw.text((w - mx - 24 - stw, fy + 24), end_txt, font=f_meta, fill=p["accent"])

        prog_w = int(((w - 2 * mx) * (slide_idx + 1)) / total_slides)
        draw.rectangle([mx, fy - 2, mx + prog_w, fy + 1], fill=p["accent"])

    def _draw_neuro_graphic(self, draw: ImageDraw.ImageDraw, mode: str, box: Tuple[int, int, int, int]):
        """
        Генерирует процедурную научную графику:
          - 'eeg': многоканальная осциллограмма ритмов мозга (Gamma / Theta / Alpha)
          - 'cortex_grid': топографическая 3D-матрица синхронизации полушарий
        """
        p = self.palette
        x1, y1, x2, y2 = box
        w = x2 - x1
        h = y2 - y1

        draw.rectangle([x1, y1, x2, y2], fill=p["bg_Card"], outline=p["border"], width=1)
        f_tiny = self._font("mono", 15)

        if mode == "eeg":
            channels = [
                ("CH-01 // PFC GAMMA (40Hz)", 0.18, 22, p["accent"]),
                ("CH-02 // THETA SYNC (6.5Hz)", 0.50, 9, p["text_main"]),
                ("CH-03 // VAGUS / CORTISOL", 0.82, 4, p["text_muted"]),
            ]
            for label, rel_y, freq, col in channels:
                cy = int(y1 + h * rel_y)
                draw.line([(x1 + 16, cy), (x2 - 16, cy)], fill=p["grid_line"], width=1)
                draw.text((x1 + 20, cy - 26), label, font=f_tiny, fill=p["text_muted"])
                pts = []
                for px in range(x1 + 20, x2 - 20, 4):
                    t = (px - x1) / w
                    envelope = math.sin(t * math.pi)
                    amp = (h * 0.11) * envelope
                    val = (
                        math.sin(t * freq * math.tau) * 0.65
                        + math.cos(t * (freq * 1.7) * math.tau) * 0.35
                    )
                    pts.append((px, cy + int(val * amp)))
                if len(pts) > 1:
                    draw.line(pts, fill=col, width=2)

        elif mode == "cortex_grid":
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            max_r = min(w, h) // 2 - 24
            for r_frac in [0.35, 0.68, 1.0]:
                r = int(max_r * r_frac)
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=p["border"], width=1)
            draw.line([(cx - max_r - 12, cy), (cx + max_r + 12, cy)], fill=p["border"], width=1)
            draw.line([(cx, cy - max_r - 12), (cx, cy + max_r + 12)], fill=p["border"], width=1)

            nodes = []
            for i in range(12):
                ang = (i / 12.0) * math.tau
                dist = max_r * (0.45 if i % 2 == 0 else 0.82)
                nx = cx + int(math.cos(ang) * dist)
                ny = cy + int(math.sin(ang) * dist)
                nodes.append((nx, ny))

            for i in range(len(nodes)):
                n1 = nodes[i]
                n2 = nodes[(i + 3) % len(nodes)]
                n3 = nodes[(i + 5) % len(nodes)]
                draw.line([n1, n2], fill=p["border"], width=1)
                if i % 3 == 0:
                    draw.line([n1, n3], fill=p["accent"], width=2)

            for idx, (nx, ny) in enumerate(nodes):
                col = p["accent"] if idx % 3 == 0 else p["text_main"]
                draw.ellipse([nx - 5, ny - 5, nx + 5, ny + 5], fill=col)

            draw.text((x1 + 20, y1 + 16), "FIG 1.4 // PREFRONTAL COHERENCE MAP", font=f_tiny, fill=p["text_muted"])
            draw.text((x1 + 20, y2 - 30), "STATUS: HYPER-FOCUS ENGAGED (+530% NA)", font=f_tiny, fill=p["accent"])

    # --------------------------------------------------------------------------
    # УМНАЯ ВЕРСТКА ТЕКСТА С ПОДДЕРЖКОЙ АКЦЕНТОВ (*слово* или [accent]слово[/accent])
    # --------------------------------------------------------------------------
    def _tokenize_styled_text(self, text: str) -> List[Tuple[str, bool]]:
        text = re.sub(r"\[accent\](.*?)\[/accent\]", r"*\1*", text, flags=re.IGNORECASE)
        segments = re.split(r"(\*[^*]+\*)", text)
        tokens: List[Tuple[str, bool]] = []
        for seg in segments:
            if not seg:
                continue
            is_acc = seg.startswith("*") and seg.endswith("*") and len(seg) > 2
            clean = seg[1:-1] if is_acc else seg
            for word in clean.split(" "):
                if word != "":
                    tokens.append((word, is_acc))
        return tokens

    def _draw_rich_paragraph(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        max_width: int,
        font: ImageFont.FreeTypeFont,
        line_height: int,
        default_color: Tuple[int, int, int],
        accent_color: Tuple[int, int, int],
        highlight_box: bool = False,
    ) -> int:
        paragraphs = text.split("\n")
        cur_y = y
        space_w = draw.textlength(" ", font=font)

        for para in paragraphs:
            if not para.strip():
                cur_y += int(line_height * 0.45)
                continue

            tokens = self._tokenize_styled_text(para)
            lines: List[List[Tuple[str, bool, float]]] = []
            current_line: List[Tuple[str, bool, float]] = []
            current_w = 0.0

            for word, is_acc in tokens:
                ww = draw.textlength(word, font=font)
                needed = ww if not current_line else (space_w + ww)
                if current_w + needed <= max_width or not current_line:
                    current_line.append((word, is_acc, ww))
                    current_w += needed
                else:
                    lines.append(current_line)
                    current_line = [(word, is_acc, ww)]
                    current_w = ww
            if current_line:
                lines.append(current_line)

            for line in lines:
                cx = float(x)
                for word, is_acc, ww in line:
                    if is_acc and highlight_box:
                        pad_x, pad_y = 6, 3
                        draw.rectangle(
                            [int(cx - pad_x), int(cur_y - pad_y), int(cx + ww + pad_x), int(cur_y + line_height - 10)],
                            fill=self.palette["accent_bg"],
                        )
                    color = accent_color if is_acc else default_color
                    draw.text((int(cx), int(cur_y)), word, font=font, fill=color)
                    cx += ww + space_w
                cur_y += line_height

            cur_y += int(line_height * 0.25)

        return cur_y

    # --------------------------------------------------------------------------
    # РЕНДЕРИНГ ТИПОВЫХ СЛАЙДОВ (ОБЛОЖКА, КОНТЕНТ/ДОСЬЕ, ПРОТОКОЛ, CTA-ВОРОНКА)
    # --------------------------------------------------------------------------
    def render_slide(self, slide: Dict, idx: int, total: int, meta: Dict) -> Image.Image:
        img = self._create_canvas(slide_idx=idx, bg_image_path=slide.get("bg_image"))
        draw = ImageDraw.Draw(img)
        p = self.palette

        self._draw_chrome_frame(
            draw,
            slide_idx=idx,
            total_slides=total,
            issue_code=meta.get("issue_code", "ISSUE №04 // NEURO-DOSSIER"),
            classification=meta.get("classification", "CLINICAL ARCHIVE"),
        )

        inner_x = self.MARGIN_X + 44
        inner_w = self.WIDTH - 2 * (self.MARGIN_X + 44)
        top_y = self.MARGIN_TOP + 98

        slide_type = slide.get("type", "content")

        badge = slide.get("badge", "").upper()
        if badge:
            f_badge = self._font("mono", 19)
            bw = int(draw.textlength(badge, font=f_badge)) + 32
            bh = 38
            draw.rectangle([inner_x, top_y, inner_x + bw, top_y + bh], fill=p["badge_bg"], outline=p["accent"], width=1)
            draw.text((inner_x + 16, top_y + 8), badge, font=f_badge, fill=p["badge_fg"])
            top_y += bh + 28

        if slide_type == "cover":
            f_title = self._font("primary", slide.get("title_size", 64))
            top_y = self._draw_rich_paragraph(
                draw,
                slide.get("title", ""),
                x=inner_x,
                y=top_y,
                max_width=inner_w,
                font=f_title,
                line_height=int(slide.get("title_size", 64) * 1.15),
                default_color=p["text_main"],
                accent_color=p["accent"],
                highlight_box=not p["is_dark"],
            )

            top_y += 14
            draw.line([(inner_x, top_y), (inner_x + inner_w, top_y)], fill=p["border"], width=1)
            draw.rectangle([inner_x, top_y - 2, inner_x + 96, top_y + 2], fill=p["accent"])
            top_y += 28

            if slide.get("subtitle"):
                f_sub = self._font("secondary", 30)
                top_y = self._draw_rich_paragraph(
                    draw,
                    slide["subtitle"],
                    x=inner_x,
                    y=top_y,
                    max_width=inner_w,
                    font=f_sub,
                    line_height=42,
                    default_color=p["text_muted"],
                    accent_color=p["text_main"],
                )

            if not slide.get("bg_image"):
                graphic_mode = slide.get("graphic", "cortex_grid")
                g_top = max(top_y + 24, 750)
                g_bot = self.HEIGHT - self.MARGIN_BOTTOM - 104
                if g_bot - g_top >= 180 and graphic_mode:
                    self._draw_neuro_graphic(draw, mode=graphic_mode, box=(inner_x, g_top, inner_x + inner_w, g_bot))

        elif slide_type == "content":
            f_title = self._font("primary", slide.get("title_size", 50))
            top_y = self._draw_rich_paragraph(
                draw,
                slide.get("title", ""),
                x=inner_x,
                y=top_y,
                max_width=inner_w,
                font=f_title,
                line_height=int(slide.get("title_size", 50) * 1.18),
                default_color=p["text_main"],
                accent_color=p["accent"],
                highlight_box=not p["is_dark"],
            )
            top_y += 12
            draw.line([(inner_x, top_y), (inner_x + 140, top_y)], fill=p["accent"], width=3)
            top_y += 24

            if slide.get("body"):
                f_body = self._font("secondary", 29)
                top_y = self._draw_rich_paragraph(
                    draw,
                    slide["body"],
                    x=inner_x,
                    y=top_y,
                    max_width=inner_w,
                    font=f_body,
                    line_height=42,
                    default_color=p["text_main"],
                    accent_color=p["accent"],
                )

            metrics = slide.get("metrics", [])
            if metrics:
                top_y += 14
                card_h = 124
                col_w = inner_w // len(metrics)
                draw.rectangle(
                    [inner_x, top_y, inner_x + inner_w, top_y + card_h],
                    fill=p["bg_Card"],
                    outline=p["border"],
                    width=1,
                )
                f_val = self._font("primary", 40)
                f_lbl = self._font("mono", 15)
                for m_idx, m in enumerate(metrics):
                    mx_col = inner_x + m_idx * col_w
                    if m_idx > 0:
                        draw.line([(mx_col, top_y), (mx_col, top_y + card_h)], fill=p["border"], width=1)
                    draw.text((mx_col + 20, top_y + 18), str(m.get("value", "")), font=f_val, fill=p["accent"])
                    draw.text((mx_col + 20, top_y + 78), str(m.get("label", "")).upper(), font=f_lbl, fill=p["text_muted"])
                top_y += card_h + 20

            if slide.get("callout"):
                c_top = max(top_y + 10, self.HEIGHT - self.MARGIN_BOTTOM - 225)
                c_bot = self.HEIGHT - self.MARGIN_BOTTOM - 100
                draw.rectangle([inner_x, c_top, inner_x + inner_w, c_bot], fill=p["bg_Card"], outline=p["border"], width=1)
                draw.rectangle([inner_x, c_top, inner_x + 6, c_bot], fill=p["accent"])
                f_call = self._font("secondary", 24)
                self._draw_rich_paragraph(
                    draw,
                    slide["callout"],
                    x=inner_x + 24,
                    y=c_top + 18,
                    max_width=inner_w - 44,
                    font=f_call,
                    line_height=33,
                    default_color=p["text_muted"],
                    accent_color=p["text_main"],
                )

        elif slide_type == "protocol":
            f_title = self._font("primary", slide.get("title_size", 48))
            top_y = self._draw_rich_paragraph(
                draw,
                slide.get("title", ""),
                x=inner_x,
                y=top_y,
                max_width=inner_w,
                font=f_title,
                line_height=56,
                default_color=p["text_main"],
                accent_color=p["accent"],
            )
            top_y += 24

            steps = slide.get("steps", [])
            f_step_num = self._font("primary", 40)
            f_step_tag = self._font("mono", 14)
            f_step_title = self._font("secondary", 28)
            f_step_desc = self._font("secondary", 24)

            avail_h = (self.HEIGHT - self.MARGIN_BOTTOM - 90) - top_y
            num_steps = len(steps) if steps else 1
            gap = 20
            card_h = min(195, max(170, (avail_h - (num_steps - 1) * gap) // num_steps))
            idx_w = 124

            for s_idx, step in enumerate(steps):
                box_top = top_y
                # Фоновая карточка
                draw.rectangle(
                    [inner_x, box_top, inner_x + inner_w, box_top + card_h],
                    fill=p["bg_Card"],
                    outline=p["border"],
                    width=1,
                )
                # Левая плашка под номер и тег
                draw.rectangle(
                    [inner_x, box_top, inner_x + idx_w, box_top + card_h],
                    fill=p["accent_bg"],
                    outline=p["border"],
                    width=1,
                )
                # Вертикальная неоновая полоса на левом краю карточки
                draw.rectangle(
                    [inner_x, box_top, inner_x + 4, box_top + card_h],
                    fill=p["accent"],
                )

                # Разбор кода шага (напр. "01 // СВЕТ" -> номер "01" и тег "СВЕТ")
                raw_code = str(step.get("code", f"0{s_idx + 1}")).strip()
                if "//" in raw_code:
                    parts = raw_code.split("//", 1)
                    num_str = parts[0].strip()
                    tag_str = parts[1].strip().upper()
                elif " " in raw_code and any(ch.isdigit() for ch in raw_code.split(" ")[0]):
                    parts = raw_code.split(" ", 1)
                    num_str = parts[0].strip()
                    tag_str = parts[1].strip().upper()
                else:
                    num_str = f"{s_idx + 1:02d}"
                    tag_str = raw_code.upper() if raw_code else f"ШАГ {s_idx + 1}"

                # Центрируем номер и тег в левой плашке
                sidebar_cx = inner_x + idx_w / 2.0
                nw = draw.textlength(num_str, font=f_step_num)
                draw.text((sidebar_cx - nw / 2.0, box_top + 40), num_str, font=f_step_num, fill=p["accent"])

                if tag_str:
                    draw.line([(inner_x + 22, box_top + 94), (inner_x + idx_w - 22, box_top + 94)], fill=p["border"], width=1)
                    tw = draw.textlength(tag_str, font=f_step_tag)
                    draw.text((sidebar_cx - tw / 2.0, box_top + 108), tag_str, font=f_step_tag, fill=p["text_muted"])

                # Контент справа от плашки — никогда не пересекается
                tx = inner_x + idx_w + 26
                tw_content = inner_w - idx_w - 46
                draw.text((tx, box_top + 22), step.get("heading", ""), font=f_step_title, fill=p["text_main"])
                self._draw_rich_paragraph(
                    draw,
                    step.get("text", ""),
                    x=tx,
                    y=box_top + 68,
                    max_width=tw_content,
                    font=f_step_desc,
                    line_height=32,
                    default_color=p["text_muted"],
                    accent_color=p["accent"],
                )
                top_y += card_h + gap

        elif slide_type == "cta":
            f_title = self._font("primary", slide.get("title_size", 54))
            top_y = self._draw_rich_paragraph(
                draw,
                slide.get("title", ""),
                x=inner_x,
                y=top_y,
                max_width=inner_w,
                font=f_title,
                line_height=64,
                default_color=p["text_main"],
                accent_color=p["accent"],
                highlight_box=not p["is_dark"],
            )
            top_y += 16

            if slide.get("body"):
                f_body = self._font("secondary", 29)
                top_y = self._draw_rich_paragraph(
                    draw,
                    slide["body"],
                    x=inner_x,
                    y=top_y,
                    max_width=inner_w,
                    font=f_body,
                    line_height=40,
                    default_color=p["text_muted"],
                    accent_color=p["text_main"],
                )
            top_y += 22

            box_h = 250
            draw.rectangle(
                [inner_x, top_y, inner_x + inner_w, top_y + box_h],
                fill=p["bg_Card"],
                outline=p["accent"],
                width=2,
            )
            f_mono_b = self._font("mono", 19)
            f_cta_h = self._font("primary", 36)
            f_cta_s = self._font("secondary", 25)

            draw.text(
                (inner_x + 32, top_y + 24),
                "БЕСПЛАТНЫЙ ДОСТУП // PDF-ДОСЬЕ (4 СТР.)",
                font=f_mono_b,
                fill=p["accent"],
            )
            draw.text(
                (inner_x + 32, top_y + 62),
                slide.get("lead_magnet_title", "«Нейро-Стек: Управление префронтальной корой»"),
                font=f_cta_h,
                fill=p["text_main"],
            )

            btn_y = top_y + 148
            btn_h = 72
            btn_bg = p.get("button_bg", p["accent"])
            btn_fg = p.get("button_fg", (10, 11, 14) if p["is_dark"] else (244, 241, 234))
            draw.rectangle(
                [inner_x + 32, btn_y, inner_x + inner_w - 32, btn_y + btn_h],
                fill=btn_bg,
            )
            btn_text = slide.get("cta_button", "ССЫЛКА В ШАПКЕ ПРОФИЛЯ -> @SPECTRNEWSBOT")
            btw = draw.textlength(btn_text, font=f_mono_b)
            draw.text(
                (inner_x + (inner_w - int(btw)) // 2, btn_y + 24),
                btn_text,
                font=f_mono_b,
                fill=btn_fg,
            )

            top_y += box_h + 24
            if slide.get("footer_note"):
                self._draw_rich_paragraph(
                    draw,
                    slide["footer_note"],
                    x=inner_x,
                    y=top_y,
                    max_width=inner_w,
                    font=f_cta_s,
                    line_height=35,
                    default_color=p["text_muted"],
                    accent_color=p["accent"],
                )

        return img

    def render_deck(self, deck_data: Dict, output_dir: str) -> List[str]:
        """Рендерит всю серию слайдов и сохраняет PNG-файлы в output_dir."""
        os.makedirs(output_dir, exist_ok=True)
        slides = deck_data.get("slides", [])
        meta = deck_data.get("meta", {})
        saved_files = []

        for idx, slide in enumerate(slides):
            img = self.render_slide(slide, idx=idx, total=len(slides), meta=meta)
            out_path = os.path.join(output_dir, f"slide_{idx + 1:02d}_{self.theme_key}.png")
            img.save(out_path, format="PNG", optimize=True)
            saved_files.append(out_path)

        return saved_files


# ==============================================================================
# ДЕМО-ДАННЫЕ КАРУСЕЛИ ПРОЕКТА SPECTR MIND (ГОТОВЫЙ ШАБЛОН ВОРОНКИ)
# ==============================================================================
SAMPLE_DECK = {
    "meta": {
        "issue_code": "VOL. 07 // PFC DEPLETION",
        "classification": "SPECTR LAB // DOSSIER",
    },
    "slides": [
        {
            "type": "cover",
            "badge": "НЕЙРОБИОЛОГИЯ ВНИМАНИЯ // АРХИВ",
            "title": "ПОЧЕМУ ТВОЙ МОЗГ *ВЫГОРАЕТ* ДО 12:00 ДНЯ (И ПРИ ЧЕМ ТУТ *НОЛАН*)",
            "subtitle": "Как микро-решения со смартфона сжигают метаболический ресурс префронтальной коры за 40 минут после пробуждения.",
            "bg_image": "carousel_tool/assets/cyan_brain_bg.jpg" if os.path.isfile("carousel_tool/assets/cyan_brain_bg.jpg") else (
                "assets/cyan_brain_bg.jpg" if os.path.isfile("assets/cyan_brain_bg.jpg") else None
            ),
            "graphic": "cortex_grid",
        },
        {
            "type": "content",
            "badge": "ФАКТ №01 // DECISION FATIGUE",
            "title": "У КРИСТОФЕРА НОЛАНА НЕТ *СМАРТФОНА* И РАБОЧЕЙ ПОЧТЫ",
            "body": "Префронтальная кора (ПФК) занимает всего 4% объема тела, но потребляет до *25% всей глюкозы* и кислорода.\n\nКаждое уведомление, скролл ленты или выбор ответа в чате запускает цикл переключения внимания. Через 90 минут такого режима уровень *глутамата* в синапсах достигает порога токсической усталости.",
            "metrics": [
                {"value": "-42%", "label": "Падение рабочей памяти"},
                {"value": "23 МИН", "label": "Возврат в глубокий фокус"},
                {"value": "+180%", "label": "Скачок утреннего кортизола"},
            ],
            "callout": "КЛИНИЧЕСКИЙ ФАКТ: Мозг не отличает выбор фильма на вечер от принятия стратегического финансового решения — цена в АТФ одинакова.",
        },
        {
            "type": "content",
            "badge": "ФАКТ №02 // ДОФАМИНОВАЯ ЯМА",
            "title": "ЛОЖНЫЙ СТИМУЛ: КОФЕИН БЛОКИРУЕТ *АДЕНОЗИН*, НО НЕ ДАЕТ ЭНЕРГИЮ",
            "body": "Двойной эспрессо утром лишь временно заклеивает рецепторы усталости. Когда его действие падает, накопленный аденозин обрушивается на кору лавиной — возникает *туман в голове* и тяга к быстрым углеводам.\n\nВ советской космической медицине эту проблему решали без стимуляторов — через связку *дыхательной гипоксии* и адаптогенов.",
            "metrics": [
                {"value": "120 СЕК", "label": "Перезапуск через блуждающий нерв"},
                {"value": "+530%", "label": "Выброс эндогенного норадреналина"},
            ],
            "callout": "ИСТОЧНИК: Закрытые протоколы Института мозга (Бехтерева Н.П.) и исследования сверхконцентрации операторов.",
        },
        {
            "type": "protocol",
            "badge": "ПРАКТИКА // УТРЕННИЙ НЕЙРО-СТЕК",
            "title": "3 ШАГА ЗАЩИТЫ *ПРЕФРОНТАЛЬНОЙ КОРЫ* В ПЕРВЫЙ ЧАС УТРА",
            "steps": [
                {
                    "code": "01 // СВЕТ",
                    "heading": "Фотонный якорь сетчатки (0–10 мин)",
                    "text": "Выйди на дневной свет без очков и экранов. Импульс в супрахиазматическое ядро запускает здоровый пик *кортизола* и таймер мелатонина.",
                },
                {
                    "code": "02 // ХОЛОД",
                    "heading": "Локальный термогенез + Box Breathing",
                    "text": "Умывание ледяной водой (15°C) + 4 цикла дыхания 4-4-4-4. Снимает гипервозбуждение *амигдалы* за 60 секунд.",
                },
                {
                    "code": "03 // БЛОК",
                    "heading": "90 минут без входящего дофамина",
                    "text": "Никаких мессенджеров до закрытия главной когнитивной задачи дня. Экономия до *60% ресурса воли*.",
                },
            ],
        },
        {
            "type": "cta",
            "badge": "БЕСПЛАТНЫЙ ПРОТОКОЛ В TELEGRAM",
            "title": "ЗАБЕРИ ПОЛНЫЙ ПРОТОКОЛ РАЗГОНА МОЗГА ЗА *120 СЕКУНД*",
            "body": "Мы упаковали пошаговую схему управления префронтальной корой, таблицы адаптогенов и утренний чек-лист в закрытый 4-страничный PDF-файл.",
            "lead_magnet_title": "Гайд «Нейро-Стек: Управление ПФК»",
            "cta_button": "ССЫЛКА В ШАПКЕ ПРОФИЛЯ -> @SPECTRNEWSBOT",
            "footer_note": "Или напиши кодовое слово *НЕЙРО* в комментарии — пришлем прямую ссылку на выдачу PDF в Директ за 5 секунд.",
        },
    ],
}


def main():
    parser = argparse.ArgumentParser(description="SPECTR MIND Carousel Generator")
    parser.add_argument("--font-primary", type=str, default=None, help="Путь к основному (заголовочному) шрифту .ttf/.otf")
    parser.add_argument("--font-secondary", type=str, default=None, help="Путь к дополнительному (текстовому) шрифту .ttf/.otf")
    parser.add_argument("--font-mono", type=str, default=None, help="Путь к моноширинному шрифту для меток .ttf/.otf")
    parser.add_argument("--theme", type=str, default="cyan", choices=["cyan", "clinic", "journal"], help="Стиль: cyan (фирменный циановый), clinic или journal")
    parser.add_argument("--input", type=str, default=None, help="Путь к JSON-файлу со слайдами")
    parser.add_argument("--output", type=str, default="./output_carousel", help="Папка для сохранения PNG-слайдов")
    args = parser.parse_args()

    deck = SAMPLE_DECK
    if args.input and os.path.isfile(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            deck = json.load(f)

    gen = SpectrCarouselGenerator(
        font_primary=args.font_primary,
        font_secondary=args.font_secondary,
        font_mono=args.font_mono,
        theme=args.theme,
    )
    files = gen.render_deck(deck, output_dir=args.output)
    print(f"[SPECTR MIND] Сгенерировано {len(files)} слайдов в стиле '{args.theme}':")
    for fp in files:
        print(" ->", fp)


if __name__ == "__main__":
    main()
