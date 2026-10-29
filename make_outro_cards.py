"""Generator of cinematic 1080x1920 video outro / end cards for Spectr Mind Reels."""
import os
import math
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = "content/outro_templates"
os.makedirs(OUT_DIR, exist_ok=True)

# Brand colors (Cyan Edition)
BG_COLOR = (2, 12, 22)
TEXT_WHITE = (245, 250, 255)
TEXT_MUTED = (142, 182, 206)
CYAN_ACCENT = (0, 229, 255)
CYAN_DIM = (10, 48, 72)
BORDER_COLOR = (20, 68, 96)
GRID_COLOR = (6, 20, 32)


def get_font(family: str, size: int):
    candidates = {
        "serif_bold": ["C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/timesbd.ttf"],
        "serif": ["C:/Windows/Fonts/georgia.ttf", "C:/Windows/Fonts/times.ttf"],
        "sans_bold": ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"],
        "sans": ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"],
        "mono": ["C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/cour.ttf"],
    }
    for path in candidates.get(family, []):
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_cyan_radial_glow(img: Image.Image, center_x: int, center_y: int, max_r: int, alpha_peak: int = 55):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    steps = 40
    for i in range(steps, 0, -1):
        r = int(max_r * (i / steps))
        alpha = int(alpha_peak * (1.0 - (i / steps)) ** 1.5)
        color = (0, 229, 255, alpha)
        draw.ellipse([center_x - r, center_y - r, center_x + r, center_y + r], fill=color)
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))


def draw_sinewave(draw: ImageDraw.ImageDraw, y_center: int, width: int = 1080):
    points = []
    for x in range(0, width, 4):
        y = y_center + int(math.sin(x * 0.015) * 18 + math.cos(x * 0.008) * 12)
        points.append((x, y))
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=(14, 45, 65), width=2)


def draw_barcode(draw: ImageDraw.ImageDraw, x: int, y: int, h: int = 28):
    bars = [2, 1, 3, 1, 1, 2, 4, 1, 2, 1, 3, 2, 1, 2, 1, 4, 1, 2, 3, 1]
    curr_x = x
    for b in bars:
        draw.rectangle([curr_x, y, curr_x + b, y + h], fill=BORDER_COLOR)
        curr_x += b + 2


def create_outro_card(
    filename: str,
    quote_lines: list[str],
    highlight_word: str,
    subtitle: str,
    keyword: str,
    sub_cta: str,
    vol_tag: str = "VOL. 01 // НЕЙРО-АРХИВ",
):
    w, h = 1080, 1920
    img = Image.new("RGB", (w, h), BG_COLOR)

    # 1. Subtle Radial Glow behind CTA
    draw_cyan_radial_glow(img, w // 2, 1150, max_r=550, alpha_peak=45)
    draw_cyan_radial_glow(img, w // 2, 600, max_r=400, alpha_peak=25)

    draw = ImageDraw.Draw(img)

    # 2. Background Grid (millimeter lines)
    for x in range(80, w, 160):
        draw.line([(x, 0), (x, h)], fill=GRID_COLOR, width=1)
    for y in range(80, h, 160):
        draw.line([(0, y), (w, y)], fill=GRID_COLOR, width=1)

    # 3. Swiss Crosshairs in 4 corners
    margin = 70
    ch_len = 16
    corners = [
        (margin, margin),
        (w - margin, margin),
        (margin, h - margin),
        (w - margin, h - margin),
    ]
    for cx, cy in corners:
        draw.line([(cx - ch_len, cy), (cx + ch_len, cy)], fill=BORDER_COLOR, width=2)
        draw.line([(cx, cy - ch_len), (cx, cy + ch_len)], fill=BORDER_COLOR, width=2)

    # 4. Top Header Line
    f_mono_sm = get_font("mono", 16)
    f_mono_md = get_font("mono", 20)
    top_y = 120
    draw.text((margin + 20, top_y), f"SPECTR MIND // {vol_tag}", font=f_mono_sm, fill=TEXT_MUTED)
    draw.text((w - margin - 220, top_y), "КЛИНИЧЕСКИЙ АРХИВ", font=f_mono_sm, fill=TEXT_MUTED)
    draw.line([(margin + 20, top_y + 35), (w - margin - 20, top_y + 35)], fill=BORDER_COLOR, width=1)

    # 5. Sinewave decorative line in upper third
    draw_sinewave(draw, 340)

    # 6. Main Quote Block (Serif Bold, Centered)
    f_quote = get_font("serif_bold", 54)
    f_sub = get_font("sans", 26)

    curr_y = 480
    for line in quote_lines:
        bbox = draw.textbbox((0, 0), line, font=f_quote)
        text_w = bbox[2] - bbox[0]
        tx = (w - text_w) // 2

        # Check if line contains highlight word
        if highlight_word and highlight_word.upper() in line.upper():
            # Render line with highlight
            draw.text((tx, curr_y), line, font=f_quote, fill=CYAN_ACCENT)
        else:
            draw.text((tx, curr_y), line, font=f_quote, fill=TEXT_WHITE)
        curr_y += 75

    curr_y += 25
    # Subtitle
    if subtitle:
        bbox_sub = draw.textbbox((0, 0), subtitle, font=f_sub)
        sub_w = bbox_sub[2] - bbox_sub[0]
        draw.text(((w - sub_w) // 2, curr_y), subtitle, font=f_sub, fill=TEXT_MUTED)
        curr_y += 65

    # 7. Elegant Divider Line
    draw.line([(w // 2 - 140, curr_y + 10), (w // 2 + 140, curr_y + 10)], fill=BORDER_COLOR, width=1)
    # Cyan center dot
    draw.ellipse([w // 2 - 4, curr_y + 7, w // 2 + 4, curr_y + 15], fill=CYAN_ACCENT)

    # 8. Brand Logo Lockup
    brand_y = curr_y + 70
    f_brand = get_font("sans_bold", 38)
    f_brand_sub = get_font("mono", 18)

    brand_text = "SPECTR MIND"
    bbox_b = draw.textbbox((0, 0), brand_text, font=f_brand)
    bw = bbox_b[2] - bbox_b[0]
    draw.text(((w - bw) // 2, brand_y), brand_text, font=f_brand, fill=TEXT_WHITE)

    sub_brand = "ИНСТИТУТ ПРИКЛАДНОЙ НЕЙРОБИОЛОГИИ"
    bbox_bs = draw.textbbox((0, 0), sub_brand, font=f_brand_sub)
    bsw = bbox_bs[2] - bbox_bs[0]
    draw.text(((w - bsw) // 2, brand_y + 55), sub_brand, font=f_brand_sub, fill=CYAN_ACCENT)

    # 9. Big CTA Button Card
    card_w = 900
    card_h = 160
    card_x = (w - card_w) // 2
    card_y = 1140

    # Draw rounded button in Electric Cyan
    draw.rounded_rectangle(
        [card_x, card_y, card_x + card_w, card_y + card_h],
        radius=20,
        fill=CYAN_ACCENT,
    )

    f_btn_lead = get_font("mono", 22)
    f_btn_main = get_font("sans_bold", 40)

    lead_text = "НАПИШИ В КОММЕНТАРИЯХ СЛОВО:"
    bbox_lead = draw.textbbox((0, 0), lead_text, font=f_btn_lead)
    lw = bbox_lead[2] - bbox_lead[0]
    draw.text(((w - lw) // 2, card_y + 26), lead_text, font=f_btn_lead, fill=(10, 30, 45))

    kw_text = f"« {keyword.upper()} »"
    bbox_kw = draw.textbbox((0, 0), kw_text, font=f_btn_main)
    kww = bbox_kw[2] - bbox_kw[0]
    draw.text(((w - kww) // 2, card_y + 72), kw_text, font=f_btn_main, fill=(2, 12, 22))

    # 10. Sub-CTA explanation under the button
    f_sub_cta = get_font("sans", 24)
    bbox_sc = draw.textbbox((0, 0), sub_cta, font=f_sub_cta)
    scw = bbox_sc[2] - bbox_sc[0]
    draw.text(((w - scw) // 2, card_y + card_h + 35), sub_cta, font=f_sub_cta, fill=TEXT_WHITE)

    hint_text = "бот мгновенно пришлет PDF в Директ"
    bbox_ht = draw.textbbox((0, 0), hint_text, font=f_mono_sm)
    htw = bbox_ht[2] - bbox_ht[0]
    draw.text(((w - htw) // 2, card_y + card_h + 75), hint_text, font=f_mono_sm, fill=TEXT_MUTED)

    # 11. Bottom Swiss Footer (barcode + link)
    bottom_y = h - margin - 50
    draw.line([(margin + 20, bottom_y), (w - margin - 20, bottom_y)], fill=BORDER_COLOR, width=1)
    draw_barcode(draw, margin + 25, bottom_y + 18, h=26)

    f_foot = get_font("mono", 17)
    draw.text((margin + 160, bottom_y + 22), "SPECTRMIND.RU • TG: @SPECTRNEWSBOT", font=f_foot, fill=TEXT_MUTED)
    draw.text((w - margin - 220, bottom_y + 22), "ПРОТОКОЛ-2026", font=f_foot, fill=CYAN_ACCENT)

    out_path = os.path.join(OUT_DIR, filename)
    img.save(out_path, format="PNG", compress_level=2)
    print(f"Saved: {out_path}")
    return out_path


if __name__ == "__main__":
    # Card 1: Ambient / Silence / Stress Reset
    create_outro_card(
        filename="outro_ambient_silence.png",
        quote_lines=[
            "МОЗГ УСТАЕТ НЕ ОТ ЖИЗНИ.",
            "ОН УСТАЕТ ОТ БЕСКОНЕЧНОГО",
            "ИНФОРМАЦИОННОГО ШУМА.",
        ],
        highlight_word="ШУМА.",
        subtitle="Верни контроль над своим вниманием и сном.",
        keyword="ТИШИНА",
        sub_cta="Забирай вечерний протокол сброса кортизола",
        vol_tag="АРХИВ // ЦИРКАДНЫЙ СТЕК",
    )

    # Card 2: Powerful Speech / Willpower / Dopamine
    create_outro_card(
        filename="outro_speech_willpower.png",
        quote_lines=[
            "СИЛА ДУХА — ЭТО НЕ МАГИЯ.",
            "ЭТО ИЗМЕРИМЫЙ РЕСУРС",
            "ПРЕФРОНТАЛЬНОЙ КОРЫ.",
        ],
        highlight_word="ПРЕФРОНТАЛЬНОЙ",
        subtitle="Физиология воли и защита от выгорания.",
        keyword="ВОЛЯ",
        sub_cta="Забирай протокол перезагрузки дофамина",
        vol_tag="ПРОТОКОЛ // РЕСУРС ВОЛИ",
    )

    # Card 3: Soviet Science / Vessels / Memory (Universal)
    create_outro_card(
        filename="outro_neuro_protocol.png",
        quote_lines=[
            "ЯСНОСТЬ МЫШЛЕНИЯ",
            "НАЧИНАЕТСЯ С КРОВОТОКА",
            "И КИСЛОРОДА В НЕЙРОНАХ.",
        ],
        highlight_word="НЕЙРОНАХ.",
        subtitle="Архивы Института Мозга и космической медицины.",
        keyword="НЕЙРО",
        sub_cta="Забирай 6-страничный гайд по разгону мозга",
        vol_tag="СССР // КЛИНИЧЕСКИЙ АРХИВ",
    )
