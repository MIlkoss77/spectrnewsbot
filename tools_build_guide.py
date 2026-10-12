"""Сборка премиального PDF-гайда «Управление префронтальной корой» в стиле SpectrMind.

Стиль: Dark High-Tech Neuro-Lab (Deep Space #0A0A0F, Obsidian #13131A, Neon Cyan #00FFFF).
"""
from __future__ import annotations

import argparse
import os

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
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# --- Фирменная палитра SpectrMind -------------------------------------------
BG_SPACE = HexColor("#0A0A0F")         # Глубокий темный фон
BG_CARD = HexColor("#13131A")          # Фон карточек (Obsidian)
BG_CARD_LIGHT = HexColor("#1A1A24")    # Приподнятый слой
CYAN = HexColor("#00FFFF")             # Фирменный неоновый Cyan
CYAN_ELECTRIC = HexColor("#00D4D4")    # Вторичный циан
CYAN_DARK = HexColor("#0A2E2E")        # Темный циан для плашек
VIOLET = HexColor("#A855F7")           # Неоновый фиолетовый

TEXT_WHITE = HexColor("#FFFFFF")       # Заголовки H1-H3
TEXT_BODY = HexColor("#D0D0E0")        # Основной текст
TEXT_MUTED = HexColor("#7A7A90")       # Второстепенный текст
TEXT_DARK = HexColor("#0A0A0F")        # Текст на светлых кнопках

BORDER_SUBTLE = HexColor("#1E1E2A")    # Тонкие границы
BORDER_CYAN = HexColor("#00FFFF")      # Акцентные границы

PAGE_W, PAGE_H = A4
MARGIN_X = 18 * mm
MARGIN_TOP = 18 * mm
MARGIN_BOTTOM = 18 * mm
USABLE_W = PAGE_W - 2 * MARGIN_X

FONT_DIR = r"C:\Windows\Fonts"


def register_fonts() -> str:
    """Подключить шрифт с поддержкой кириллицы."""
    candidates = [
        ("GuideSans", "arial.ttf", "arialbd.ttf", "ariali.ttf"),
        ("GuideSans", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf"),
    ]
    for family, regular, bold, italic in candidates:
        paths = [os.path.join(FONT_DIR, name) for name in (regular, bold, italic)]
        if all(os.path.exists(path) for path in paths):
            pdfmetrics.registerFont(TTFont(family, paths[0]))
            pdfmetrics.registerFont(TTFont(family + "-Bold", paths[1]))
            pdfmetrics.registerFont(TTFont(family + "-Italic", paths[2]))
            pdfmetrics.registerFontFamily(
                family, normal=family, bold=family + "-Bold", italic=family + "-Italic"
            )
            return family
    raise RuntimeError("Не найден системный шрифт с кириллицей")


def build_styles(font: str) -> dict:
    return {
        "kicker": ParagraphStyle(
            "kicker", fontName=font + "-Bold", fontSize=8.5, leading=12,
            textColor=CYAN, spaceAfter=2.5 * mm,
        ),
        "h1": ParagraphStyle(
            "h1", fontName=font + "-Bold", fontSize=18, leading=22,
            textColor=TEXT_WHITE, spaceAfter=3 * mm, spaceBefore=0,
        ),
        "h2": ParagraphStyle(
            "h2", fontName=font + "-Bold", fontSize=12, leading=16,
            textColor=CYAN, spaceBefore=3.5 * mm, spaceAfter=2 * mm,
        ),
        "lead": ParagraphStyle(
            "lead", fontName=font, fontSize=9.5, leading=14,
            textColor=TEXT_BODY, spaceAfter=3 * mm,
        ),
        "body": ParagraphStyle(
            "body", fontName=font, fontSize=9, leading=13.5,
            textColor=TEXT_BODY, spaceAfter=2 * mm, alignment=TA_LEFT,
        ),
        "card_title": ParagraphStyle(
            "card_title", fontName=font + "-Bold", fontSize=10, leading=14,
            textColor=CYAN, spaceAfter=1.5 * mm,
        ),
        "card_text": ParagraphStyle(
            "card_text", fontName=font, fontSize=8.5, leading=12.5,
            textColor=TEXT_BODY, spaceAfter=0,
        ),
        "bullet_item": ParagraphStyle(
            "bullet_item", fontName=font, fontSize=9, leading=13,
            textColor=TEXT_BODY, spaceAfter=1.5 * mm,
        ),
        "note": ParagraphStyle(
            "note", fontName=font, fontSize=8, leading=11.5,
            textColor=TEXT_MUTED, spaceBefore=2 * mm,
        ),
        # Обложка
        "cover_badge": ParagraphStyle(
            "cover_badge", fontName=font + "-Bold", fontSize=8.5, leading=11,
            textColor=CYAN, alignment=TA_CENTER,
        ),
        "cover_title": ParagraphStyle(
            "cover_title", fontName=font + "-Bold", fontSize=28, leading=34,
            textColor=TEXT_WHITE, spaceAfter=4 * mm,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub", fontName=font, fontSize=11, leading=16,
            textColor=TEXT_BODY, spaceAfter=5 * mm,
        ),
        "cover_quote": ParagraphStyle(
            "cover_quote", fontName=font + "-Italic", fontSize=10, leading=15,
            textColor=TEXT_WHITE,
        ),
        "cover_footer": ParagraphStyle(
            "cover_footer", fontName=font + "-Bold", fontSize=8, leading=11,
            textColor=TEXT_MUTED, alignment=TA_CENTER,
        ),
        # CTA страница
        "cta_title": ParagraphStyle(
            "cta_title", fontName=font + "-Bold", fontSize=22, leading=27,
            textColor=TEXT_WHITE, spaceAfter=3 * mm,
        ),
        "cta_body": ParagraphStyle(
            "cta_body", fontName=font, fontSize=10, leading=15,
            textColor=TEXT_BODY, spaceAfter=3.5 * mm,
        ),
        "cta_item": ParagraphStyle(
            "cta_item", fontName=font, fontSize=9.5, leading=14,
            textColor=TEXT_WHITE, spaceAfter=2 * mm,
        ),
        "cta_price_old": ParagraphStyle(
            "cta_price_old", fontName=font, fontSize=11, leading=14,
            textColor=TEXT_MUTED, alignment=TA_CENTER,
        ),
        "cta_price_new": ParagraphStyle(
            "cta_price_new", fontName=font + "-Bold", fontSize=22, leading=26,
            textColor=CYAN, alignment=TA_CENTER, spaceBefore=1 * mm,
        ),
        "cta_button": ParagraphStyle(
            "cta_button", fontName=font + "-Bold", fontSize=13, leading=16,
            textColor=TEXT_DARK, alignment=TA_CENTER,
        ),
        "cta_note": ParagraphStyle(
            "cta_note", fontName=font, fontSize=8, leading=12,
            textColor=TEXT_MUTED, alignment=TA_CENTER, spaceBefore=4 * mm,
        ),
    }


def draw_dark_canvas(font: str):
    """Единый брендовый холст для всех страниц: темный фон, шапка, подвал."""
    def on_page(canvas, doc):
        canvas.saveState()
        # 1. Заливка глубоким фоном Deep Space
        canvas.setFillColor(BG_SPACE)
        canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)

        # 2. Декоративные угловые линии (стиль Hi-Tech / Sci-Fi)
        canvas.setStrokeColor(HexColor("#1A1A26"))
        canvas.setLineWidth(0.5)

        # Верхняя и нижняя границы
        if doc.page == 1:
            # Обложка: стилизованные углы
            canvas.line(MARGIN_X, PAGE_H - 12 * mm, MARGIN_X + 25 * mm, PAGE_H - 12 * mm)
            canvas.line(PAGE_W - MARGIN_X - 25 * mm, PAGE_H - 12 * mm, PAGE_W - MARGIN_X, PAGE_H - 12 * mm)
            canvas.line(MARGIN_X, 14 * mm, MARGIN_X + 25 * mm, 14 * mm)
            canvas.line(PAGE_W - MARGIN_X - 25 * mm, 14 * mm, PAGE_W - MARGIN_X, 14 * mm)
        else:
            # Контентные страницы: верхний и нижний колонтитулы
            # Верхний колонтитул
            canvas.setStrokeColor(BORDER_SUBTLE)
            canvas.setLineWidth(0.5)
            canvas.line(MARGIN_X, PAGE_H - 13 * mm, PAGE_W - MARGIN_X, PAGE_H - 13 * mm)

            canvas.setFont(font + "-Bold", 7.5)
            canvas.setFillColor(CYAN)
            canvas.drawString(MARGIN_X, PAGE_H - 10.5 * mm, "SPECTRMIND")

            canvas.setFont(font, 7.5)
            canvas.setFillColor(TEXT_MUTED)
            canvas.drawString(MARGIN_X + 23 * mm, PAGE_H - 10.5 * mm, "//   ПРАКТИЧЕСКИЙ НЕЙРОПРОТОКОЛ")
            canvas.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 10.5 * mm, "ПРЕФРОНТАЛЬНАЯ КОРА")

            # Нижний колонтитул
            canvas.line(MARGIN_X, 13 * mm, PAGE_W - MARGIN_X, 13 * mm)
            canvas.drawString(MARGIN_X, 9 * mm, "spectrmind.ru  ·  Научная база Stanford / MIT")

            canvas.setFont(font + "-Bold", 7.5)
            canvas.setFillColor(CYAN)
            canvas.drawRightString(PAGE_W - MARGIN_X, 9 * mm, f"PAGE 0{doc.page} // 07")

        canvas.restoreState()
    return on_page


def make_card(flowables: list, bg=BG_CARD, border_color=BORDER_SUBTLE,
              border_left_color=None, border_left_width=0, padding=10) -> Table:
    """Генерирует стилизованную темную карточку."""
    t = Table([[flowables]], colWidths=[USABLE_W])
    style = [
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.5, border_color),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
        ("LEFTPADDING", (0, 0), (-1, -1), padding + 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding + 2),
    ]
    if border_left_color and border_left_width > 0:
        style.append(("LINEBEFORE", (0, 0), (0, -1), border_left_width, border_left_color))
    t.setStyle(TableStyle(style))
    return t


class ButtonLink(Flowable):
    """Кнопка с активной ссылкой и неоновым свечением."""
    def __init__(self, text: str, url: str, width: float, height: float,
                 style: ParagraphStyle, color=CYAN):
        super().__init__()
        self.text = text
        self.url = url
        self.width = width
        self.height = height
        self.style = style
        self.color = color

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        # Заливка Cyan
        canvas.setFillColor(self.color)
        canvas.roundRect(0, 0, self.width, self.height, 4, stroke=0, fill=1)

        # Текст
        paragraph = Paragraph(self.text, self.style)
        _, para_height = paragraph.wrap(self.width, self.height)
        paragraph.drawOn(canvas, 0, (self.height - para_height) / 2.0)

        # Кликабельная ссылка
        if self.url:
            scale = getattr(canvas, "_currentMatrix", [1, 0, 0, 1, 0, 0])[0] or 1
            origin_x, origin_y = canvas.absolutePosition(0, 0)
            canvas.linkURL(
                self.url,
                (origin_x, origin_y, origin_x + self.width * scale, origin_y + self.height * scale),
                relative=0, thickness=0,
            )
        canvas.restoreState()


# --- Разделы документа -------------------------------------------------------

def cover(styles: dict) -> list:
    """Титульная страница: ультра-стильный киберпанк/нейро-лаб дизайн."""
    badge = Table(
        [[Paragraph("SPECTRMIND  ·  ПРАКТИЧЕСКИЙ ПРОТОКОЛ", styles["cover_badge"])]],
        colWidths=[80 * mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
            ("BOX", (0, 0), (-1, -1), 0.75, CYAN),
            ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]),
    )

    quote_card = make_card(
        [
            Paragraph("<font color='#00FFFF'><b>ЭКСПЕРИМЕНТ ЛИБЕТА (1983)</b></font>", styles["card_title"]),
            Spacer(1, 1.5 * mm),
            Paragraph(
                "Эксперимент Либета показал: мозг начинает готовить действие за 350–500 мс "
                "до того, как человек осознаёт своё решение. Это не отменяет свободу воли — "
                "это доказывает, почему управление мозгом начинается с <b>управления условиями</b>.",
                styles["cover_quote"],
            ),
        ],
        bg=BG_CARD,
        border_left_color=CYAN,
        border_left_width=3,
        padding=12,
    )

    footer_bar = Table(
        [[
            Paragraph("<font color='#00FFFF'>[ 01 ]</font> СТРУКТУРА ПФК", styles["cover_footer"]),
            Paragraph("<font color='#00FFFF'>[ 02 ]</font> ВЫВОД ЛИБЕТА", styles["cover_footer"]),
            Paragraph("<font color='#00FFFF'>[ 03 ]</font> 5 ПРОТОКОЛОВ", styles["cover_footer"]),
            Paragraph("<font color='#00FFFF'>[ 04 ]</font> СИСТЕМА", styles["cover_footer"]),
        ]],
        colWidths=[USABLE_W / 4] * 4,
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_SUBTLE),
            ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]),
    )

    return [
        Spacer(1, 35 * mm),
        badge,
        Spacer(1, 10 * mm),
        Paragraph(
            "Управление<br/><font color='#00FFFF'>префронтальной корой</font>",
            styles["cover_title"],
        ),
        Paragraph(
            "Как вернуть себе внимание, решения и эмоциональный контроль — "
            "пять практических протоколов, опирающихся на исследования нейробиологов, "
            "а не на абстрактную силу воли.",
            styles["cover_sub"],
        ),
        Spacer(1, 8 * mm),
        quote_card,
        Spacer(1, 20 * mm),
        footer_bar,
        PageBreak(),
    ]


def section_how_it_works(styles: dict) -> list:
    """Страница 2: Как работает префронтальная кора."""
    functions = [
        "<b><font color='#00FFFF'>[ + ] Рабочая память:</font></b> Удерживает в голове то, с чем вы работаете прямо сейчас: условие задачи, аргумент собеседника, ход мысли.",
        "<b><font color='#00FFFF'>[ + ] Торможение импульсов:</font></b> Позволяет не сказать лишнего, не открыть ленту соцсетей, притормозить автоматическую реакцию раздражения.",
        "<b><font color='#00FFFF'>[ + ] Переключение:</font></b> Даёт гибко выйти из одной задачи и войти в другую, не теряя концентрацию и нить рассуждения.",
        "<b><font color='#00FFFF'>[ + ] Связь с эмоциями:</font></b> Удерживает импульсы под контролем рассудка: не подавляет чувства, а выбирает взрослую реакцию.",
    ]
    func_flowables = [Paragraph(f, styles["bullet_item"]) for f in functions]

    box_functions = make_card(
        [
            Paragraph("ЧТО ОНА ДЕЛАЕТ КАЖДЫЙ ДЕНЬ", styles["card_title"]),
            Spacer(1, 1.5 * mm),
        ] + func_flowables,
        bg=BG_CARD,
        border_color=BORDER_SUBTLE,
        padding=9,
    )

    box_burnout = make_card(
        [
            Paragraph("<font color='#00FFFF'>ПОЧЕМУ ОНА «САДИТСЯ» ПЕРВОЙ</font>", styles["card_title"]),
            Spacer(1, 1 * mm),
            Paragraph(
                "Эта система метаболически самая дорогая в организме: она тратит колоссальное "
                "количество глюкозы и легко уступает более быстрым, древним реакциям амигдалы. "
                "Поэтому при недосыпе, стрессе и шуме первым пропадает контроль. "
                "<b>Это не «слабый характер» — это исчерпанный биологический ресурс.</b>",
                styles["card_text"],
            ),
        ],
        bg=BG_CARD,
        border_left_color=VIOLET,
        border_left_width=2.5,
        padding=9,
    )

    box_takeaway = make_card(
        [
            Paragraph(
                "<b>Практический вывод:</b> работать нужно не над самобичеванием, а над условиями. "
                "Пять протоколов ниже возвращают префронтальной коре то, что она теряет: "
                "сон, ясную структуру дня, толерантность к нагрузке и навык чистого переключения.",
                styles["card_text"],
            ),
        ],
        bg=BG_CARD_LIGHT,
        border_left_color=CYAN,
        border_left_width=2.5,
        padding=8,
    )

    return [
        Paragraph("РАЗДЕЛ 01 // НЕЙРОБИОЛОГИЯ ВНИМАНИЯ", styles["kicker"]),
        Paragraph("Как работает префронтальная кора", styles["h1"]),
        Paragraph(
            "Префронтальная кора (ПФК) — передняя часть лобных долей головного мозга. "
            "Это биологический центр исполнительных функций: именно она удерживает цель, "
            "гасит импульсивные желания, направляет внимание и связывает эмоции с действиями.",
            styles["lead"],
        ),
        Spacer(1, 1.5 * mm),
        box_functions,
        Spacer(1, 3.5 * mm),
        box_burnout,
        Spacer(1, 3 * mm),
        box_takeaway,
        PageBreak(),
    ]


def section_libet(styles: dict) -> list:
    """Страница 3: Эксперимент Либета."""
    points = [
        "<b><font color='#00FFFF'>01. Сигнал готовности не равен решению:</font></b> Потенциал готовности предсказывает движение статистически, а не детерминирует его жёстко.",
        "<b><font color='#00FFFF'>02. Момент осознания сложно зафиксировать:</font></b> Испытуемые оценивают тайминг задним числом, само внимание к часам вносит искажение.",
        "<b><font color='#00FFFF'>03. Существует «право вето»:</font></b> Позднейшие работы показали, что за 100–150 мс человек способен отменить запущенный импульс — и это прямая работа ПФК.",
        "<b><font color='#00FFFF'>04. Решение — это распределённый процесс:</font></b> Намерение складывается из среды, сна, уровня глюкозы и прошлого опыта.",
    ]
    points_flow = [Paragraph(p, styles["bullet_item"]) for p in points]

    box_points = make_card(
        [
            Paragraph("ЧТО НА САМОМ ДЕЛЕ ПОКАЗЫВАЮТ УТОЧНЕНИЯ", styles["card_title"]),
            Spacer(1, 1.5 * mm),
        ] + points_flow,
        bg=BG_CARD,
        border_color=BORDER_SUBTLE,
        padding=9,
    )

    box_conclusion = make_card(
        [
            Paragraph("<font color='#00FFFF'>ГЛАВНЫЙ ТЕЗИС ГАЙДА</font>", styles["card_title"]),
            Spacer(1, 1 * mm),
            Paragraph(
                "Если решение созревает заранее и на 90% зависит от биохимического фона, "
                "то надежнее менять не героический «момент выбора», а <b>среду и физиологию</b>. "
                "Свет, сон, тайминг кофеина и правила работы разгружают мозг лучше любой мотивации.",
                styles["card_text"],
            ),
        ],
        bg=BG_CARD,
        border_left_color=CYAN,
        border_left_width=3,
        padding=9,
    )

    return [
        Paragraph("РАЗДЕЛ 02 // ПРИРОДА ПРИНЯТИЯ РЕШЕНИЙ", styles["kicker"]),
        Paragraph("Что на самом деле показал эксперимент Либета", styles["h1"]),
        Paragraph(
            "В 1983 году Бенджамин Либет измерил активность моторных зон мозга и сопоставил её "
            "с моментом, когда испытуемый осознавал желание пошевелить пальцем. "
            "Сигнал в мозге возникал за несколько сотен миллисекунд ДО осознания решения.",
            styles["lead"],
        ),
        Paragraph(
            "Из этого часто делают ошибочный вывод: <i>«Мозг всё решил сам, свободы воли нет»</i>. "
            "Однако современная когнитивная наука даёт куда более глубокую картину:",
            styles["body"],
        ),
        Spacer(1, 1 * mm),
        box_points,
        Spacer(1, 3.5 * mm),
        box_conclusion,
        PageBreak(),
    ]


def format_protocol(number: int, title: str, mechanism: str, steps: list, styles: dict) -> list:
    """Форматирование одного протокола в виде компактного, плотного блока."""
    header = Paragraph(
        f"<font color='#00FFFF'><b>ПРОТОКОЛ #{number:02d}</b></font>  "
        f"<font color='#6B6B7B'>|</font>  "
        f"<font color='#FFFFFF'><b>{title}</b></font>",
        styles["card_title"],
    )

    mech_p = Paragraph(f"<i>Механизм:</i> {mechanism}", styles["card_text"])

    step_paras = []
    for idx, (name, desc) in enumerate(steps, 1):
        step_paras.append(
            Paragraph(
                f"<font color='#00FFFF'><b>[{idx:02d}]</b></font> "
                f"<b><font color='#FFFFFF'>{name}:</font></b> "
                f"<font color='#D0D0E0'>{desc}</font>",
                styles["bullet_item"],
            )
        )

    return [
        make_card(
            [header, Spacer(1, 1 * mm), mech_p, Spacer(1, 2 * mm)] + step_paras,
            bg=BG_CARD,
            border_left_color=CYAN if number % 2 != 0 else VIOLET,
            border_left_width=2.5,
            padding=8,
        )
    ]


def page_protocols_1_2(styles: dict) -> list:
    """Страница 4: Протоколы 1 и 2."""
    p1 = format_protocol(
        1,
        "Фундамент: сон и утренний свет",
        "ПФК перезагружается исключительно в фазах глубокого сна и настраивается фотонами света через циркадные рецепторы сетчатки (ipRGC).",
        [
            ("Фиксированный подъём", "Одно время в будни и выходные (дельта ±30 мин). Подъём задаёт ритм всего дня, а не время отхода ко сну."),
            ("Свет в первые 30 мин", "10–20 минут естественного дневного света на улице или у окна. Это якорь выработки утреннего кортизола и ночного мелатонина."),
            ("Отсрочка кофеина", "Первая чашка кофе — строго через 60–90 минут после подъёма. Это предотвратит дневной краш в 15:00."),
            ("Экранный стоп-час", "Первые 30 минут без соцсетей и рабочих чатов: чужие проблемы не должны захватывать оперативную память мозга."),
        ],
        styles,
    )

    p2 = format_protocol(
        2,
        "Фокус: одна задача и внешняя память",
        "Объём рабочей памяти — всего 3–4 объекта. Мультитаскинг физически разрушает фокус, заставляя ПФК непрерывно сжигать глюкозу на переключения.",
        [
            ("Блоки по 40–50 минут", "Одна задача, один открытый экран, телефон убран из поля зрения. Дольше 50 минут удержание внимания падает."),
            ("Бумага вместо головы", "Любая мысль или идея — сразу на внешний лист, а не в память. Так вы освобождаете ПФК для сложного анализа."),
            ("Правило 3 задач", "Максимум 3 ключевых приоритета на день. Всё остальное — во вторичный бэклог «когда-нибудь»."),
            ("Физическое переключение", "После каждого блока — 5 минут движения без экрана. Переход без паузы расщепляет фокус на весь день."),
        ],
        styles,
    )

    return [
        Paragraph("ПРАКТИЧЕСКИЕ ПРОТОКОЛЫ // ЧАСТЬ 1", styles["kicker"]),
        Paragraph("Биологический фундамент и фокус", styles["h1"]),
        p1[0],
        Spacer(1, 4 * mm),
        p2[0],
        PageBreak(),
    ]


def page_protocols_3_4(styles: dict) -> list:
    """Страница 5: Протоколы 3 и 4."""
    p3 = format_protocol(
        3,
        "Стресс: физиология раньше уговоров",
        "При всплеске кортизола и адреналина ПФК блокируется мгновенно. Логические уговоры не работают, пока тело находится в режиме тревоги.",
        [
            ("Физиологический вздох", "Два вдоха носом (один глубокий, второй довольный добор) + протяжный выдох ртом × 3 цикла. Снижает пульс за 30 секунд."),
            ("Тело важнее разговора", "Пока пульс выше нормы, запрещено вступать в споры, выяснения отношений и принимать решения."),
            ("Маркировка эмоции", "Назовите вслух: «Я раздражён из-за срыва дедлайна». Вербализация активирует кору и гасит активность амигдалы."),
            ("Тайм-аут 20 минут", "Острая фаза адреналинового выброса длится около 20 минут. Возвращайтесь к диалогу только после спада физиологии."),
        ],
        styles,
    )

    p4 = format_protocol(
        4,
        "Нагрузка: движение и выносливость",
        "Физическая активность стимулирует выработку BDNF (нейротрофического фактора мозга), ускоряя нейропластичность и устойчивость к нагрузкам.",
        [
            ("Движение до экрана", "10–15 минут прогулки или суставной разминки утром активируют кровоток префронтальной коры."),
            ("Вода вместо третьей чашки", "Когда внимание падает — сначала стакан прохладной воды и 10 приседаний, и только потом стимуляторы."),
            ("Дозированная сложность", "Берите задачу чуть выше привычного порога: слишком просто вызывает скуку, слишком сложно — саботаж."),
            ("Регулярность > рекорд", "Пять коротких 20-минутных тренировок в неделю дают втрое больше когнитивной стабильности, чем один подвиг в зале."),
        ],
        styles,
    )

    return [
        Paragraph("ПРАКТИЧЕСКИЕ ПРОТОКОЛЫ // ЧАСТЬ 2", styles["kicker"]),
        Paragraph("Стресс-менеджмент и когнитивная выносливость", styles["h1"]),
        p3[0],
        Spacer(1, 4 * mm),
        p4[0],
        PageBreak(),
    ]


def page_protocols_5_and_system(styles: dict) -> list:
    """Страница 6: Протокол 5 и удержание результата."""
    p5 = format_protocol(
        5,
        "Сознание: метакогнитивный контроль",
        "Способность отслеживать фокус своего внимания — тренируемый навык. Осознанность увеличивает паузу между внешним стимулом и реакцией.",
        [
            ("10 минут наблюдения", "Фокус на дыхании или телесных ощущениях. Внимание ушло — мягко вернули назад без самокритики."),
            ("Осознанность в быту", "Один раз в день полностью погрузитесь в простое действие (душ, еда, кофе) без наушников и телефона."),
            ("Рефрейминг тревоги", "Вместо подавления мысли «не думай об этом» переведите в задачу: «Что здесь является моим первым шагом?»."),
            ("Вечерняя выгрузка", "5 минут перед сном: выпишите на бумагу всё незавершённое. Освобождённая ПФК не будет прокручивать это ночью."),
        ],
        styles,
    )

    steps_in = [
        "<b><font color='#00FFFF'>Неделя 1:</font></b> Только сон и утренний свет. Никаких других изменений.",
        "<b><font color='#00FFFF'>Неделя 2:</font></b> Добавляются 45-минутные блоки фокуса и внешняя память.",
        "<b><font color='#00FFFF'>Неделя 3:</font></b> Внедряются физиологический вздох и тайм-ауты в стрессе.",
        "<b><font color='#00FFFF'>Неделя 4:</font></b> Утреннее движение и ежедневная вечерняя выгрузка.",
    ]
    steps_flow = [Paragraph(s, styles["bullet_item"]) for s in steps_in]

    box_system = make_card(
        [
            Paragraph("КАК ВНЕДРЯТЬ СИСТЕМУ: ПЛАН ПО НЕДЕЛЯМ", styles["card_title"]),
            Spacer(1, 1 * mm),
        ] + steps_flow,
        bg=BG_CARD,
        border_left_color=CYAN,
        border_left_width=2.5,
        padding=7,
    )

    box_disclaimer = make_card(
        [
            Paragraph(
                "<b>Важный дисклеймер:</b> Гайд носит прикладной образовательный характер и не заменяет "
                "медицинскую помощь при клинической депрессии, тревожных расстройствах или хронической "
                "бессоннице. Если симптомы длятся месяцами — обратитесь к профильному специалисту.",
                styles["note"],
            ),
        ],
        bg=BG_CARD,
        border_color=BORDER_SUBTLE,
        padding=6,
    )

    return [
        Paragraph("ПРАКТИЧЕСКИЕ ПРОТОКОЛЫ // ЧАСТЬ 3", styles["kicker"]),
        Paragraph("Управление вниманием и удержание системы", styles["h1"]),
        p5[0],
        Spacer(1, 3.5 * mm),
        box_system,
        Spacer(1, 2.5 * mm),
        box_disclaimer,
        PageBreak(),
    ]


def cta_page(styles: dict, link: str, price: str, product: str) -> list:
    """Страница 7: Высококонверсионный оффер на полный нейрогайд."""
    features = [
        "<b><font color='#00FFFF'>[ + ] 5 углубленных протоколов:</font></b> Детокс дофамина, архитектура сна, матрица быстрых решений, стресс-ресет и когнитивное самопрограммирование.",
        "<b><font color='#00FFFF'>[ + ] Пошаговый календарь на 21 день:</font></b> Точный график ввода привычек без риска сорваться на 3-й день.",
        "<b><font color='#00FFFF'>[ + ] Разборы срывов:</font></b> Алгоритм возвращения в рабочее состояние, если график сбился.",
        "<b><font color='#00FFFF'>[ + ] Безопасный стек добавок:</font></b> Дозировки, время приёма и научная база препаратов аптечного сегмента РФ.",
        "<b><font color='#00FFFF'>[ + ] Доступ в закрытый клуб на 7 дней:</font></b> Микро-протоколы каждое утро и комьюнити единомышленников.",
    ]
    feat_flow = [Paragraph(f, styles["cta_item"]) for f in features]

    offer_card = make_card(
        [
            Paragraph("<font color='#00FFFF'>ЧТО ВХОДИТ В ПОЛНУЮ ВЕРСИЮ</font>", styles["card_title"]),
            Spacer(1, 2 * mm),
        ] + feat_flow,
        bg=BG_CARD,
        border_left_color=CYAN,
        border_left_width=3,
        padding=11,
    )

    price_card = Table(
        [
            [Paragraph("<strike>3 990 ₽</strike>", styles["cta_price_old"])],
            [Paragraph(f"<b>{price}</b>", styles["cta_price_new"])],
            [Paragraph("<font color='#A0A0B0'>Специальное предложение первого потока</font>", styles["cta_note"])],
        ],
        colWidths=[USABLE_W],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_CARD_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_SUBTLE),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
        ]),
    )

    btn = ButtonLink(
        "ПЕРЕЙТИ К ПОЛНОМУ ПРОТОКОЛУ →",
        link,
        width=USABLE_W,
        height=14 * mm,
        style=styles["cta_button"],
        color=CYAN,
    )

    return [
        Spacer(1, 10 * mm),
        Paragraph("СЛЕДУЮЩИЙ УРОВЕНЬ // ПОЛНАЯ СИСТЕМА", styles["kicker"]),
        Paragraph("Полный нейрогайд SpectrMind", styles["cta_title"]),
        Paragraph(
            "Этот мини-гайд — базовая реанимация ресурса. Полный протокол — это законченная "
            "система глубокой перенастройки сна, дофаминовых рецепторов и ясности ума.",
            styles["cta_body"],
        ),
        Spacer(1, 2 * mm),
        offer_card,
        Spacer(1, 5 * mm),
        price_card,
        Spacer(1, 5 * mm),
        btn,
        Spacer(1, 3 * mm),
        Paragraph(
            "Безопасная оплата картами (МИР, СБП, Visa/Mastercard) на защищённой странице Robokassa.<br/>"
            "Доступ к полной версии и клубу приходит на почту сразу после успешной оплаты.",
            styles["cta_note"],
        ),
    ]


def build_pdf(out_path: str, link: str, price: str = "1 990 ₽",
              product: str = "SpectrMind: Нейро-Хакер (5 протоколов)") -> None:
    font = register_fonts()
    styles = build_styles(font)

    doc = BaseDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title="SpectrMind — Управление префронтальной корой",
        author="SpectrMind",
        subject="Практический протокол управления вниманием и мозгом",
    )

    frame = Frame(
        MARGIN_X, MARGIN_BOTTOM,
        USABLE_W, PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
        id="normal",
        topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0,
    )

    page_template = PageTemplate(id="dark_page", frames=[frame], onPage=draw_dark_canvas(font))
    doc.addPageTemplates([page_template])

    story = []
    story += cover(styles)
    story += section_how_it_works(styles)
    story += section_libet(styles)
    story += page_protocols_1_2(styles)
    story += page_protocols_3_4(styles)
    story += page_protocols_5_and_system(styles)
    story += cta_page(styles, link, price, product)

    doc.build(story)
    print(f"[OK] Сгенерирован премиальный PDF: {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Сборка красивого PDF-гайда SpectrMind")
    parser.add_argument("--out", default="prefrontal_guide.pdf")
    parser.add_argument("--link", default="", help="Ссылка на оплату")
    parser.add_argument("--price", default="1 990 ₽")
    parser.add_argument("--product", default="SpectrMind: Полный нейрогайд")
    args = parser.parse_args()

    # Ссылка по умолчанию из файла или на сайт
    link = args.link
    if not link:
        link_file = os.path.join(os.path.dirname(__file__), ".selfcheck_state", "guide_link.txt")
        if os.path.exists(link_file):
            with open(link_file, encoding="utf-8") as f:
                link = f.read().strip()
        if not link:
            link = "https://spectrmind.ru/#pricing"

    build_pdf(args.out, link, args.price, args.product)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
