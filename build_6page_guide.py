"""Сборка 6-страничного бесплатного гайда SPECTR_Prefrontal_Protocol.pdf.

Текст — точно по ТЗ из гайд.txt.
Дизайн — Dark Neuro-Lab (Deep Space #0A0A0F, Obsidian #13131A, Cyan #00FFFF).
Финальная страница — оффер с product_cover.jpg и кликабельной кнопкой Robokassa.
"""
from __future__ import annotations

import os
import shutil
import sys

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image as RLImage,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ── Палитра ──────────────────────────────────────────────────────────────────
BG_SPACE    = HexColor("#0A0A0F")
BG_CARD     = HexColor("#13131A")
BG_CARD_ALT = HexColor("#1A1A24")
CYAN        = HexColor("#00FFFF")
CYAN_DIM    = HexColor("#00D4D4")
TEXT_WHITE   = HexColor("#FFFFFF")
TEXT_BODY    = HexColor("#D0D0E0")
TEXT_MUTED   = HexColor("#7A7A90")
TEXT_DARK    = HexColor("#0A0A0F")
BORDER       = HexColor("#1E1E2A")
VIOLET       = HexColor("#A855F7")

PAGE_W, PAGE_H = A4
MX   = 18 * mm      # margin X
MT   = 18 * mm      # margin top
MB   = 18 * mm      # margin bottom
UW   = PAGE_W - 2 * MX   # usable width

ROBOKASSA_URL = (
    "https://auth.robokassa.ru/Merchant/Index.aspx?"
    "MerchantLogin=Spectrmind&OutSum=1990.00&InvId=990001&"
    "SignatureValue=563a85cd72e55528c3b58858c2bbf7bb&"
    "Description=SpectrMind%3A+%D0%BF%D0%BE%D0%BB%D0%BD%D1%8B%D0%B9+"
    "%D0%BD%D0%B5%D0%B9%D1%80%D0%BE%D0%B3%D0%B0%D0%B9%D0%B4&"
    "Culture=ru&Encoding=utf-8"
)

FONT_DIR = r"C:\Windows\Fonts"


# ── Шрифты ───────────────────────────────────────────────────────────────────
def register_fonts() -> str:
    for fam, reg, bold, ital in [
        ("GSans", "arial.ttf", "arialbd.ttf", "ariali.ttf"),
        ("GSans", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf"),
    ]:
        paths = [os.path.join(FONT_DIR, n) for n in (reg, bold, ital)]
        if all(os.path.exists(p) for p in paths):
            pdfmetrics.registerFont(TTFont(fam, paths[0]))
            pdfmetrics.registerFont(TTFont(fam + "-Bold", paths[1]))
            pdfmetrics.registerFont(TTFont(fam + "-Italic", paths[2]))
            pdfmetrics.registerFontFamily(fam, normal=fam, bold=fam + "-Bold",
                                          italic=fam + "-Italic")
            return fam
    raise RuntimeError("Шрифт с кириллицей не найден")


# ── Стили ────────────────────────────────────────────────────────────────────
def make_styles(f: str) -> dict:
    return {
        # Обложка
        "cover_badge": ParagraphStyle("cb", fontName=f + "-Bold", fontSize=8.5,
                                      leading=11, textColor=CYAN, alignment=TA_CENTER),
        "cover_title": ParagraphStyle("ct", fontName=f + "-Bold", fontSize=26,
                                      leading=32, textColor=TEXT_WHITE, spaceAfter=4*mm),
        "cover_sub":   ParagraphStyle("cs", fontName=f, fontSize=10.5, leading=15,
                                      textColor=TEXT_BODY, spaceAfter=5*mm),
        "cover_foot":  ParagraphStyle("cf", fontName=f, fontSize=8.5, leading=12,
                                      textColor=TEXT_MUTED, alignment=TA_CENTER),
        # Контент
        "kicker":     ParagraphStyle("ki", fontName=f + "-Bold", fontSize=8, leading=11,
                                     textColor=CYAN, spaceAfter=2*mm),
        "h1":         ParagraphStyle("h1", fontName=f + "-Bold", fontSize=16, leading=20,
                                     textColor=TEXT_WHITE, spaceAfter=3*mm),
        "h2":         ParagraphStyle("h2", fontName=f + "-Bold", fontSize=11, leading=15,
                                     textColor=CYAN, spaceBefore=3*mm, spaceAfter=2*mm),
        "lead":       ParagraphStyle("ld", fontName=f, fontSize=9, leading=13.5,
                                     textColor=TEXT_BODY, spaceAfter=2.5*mm),
        "body":       ParagraphStyle("bd", fontName=f, fontSize=8.5, leading=12.5,
                                     textColor=TEXT_BODY, spaceAfter=2*mm),
        "card_title": ParagraphStyle("cdt", fontName=f + "-Bold", fontSize=9.5, leading=13,
                                     textColor=CYAN, spaceAfter=1.5*mm),
        "card_text":  ParagraphStyle("cdx", fontName=f, fontSize=8, leading=11.5,
                                     textColor=TEXT_BODY, spaceAfter=0),
        "bullet":     ParagraphStyle("bu", fontName=f, fontSize=8.5, leading=12.5,
                                     textColor=TEXT_BODY, spaceAfter=1.5*mm),
        "step_title": ParagraphStyle("st", fontName=f + "-Bold", fontSize=9.5, leading=13,
                                     textColor=TEXT_WHITE, spaceAfter=1*mm),
        "note":       ParagraphStyle("no", fontName=f, fontSize=7.5, leading=10.5,
                                     textColor=TEXT_MUTED, spaceBefore=1.5*mm),
        # CTA / Оффер
        "cta_badge":  ParagraphStyle("ctb", fontName=f + "-Bold", fontSize=8, leading=11,
                                     textColor=CYAN, alignment=TA_CENTER),
        "cta_title":  ParagraphStyle("ctt", fontName=f + "-Bold", fontSize=17, leading=22,
                                     textColor=TEXT_WHITE, alignment=TA_CENTER, spaceAfter=2*mm),
        "cta_sub":    ParagraphStyle("cts", fontName=f, fontSize=9, leading=13,
                                     textColor=TEXT_BODY, alignment=TA_CENTER, spaceAfter=2*mm),
        "cta_item":   ParagraphStyle("cti", fontName=f, fontSize=8, leading=11.5,
                                     textColor=TEXT_BODY, spaceAfter=1.2*mm),
        "price_old":  ParagraphStyle("po", fontName=f, fontSize=10, leading=12,
                                     textColor=TEXT_MUTED, alignment=TA_CENTER),
        "price_new":  ParagraphStyle("pn", fontName=f + "-Bold", fontSize=18, leading=22,
                                     textColor=CYAN, alignment=TA_CENTER),
        "price_note": ParagraphStyle("ppn", fontName=f, fontSize=7.5, leading=10,
                                     textColor=TEXT_MUTED, alignment=TA_CENTER),
        "btn_text":   ParagraphStyle("bt", fontName=f + "-Bold", fontSize=11, leading=14,
                                     textColor=TEXT_DARK, alignment=TA_CENTER),
        "cta_note":   ParagraphStyle("cn", fontName=f, fontSize=7, leading=9.5,
                                     textColor=TEXT_MUTED, alignment=TA_CENTER, spaceBefore=1.5*mm),
    }


# ── Компоненты ───────────────────────────────────────────────────────────────
class ButtonLink(Flowable):
    """Кнопка с активной ссылкой."""
    def __init__(self, text, url, width, height, style, color=CYAN):
        super().__init__()
        self.text, self.url = text, url
        self.width, self.height = width, height
        self.style, self.color = style, color

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(self.color)
        c.roundRect(0, 0, self.width, self.height, 5, stroke=0, fill=1)
        p = Paragraph(self.text, self.style)
        _, h = p.wrap(self.width, self.height)
        p.drawOn(c, 0, (self.height - h) / 2.0)
        if self.url:
            sc = getattr(c, "_currentMatrix", [1, 0, 0, 1, 0, 0])[0] or 1
            ox, oy = c.absolutePosition(0, 0)
            c.linkURL(self.url, (ox, oy, ox + self.width * sc, oy + self.height * sc),
                      relative=0, thickness=0)
        c.restoreState()


def card(flowables, bg=BG_CARD, border=BORDER, left_color=None, left_w=0, pad=9):
    """Темная карточка с опциональным левым бордером."""
    t = Table([[flowables]], colWidths=[UW])
    st = [
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.5, border),
        ("TOPPADDING", (0, 0), (-1, -1), pad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
        ("LEFTPADDING", (0, 0), (-1, -1), pad + 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), pad + 2),
    ]
    if left_color and left_w > 0:
        st.append(("LINEBEFORE", (0, 0), (0, -1), left_w, left_color))
    t.setStyle(TableStyle(st))
    return t


def dark_bg(font):
    """Общий фон + колонтитулы для каждой страницы."""
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(BG_SPACE)
        canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)

        if doc.page == 1:
            # Обложка: стильные угловые линии
            canvas.setStrokeColor(HexColor("#1A1A26"))
            canvas.setLineWidth(0.5)
            canvas.line(MX, PAGE_H - 12*mm, MX + 25*mm, PAGE_H - 12*mm)
            canvas.line(PAGE_W - MX - 25*mm, PAGE_H - 12*mm, PAGE_W - MX, PAGE_H - 12*mm)
            canvas.line(MX, 14*mm, MX + 25*mm, 14*mm)
            canvas.line(PAGE_W - MX - 25*mm, 14*mm, PAGE_W - MX, 14*mm)
        else:
            # Колонтитулы
            canvas.setStrokeColor(BORDER)
            canvas.setLineWidth(0.5)
            canvas.line(MX, PAGE_H - 13*mm, PAGE_W - MX, PAGE_H - 13*mm)
            canvas.setFont(font + "-Bold", 7.5)
            canvas.setFillColor(CYAN)
            canvas.drawString(MX, PAGE_H - 10.5*mm, "SPECTRMIND")
            canvas.setFont(font, 7.5)
            canvas.setFillColor(TEXT_MUTED)
            canvas.drawString(MX + 23*mm, PAGE_H - 10.5*mm,
                              "//   БАЗОВЫЙ НЕЙРО-ПРОТОКОЛ")
            canvas.drawRightString(PAGE_W - MX, PAGE_H - 10.5*mm,
                                   "ПРЕФРОНТАЛЬНАЯ КОРА")
            # Нижний
            canvas.line(MX, 13*mm, PAGE_W - MX, 13*mm)
            canvas.drawString(MX, 9*mm, "SPECTRMIND // COGNITIVE LAB")
            canvas.setFont(font + "-Bold", 7.5)
            canvas.setFillColor(CYAN)
            canvas.drawRightString(PAGE_W - MX, 9*mm,
                                   f"PAGE 0{doc.page} // 06")
        canvas.restoreState()
    return on_page


# ══════════════════════════════════════════════════════════════════════════════
#  СТРАНИЦЫ
# ══════════════════════════════════════════════════════════════════════════════

def page1_cover(S):
    """Страница 1 — Обложка."""
    badge = Table(
        [[Paragraph("SPECTRMIND  //  COGNITIVE LAB", S["cover_badge"])]],
        colWidths=[80*mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
            ("BOX", (0, 0), (-1, -1), 0.75, CYAN),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5*mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5*mm),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]),
    )

    info_card = card([
        Paragraph(
            "<font color='#00FFFF'>На основе исследований Stanford, MIT и Huberman Lab.</font>",
            S["card_text"]),
        Spacer(1, 2*mm),
        Paragraph("Время чтения: 4 минуты.", S["card_text"]),
        Paragraph("Формат: Прикладная нейробиология без воды.", S["card_text"]),
    ], bg=BG_CARD, left_color=CYAN, left_w=2.5, pad=10)

    return [
        Spacer(1, 45*mm),
        badge,
        Spacer(1, 14*mm),
        Paragraph(
            "УПРАВЛЕНИЕ<br/><font color='#00FFFF'>ПРЕФРОНТАЛЬНОЙ КОРОЙ</font>",
            S["cover_title"],
        ),
        Paragraph(
            "Базовый нейро-протокол: как убрать туман в голове, "
            "остановить кортизоловый захват и вернуть лазерный фокус за 24 часа",
            S["cover_sub"],
        ),
        Spacer(1, 20*mm),
        info_card,
        PageBreak(),
    ]


def page2_diagnostics(S):
    """Страница 2 — Диагностика: почему вы просыпаетесь уже уставшим."""

    card_d2 = card([
        Paragraph(
            "<font color='#00FFFF'>1. ВЫГОРАНИЕ ДОФАМИНОВЫХ РЕЦЕПТОРОВ D2</font>",
            S["card_title"]),
        Spacer(1, 1*mm),
        Paragraph(
            "В мозге работают два ключевых типа дофаминовых рецепторов: D1 и D2.",
            S["card_text"]),
        Spacer(1, 1.5*mm),
        Paragraph(
            "<b><font color='#00FFFF'>D1</font></b> реагируют на дешевую новизну: "
            "ленту Reels/TikTok, уведомления, сахар, фастфуд.",
            S["card_text"]),
        Spacer(1, 1*mm),
        Paragraph(
            "<b><font color='#00FFFF'>D2</font></b> отвечают за глубокую мотивацию, "
            "способность долго держать фокус и получать удовольствие от сложной работы.",
            S["card_text"]),
        Spacer(1, 1.5*mm),
        Paragraph(
            "Когда вы начинаете утро со смартфона, вы заливаете мозг дешевым дофамином. "
            "В ответ срабатывает защитный механизм — <b>рецепторная даунрегуляция</b> "
            "(снижение чувствительности D2). Обычная работа становится для мозга "
            "физически невыносимой и скучной.",
            S["card_text"]),
    ], bg=BG_CARD, left_color=CYAN, left_w=2.5, pad=8)

    card_cortisol = card([
        Paragraph(
            "<font color='#A855F7'>2. КОРТИЗОЛОВЫЙ ЗАХВАТ (БЛОКИРОВКА ПФК)</font>",
            S["card_title"]),
        Spacer(1, 1*mm),
        Paragraph(
            "Префронтальная кора — ваш \"внутренний гендиректор\", отвечающий за логику, "
            "стратегию и самоконтроль. При хроническом информационном шуме и стрессе "
            "активируется миндалевидное тело (амигдала). Уровень кортизола взлетает, "
            "буквально отключая префронтальную кору. Вы переходите в режим выживания: "
            "суетитесь, реагируете на мессенджеры, но не двигаетесь к целям.",
            S["card_text"]),
        Spacer(1, 1.5*mm),
        Paragraph(
            "<i>Эксперимент Бенджамина Либета доказал: мозг принимает импульсивное решение "
            "за миллисекунды до того, как вы его осознаете. Единственный способ вернуть "
            "контроль — использовать протоколы прерывания автоматизма, пока "
            "префронтальная кора еще активна.</i>",
            S["card_text"]),
    ], bg=BG_CARD, left_color=VIOLET, left_w=2.5, pad=8)

    return [
        Paragraph("РАЗДЕЛ 01 // ДИАГНОСТИКА", S["kicker"]),
        Paragraph("Почему вы просыпаетесь уже уставшим", S["h1"]),
        Spacer(1, 1*mm),

        card([
            Paragraph(
                "<font color='#00FFFF'><b>ЛЕНЬ — ЭТО НЕ СЛАБОСТЬ ХАРАКТЕРА. "
                "ЭТО СБОЙ НЕЙРОХИМИИ.</b></font>",
                S["card_title"]),
            Spacer(1, 1*mm),
            Paragraph(
                "Если вы спите по 7-8 часов, но просыпаетесь с ощущением "
                "\"тумана в голове\", откладываете важные задачи и чувствуете "
                "выгорание к 14:00 — проблема не в вашей силе воли. В вашем мозге "
                "прямо сейчас происходят два физиологических сбоя:",
                S["card_text"]),
        ], bg=BG_CARD_ALT, left_color=CYAN, left_w=3, pad=8),

        Spacer(1, 3*mm),
        card_d2,
        Spacer(1, 3*mm),
        card_cortisol,
        PageBreak(),
    ]


def page3_protocol1(S):
    """Страница 3 — Протокол №1: Золотые 90 минут."""

    step1 = card([
        Paragraph(
            "<font color='#00FFFF'><b>[01]</b></font>  "
            "<b>БЛОКАДА ЭКРАНА</b>  "
            "<font color='#7A7A90'>Первые 60 минут — 0% гаджетов</font>",
            S["step_title"]),
        Spacer(1, 1*mm),
        Paragraph(
            "Не берите телефон в руки сразу после будильника. В первые полчаса мозг "
            "переходит от тета- и альфа-волн к рабочим бета-волнам. Любое уведомление "
            "или скроллинг ленты мгновенно вызывает кортизоловый скачок и задает "
            "\"рваный\" паттерн внимания на весь день.",
            S["card_text"]),
    ], bg=BG_CARD, left_color=CYAN, left_w=2.5, pad=8)

    step2 = card([
        Paragraph(
            "<font color='#00FFFF'><b>[02]</b></font>  "
            "<b>АДЕНОЗИНОВОЕ ОКНО</b>  "
            "<font color='#7A7A90'>Отложите кофе на 90 минут</font>",
            S["step_title"]),
        Spacer(1, 1*mm),
        Paragraph(
            "Главная ошибка 90% людей — пить кофе сразу после подъема. "
            "В течение ночи в мозге остаются молекулы усталости — аденозин. "
            "Кофеин не дает вам энергию, он просто временно блокирует "
            "аденозиновые рецепторы.",
            S["card_text"]),
        Spacer(1, 1*mm),
        Paragraph(
            "Если выпить кофе в первые 15 минут после сна, естественная очистка "
            "аденозина останавливается. Как только действие кофеина закончится "
            "(~13:00-14:00), весь накопленный аденозин обрушится на рецепторы разом, "
            "вызывая жесткий дневной туман.",
            S["card_text"]),
        Spacer(1, 1*mm),
        Paragraph(
            "<b><font color='#00FFFF'>Правило:</font></b> Стакан воды с электролитами, "
            "а первая чашка кофе — строго через 90 минут после пробуждения.",
            S["card_text"]),
    ], bg=BG_CARD, left_color=VIOLET, left_w=2.5, pad=8)

    step3 = card([
        Paragraph(
            "<font color='#00FFFF'><b>[03]</b></font>  "
            "<b>ФОТОННЫЙ ИМПУЛЬС</b>  "
            "<font color='#7A7A90'>10 минут утреннего света</font>",
            S["step_title"]),
        Spacer(1, 1*mm),
        Paragraph(
            "Выйдите на балкон или улицу в первые 30 минут после подъема (даже в "
            "пасмурную погоду). Попадание естественных фотонов света на сетчатку глаза "
            "дает сигнал супрахиазматическому ядру мозга: \"День начался\". Это "
            "обеспечивает здоровый утренний пик фокуса и запускает таймер выработки "
            "мелатонина ровно через 14-16 часов для глубокого сна ночью.",
            S["card_text"]),
    ], bg=BG_CARD, left_color=CYAN, left_w=2.5, pad=8)

    return [
        Paragraph("ПРОТОКОЛ 01 // УТРЕННИЙ РЕСЕТ", S["kicker"]),
        Paragraph("Золотые 90 минут", S["h1"]),
        Paragraph(
            "<b><font color='#00FFFF'>КАК ЗАПУСТИТЬ МОЗГ БЕЗ ДОФАМИНОВОГО КРАША</font></b>",
            S["lead"]),
        Paragraph(
            "Ваше состояние в течение всего дня определяется тем, как вы проводите "
            "первые 90 минут после пробуждения. Внедрите этот алгоритм завтра утром:",
            S["body"]),
        Spacer(1, 1.5*mm),
        step1,
        Spacer(1, 2.5*mm),
        step2,
        Spacer(1, 2.5*mm),
        step3,
        PageBreak(),
    ]


def page4_protocol2(S):
    """Страница 4 — Протокол №2: Защита ПФК (Decision Matrix)."""

    halt = card([
        Paragraph(
            "<font color='#00FFFF'><b>[01]</b></font>  "
            "<b>СТОП-КРАН HALT</b>",
            S["step_title"]),
        Spacer(1, 1*mm),
        Paragraph(
            "Запретите себе принимать важные финансовые, рабочие или личные решения, "
            "если вы находитесь в одном из четырех состояний:",
            S["card_text"]),
        Spacer(1, 1*mm),
        Paragraph(
            "<b><font color='#00FFFF'>H</font></b>ungry (Голоден)  |  "
            "<b><font color='#00FFFF'>A</font></b>ngry (Раздражен)  |  "
            "<b><font color='#00FFFF'>L</font></b>onely (Одинок)  |  "
            "<b><font color='#00FFFF'>T</font></b>ired (Устал)",
            S["card_text"]),
        Spacer(1, 1*mm),
        Paragraph(
            "В этих точках вами управляет миндалевидное тело, а не разум.",
            S["card_text"]),
    ], bg=BG_CARD, left_color=CYAN, left_w=2.5, pad=8)

    rule2min = card([
        Paragraph(
            "<font color='#A855F7'><b>[02]</b></font>  "
            "<b>ПРАВИЛО 2 МИНУТ (Решения Типа С)</b>",
            S["step_title"]),
        Spacer(1, 1*mm),
        Paragraph(
            "Все мелкие операционные задачи, не несущие необратимых рисков, "
            "решаются за 120 секунд без обдумывания. Это освобождает рабочую память "
            "для действительно важных решений.",
            S["card_text"]),
    ], bg=BG_CARD, left_color=VIOLET, left_w=2.5, pad=8)

    algo = card([
        Paragraph(
            "<font color='#00FFFF'><b>[03]</b></font>  "
            "<b>АЛГОРИТМ 10 / 10 / 10</b>  "
            "<font color='#7A7A90'>Снятие тревожного паралича</font>",
            S["step_title"]),
        Spacer(1, 1*mm),
        Paragraph(
            "Если вы застряли перед сложным выбором и чувствуете стресс, "
            "задайте себе три вопроса:",
            S["card_text"]),
        Spacer(1, 1.5*mm),
        Paragraph(
            "<b><font color='#00FFFF'>[ ? ]</font></b> "
            "Как это решение повлияет на меня через <b>10 минут</b>?",
            S["card_text"]),
        Spacer(1, 0.5*mm),
        Paragraph(
            "<b><font color='#00FFFF'>[ ? ]</font></b> "
            "Через <b>10 месяцев</b>?",
            S["card_text"]),
        Spacer(1, 0.5*mm),
        Paragraph(
            "<b><font color='#00FFFF'>[ ? ]</font></b> "
            "Через <b>10 лет</b>?",
            S["card_text"]),
        Spacer(1, 1.5*mm),
        Paragraph(
            "<i>Этот прием за 15 секунд принудительно переключает кровоток "
            "от эмоциональной амигдалы обратно в префронтальную кору.</i>",
            S["card_text"]),
    ], bg=BG_CARD, left_color=CYAN, left_w=2.5, pad=8)

    return [
        Paragraph("ПРОТОКОЛ 02 // DECISION MATRIX", S["kicker"]),
        Paragraph("Защита префронтальной коры", S["h1"]),
        Paragraph(
            "<b><font color='#00FFFF'>КАК УБРАТЬ УСТАЛОСТЬ ОТ РЕШЕНИЙ "
            "(DECISION FATIGUE)</font></b>",
            S["lead"]),
        Paragraph(
            "Исследования показывают: среднестатистический человек принимает около "
            "35 000 решений в день. Каждое сомнение сжигает глюкозу и ресурс "
            "префронтальной коры. К вечеру наступает паралич воли (Decision Fatigue).",
            S["body"]),
        Paragraph(
            "Чтобы сохранить 100% энергии для главных задач, пропускайте рабочие "
            "вопросы через <b>3-ступенчатый фильтр SpectrMind</b>:",
            S["body"]),
        Spacer(1, 1*mm),
        halt,
        Spacer(1, 2.5*mm),
        rule2min,
        Spacer(1, 2.5*mm),
        algo,
        PageBreak(),
    ]


def page5_bridge(S):
    """Страница 5 — Мост к платному продукту (разрыв шаблона)."""

    problem1 = card([
        Paragraph(
            "<font color='#00FFFF'><b>[ X ] ПРОБЛЕМА С БАДАМИ И НООТРОПАМИ</b></font>",
            S["card_title"]),
        Spacer(1, 1*mm),
        Paragraph(
            "Большинство пьет добавки и использует пептиды хаотично, получая "
            "рецепторную толерантность и откат через 2 недели. Нужна точная схема "
            "циклирования (on/off periods) для роста BDNF (нейротрофического "
            "фактора мозга) без истощения ЦНС.",
            S["card_text"]),
    ], bg=BG_CARD, left_color=HexColor("#FF4444"), left_w=2.5, pad=8)

    problem2 = card([
        Paragraph(
            "<font color='#00FFFF'><b>[ X ] ПРОБЛЕМА СО СНОМ</b></font>",
            S["card_title"]),
        Spacer(1, 1*mm),
        Paragraph(
            "Можно лежать в кровати 8 часов, но если у вас нарушена фаза глубокого "
            "сна (NREM Stage 3), глимфатическая система не вымывает нейротоксины "
            "из мозга ночью.",
            S["card_text"]),
    ], bg=BG_CARD, left_color=HexColor("#FF4444"), left_w=2.5, pad=8)

    problem3 = card([
        Paragraph(
            "<font color='#00FFFF'><b>[ X ] ПРОБЛЕМА СО СРЫВАМИ</b></font>",
            S["card_title"]),
        Spacer(1, 1*mm),
        Paragraph(
            "Мягкий отказ от соцсетей не восстанавливает рецепторы D2 — нужен "
            "пошаговый 7-дневный протокол перезагрузки с защитой от отката "
            "в первые 48 часов.",
            S["card_text"]),
    ], bg=BG_CARD, left_color=HexColor("#FF4444"), left_w=2.5, pad=8)

    cta_card = card([
        Paragraph(
            "<font color='#00FFFF'><b>Именно для этого мы собрали полную "
            "закрытую документацию:</b></font>",
            S["card_title"]),
        Spacer(1, 2*mm),
        Paragraph(
            "<b><font color='#FFFFFF' size='13'>SPECTRMIND // НЕЙРО ПРОТОКОЛЫ</font></b>",
            S["card_text"]),
        Spacer(1, 1.5*mm),
        Paragraph(
            "Полная 21-дневная система перенастройки мозга с пошаговым внедрением.",
            S["card_text"]),
    ], bg=BG_CARD_ALT, left_color=CYAN, left_w=3, pad=10)

    return [
        Paragraph("РАЗДЕЛ 03 // РАЗРЫВ ШАБЛОНА", S["kicker"]),
        Paragraph("Почему одних утренних привычек недостаточно", S["h1"]),
        Paragraph(
            "Два протокола, которые вы только что изучили, остановят ежедневный "
            "слив энергии и уберут утреннюю разбитость уже в первые 24-48 часов.",
            S["lead"]),
        Paragraph(
            "Но будьте реалистами: если ваша дофаминовая система перегружалась годами, "
            "а сон перестал восстанавливать мозг на клеточном уровне — легкой коррекции "
            "режима хватит лишь на <b>20% от вашего реального потенциала</b>.",
            S["body"]),
        Paragraph(
            "Чтобы выйти на уровень <b>4 часов сверхглубокой работы (Flow State)</b> "
            "вместо 12 часов суеты, необходимо перенастроить все 5 фундаментов "
            "нейробиологии в единую систему:",
            S["body"]),
        Spacer(1, 2*mm),
        problem1,
        Spacer(1, 2.5*mm),
        problem2,
        Spacer(1, 2.5*mm),
        problem3,
        Spacer(1, 3.5*mm),
        cta_card,
        PageBreak(),
    ]


def page6_offer(S, image_path):
    """Страница 6 — Оффер с фото продукта и кнопкой Robokassa."""

    # Изображение продукта
    img_w = UW
    img_h = img_w * (571.0 / 1024.0)

    # Пункты оффера
    bullets = [
        "<b><font color='#00FFFF'>[ + ] Календари циклирования (90 дней):</font></b> "
        "точные протоколы синергии (пептиды Semax, Selank, P21, адаптогены) "
        "с расписанием on/off циклов без толерантности.",

        "<b><font color='#00FFFF'>[ + ] Дофаминовый детокс 2.0:</font></b> "
        "протокол выхода из информационной усталости и переход на "
        "4 часа глубокой работы вместо 12 часов суеты.",

        "<b><font color='#00FFFF'>[ + ] Архитектура сна:</font></b> "
        "синхронизация NREM 3 и REM фаз, тайминг света и суплементов "
        "для 100% энергии за 6-7 часов сна.",

        "<b><font color='#00FFFF'>[ + ] Матрица решений:</font></b> "
        "устранение decision fatigue, нейроперепрошивка установок "
        "и контроль префронтальной коры.",

        "<b><font color='#00FFFF'>[ + ] БОНУС: 7 дней в SPECTR CLUB:</font></b> "
        "закрытый клуб с микро-протоколами каждое утро в 8:00 "
        "и поддержкой комьюнити.",
    ]
    bullet_paras = [Paragraph(b, S["cta_item"]) for b in bullets]

    offer_card = Table([[
        [Paragraph("ЧТО ВЫ ПОЛУЧАЕТЕ В ПОЛНОЙ ВЕРСИИ:", S["card_title"]),
         Spacer(1, 1*mm)] + bullet_paras
    ]], colWidths=[UW])
    offer_card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, CYAN),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))

    price_block = Table([
        [Paragraph("<strike>3 990 \u20bd</strike>", S["price_old"])],
        [Paragraph("<b>1 990 \u20bd</b>", S["price_new"])],
        [Paragraph("Специальная цена для читателей гайда", S["price_note"])],
    ], colWidths=[UW])
    price_block.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    btn = ButtonLink(
        "ПОЛУЧИТЬ ПОЛНЫЙ НЕЙРО-ПРОТОКОЛ →",
        ROBOKASSA_URL,
        width=UW,
        height=11*mm,
        style=S["btn_text"],
        color=CYAN,
    )

    return [
        Spacer(1, 2*mm),
        Paragraph("СЛЕДУЮЩИЙ УРОВЕНЬ // ПОЛНАЯ СИСТЕМА", S["cta_badge"]),
        Spacer(1, 1.5*mm),
        Paragraph("НЕЙРО ПРОТОКОЛЫ", S["cta_title"]),
        Paragraph(
            "Вы изучили базовые принципы. Полная версия — это фундаментальная "
            "система перенастройки мозга на 21 день с пошаговым внедрением.",
            S["cta_sub"]),
        Spacer(1, 1*mm),
        RLImage(image_path, width=img_w, height=img_h),
        Spacer(1, 2.5*mm),
        offer_card,
        Spacer(1, 2.5*mm),
        price_block,
        Spacer(1, 2.5*mm),
        btn,
        Spacer(1, 1*mm),
        Paragraph(
            "Безопасная оплата картами (МИР, СБП, Visa/Mastercard) через Robokassa.<br/>"
            "Доступ к полной версии и закрытому клубу приходит на email мгновенно после оплаты.",
            S["cta_note"]),
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  СБОРКА
# ══════════════════════════════════════════════════════════════════════════════

def build(out_path: str, image_path: str):
    font = register_fonts()
    S = make_styles(font)

    doc = BaseDocTemplate(
        out_path, pagesize=A4,
        leftMargin=MX, rightMargin=MX, topMargin=MT, bottomMargin=MB,
        title="SpectrMind — Управление префронтальной корой",
        author="SpectrMind",
    )
    frame = Frame(MX, MB, UW, PAGE_H - MT - MB, id="main",
                  topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0)
    doc.addPageTemplates([PageTemplate(id="dark", frames=[frame],
                                       onPage=dark_bg(font))])

    story = []
    story += page1_cover(S)
    story += page2_diagnostics(S)
    story += page3_protocol1(S)
    story += page4_protocol2(S)
    story += page5_bridge(S)
    story += page6_offer(S, image_path)

    doc.build(story)
    print(f"[OK] PDF собран: {out_path}")


def main():
    image_path = os.path.abspath("product_cover.jpg")
    if not os.path.exists(image_path):
        print(f"[ERR] Не найден product_cover.jpg: {image_path}")
        return 1

    out_name = "SPECTR_Prefrontal_Protocol.pdf"
    build(out_name, image_path)

    # Копируем как freeguide.pdf для бота
    bot_path = os.path.abspath("freeguide.pdf")
    shutil.copyfile(out_name, bot_path)
    print(f"[OK] Скопирован для бота: {bot_path}")

    # Копируем в Marketing
    marketing = r"C:\Users\Admin\Desktop\Marketing\SpectrMind Guide\freeguide.pdf"
    if os.path.isdir(os.path.dirname(marketing)):
        shutil.copyfile(out_name, marketing)
        print(f"[OK] Скопирован в маркетинг: {marketing}")

    # Рендерим страницы для проверки
    try:
        import fitz
        doc = fitz.open(out_name)
        print(f"[OK] Страниц в PDF: {len(doc)}")
        for i in range(len(doc)):
            pix = doc[i].get_pixmap(dpi=150)
            pix.save(f"page_{i+1}.png")
            print(f"     page_{i+1}.png сохранен")
        doc.close()
    except ImportError:
        print("[WARN] PyMuPDF не установлен, рендер пропущен")

    return 0


if __name__ == "__main__":
    sys.exit(main())
