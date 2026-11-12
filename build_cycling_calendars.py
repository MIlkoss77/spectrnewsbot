"""Генератор PDF «SPECTR MIND // Календари циклирования (90 дней)».

Создаёт 6-страничный документ формата A4 в фирменной палитре Cyan Edition:
- Базовый холст: #020C16 (Obsidian Navy)
- Карточки: #071826 (Dark Cyan Glass)
- Рамки / сетка: #144460 (Blueprint Cyan)
- Акцент: #00E5FF (Electric Cyan)
- Текст: #F5FAFF (Ice White) и #8EB6CE (Silver Cyan)
"""
from __future__ import annotations

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
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ── Палитра Cyan Edition ─────────────────────────────────────────────────────
BG_OBSIDIAN = HexColor("#020C16")
BG_GLASS    = HexColor("#071826")
BG_BADGE    = HexColor("#0A2E48")
CYAN        = HexColor("#00E5FF")
BORDER      = HexColor("#144460")
GRID_LINE   = HexColor("#081A26")
TEXT_WHITE  = HexColor("#F5FAFF")
TEXT_MUTED  = HexColor("#8EB6CE")
TEXT_DARK   = HexColor("#020C16")
STATUS_ON   = HexColor("#063847")
STATUS_OFF  = HexColor("#101D2B")

PAGE_W, PAGE_H = A4
MX = 16 * mm
MT = 18 * mm
MB = 16 * mm
UW = PAGE_W - 2 * MX

OUTPUT_PDF = "SPECTR_90_Day_Cycling_Calendars.pdf"
FONT_DIR = r"C:\Windows\Fonts"


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
            pdfmetrics.registerFontFamily(
                fam, normal=fam, bold=fam + "-Bold", italic=fam + "-Italic"
            )
            return fam
    raise RuntimeError("Шрифт с кириллицей не найден")


def draw_page_bg(canvas, doc):
    """Тёмный фон Cyan Edition + швейцарская сетка + верхний/нижний колонтитул."""
    canvas.saveState()
    canvas.setFillColor(BG_OBSIDIAN)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Лёгкая координатная сетка
    canvas.setStrokeColor(GRID_LINE)
    canvas.setLineWidth(0.4)
    step = 18 * mm
    x = MX
    while x < PAGE_W - MX + 1:
        canvas.line(x, MB, x, PAGE_H - MT)
        x += step
    y = MB
    while y < PAGE_H - MT + 1:
        canvas.line(MX, y, PAGE_W - MX, y)
        y += step

    # Верхний колонтитул
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.6)
    canvas.line(MX, PAGE_H - 12 * mm, PAGE_W - MX, PAGE_H - 12 * mm)
    canvas.setFillColor(TEXT_MUTED)
    canvas.setFont("GSans", 7.5)
    canvas.drawString(MX, PAGE_H - 10 * mm, "SPECTR MIND // КАЛЕНДАРИ ЦИКЛИРОВАНИЯ (90 ДНЕЙ)")
    canvas.setFillColor(CYAN)
    canvas.drawRightString(PAGE_W - MX, PAGE_H - 10 * mm, f"ЛИСТ 0{doc.page} / 06")

    # Нижний колонтитул
    canvas.line(MX, 11 * mm, PAGE_W - MX, 11 * mm)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawString(MX, 7.5 * mm, "SPECTRMIND.RU  •  TG: @SPECTRNEWSBOT")
    canvas.drawRightString(PAGE_W - MX, 7.5 * mm, "КЛИНИЧЕСКИЙ АРХИВ // ON-OFF ПРОТОКОЛЫ")
    canvas.restoreState()


def make_styles(f: str) -> dict:
    return {
        "badge": ParagraphStyle(
            "badge", fontName=f + "-Bold", fontSize=8, leading=11,
            textColor=CYAN, alignment=TA_LEFT,
        ),
        "h1": ParagraphStyle(
            "h1", fontName=f + "-Bold", fontSize=21, leading=26,
            textColor=TEXT_WHITE, spaceAfter=3 * mm,
        ),
        "h2": ParagraphStyle(
            "h2", fontName=f + "-Bold", fontSize=14, leading=18,
            textColor=CYAN, spaceBefore=3 * mm, spaceAfter=2 * mm,
        ),
        "h3": ParagraphStyle(
            "h3", fontName=f + "-Bold", fontSize=11, leading=14,
            textColor=TEXT_WHITE, spaceBefore=2 * mm, spaceAfter=1.5 * mm,
        ),
        "body": ParagraphStyle(
            "body", fontName=f, fontSize=9.5, leading=14,
            textColor=TEXT_MUTED, spaceAfter=2.5 * mm,
        ),
        "body_white": ParagraphStyle(
            "body_white", fontName=f, fontSize=9.5, leading=14,
            textColor=TEXT_WHITE, spaceAfter=2 * mm,
        ),
        "cell_hdr": ParagraphStyle(
            "cell_hdr", fontName=f + "-Bold", fontSize=8.5, leading=11,
            textColor=CYAN, alignment=TA_LEFT,
        ),
        "cell": ParagraphStyle(
            "cell", fontName=f, fontSize=8.5, leading=11.5,
            textColor=TEXT_WHITE, alignment=TA_LEFT,
        ),
        "cell_muted": ParagraphStyle(
            "cell_muted", fontName=f, fontSize=8.2, leading=11,
            textColor=TEXT_MUTED, alignment=TA_LEFT,
        ),
        "cell_center": ParagraphStyle(
            "cell_center", fontName=f + "-Bold", fontSize=8.2, leading=11,
            textColor=CYAN, alignment=TA_CENTER,
        ),
        "warn": ParagraphStyle(
            "warn", fontName=f + "-Italic", fontSize=8.2, leading=11.5,
            textColor=TEXT_MUTED,
        ),
    }


def glass_card(paragraphs: list, width: float = UW, bg=BG_GLASS, border_color=BORDER) -> Table:
    t = Table([[paragraphs]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.8, border_color),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def styled_table(data: list, col_widths: list) -> Table:
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BG_BADGE),
        ("BACKGROUND", (0, 1), (-1, -1), BG_GLASS),
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def build_pdf(out_path: str = OUTPUT_PDF) -> str:
    font = register_fonts()
    s = make_styles(font)

    doc = BaseDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=MX,
        rightMargin=MX,
        topMargin=MT,
        bottomMargin=MB,
        title="SPECTR MIND — Календари циклирования (90 дней)",
        author="SPECTR MIND",
    )
    frame = Frame(MX, MB, UW, PAGE_H - MT - MB, id="main")
    doc.addPageTemplates([PageTemplate(id="dark", frames=[frame], onPage=draw_page_bg)])

    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # СТРАНИЦА 1: ВВЕДЕНИЕ И ФИЗИОЛОГИЯ ТОЛЕРАНТНОСТИ
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("ДОСЬЕ №01 // ПОЛНАЯ СИСТЕМА ЦИКЛИРОВАНИЯ", s["badge"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("КАЛЕНДАРИ ЦИКЛИРОВАНИЯ (90 ДНЕЙ)", s["h1"]))
    story.append(Paragraph(
        "Точные протоколы синергии для пептидов (<b>Semax, Selank, P21</b>), советских адаптогенов "
        "и дофамин-модуляторов с жёстким расписанием <b>ON / OFF циклов</b> без рецепторной толерантности и откатов.",
        s["body_white"],
    ))
    story.append(Spacer(1, 3 * mm))

    story.append(glass_card([
        Paragraph("ПОЧЕМУ 90% ЛЮДЕЙ ЛОВЯТ ОТКАТ ЧЕРЕЗ 14 ДНЕЙ?", s["h3"]),
        Paragraph(
            "При непрерывной стимуляции мозг включает защитный механизм — <b>downregulation</b> (снижение плотности "
            "и чувствительности рецепторов D2, TrkB и ГАМК-А). Вещество перестаёт действовать, дозировку хочется поднять, "
            "а при отмене наступает резкий спад когнитивной энергии.",
            s["body"],
        ),
        Paragraph(
            "<b>Золотое правило SpectrMind:</b> любое нейроактивное воздействие работает только в связке "
            "<i>импульс (ON) → окно тишины и ресинтеза (OFF)</i>. Пока вы в фазе OFF, нейроны закрепляют новые "
            "синаптические связи и восстанавливают чувствительность рецепторов.",
            s["body_white"],
        ),
    ]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("БАЗОВЫЕ УСЛОВИЯ ПЕРЕД СТАРТОМ 90-ДНЕВНОГО ЦИКЛА", s["h2"]))
    base_data = [
        [Paragraph("Фундамент", s["cell_hdr"]), Paragraph("Норма в течение всех 90 дней", s["cell_hdr"]), Paragraph("Зачем это нужно", s["cell_hdr"])],
        [Paragraph("Свет и сон", s["cell"]), Paragraph("10 мин дневного света до 09:00; сон 7–7.5 ч", s["cell_muted"]), Paragraph("Без фазы глубокого сна NREM 3 нейропластичность падает на 60%", s["cell_muted"])],
        [Paragraph("Гидратация", s["cell"]), Paragraph("30 мл воды на 1 кг веса + щепотка соли утром", s["cell_muted"]), Paragraph("Снимает микроспазм капилляров и улучшает доставку кислорода", s["cell_muted"])],
        [Paragraph("Кофеин", s["cell"]), Paragraph("Не раньше чем через 90 мин после подъёма", s["cell_muted"]), Paragraph("Исключает аденозиновый провал в 14:00 и перегрузку кортизола", s["cell_muted"])],
        [Paragraph("Режим ON/OFF", s["cell"]), Paragraph("Строгое соблюдение дней отдыха (Washout)", s["cell_muted"]), Paragraph("Обнуляет толерантность и сохраняет 100% отклик рецепторов", s["cell_muted"])],
    ]
    story.append(styled_table(base_data, [32 * mm, 64 * mm, UW - 96 * mm]))
    story.append(Spacer(1, 5 * mm))

    story.append(glass_card([
        Paragraph("ДИСКЛЕЙМЕР И БЕЗОПАСНОСТЬ", s["h3"]),
        Paragraph(
            "Материал носит исключительно информационно-образовательный характер и описывает принципы биохакинга "
            "и циклирования на базе научных публикаций. Не является индивидуальной медицинской рекомендацией или "
            "назначением лекарственных средств. Перед использованием пептидов и добавок проконсультируйтесь со специалистом.",
            s["warn"],
        ),
    ], bg=BG_BADGE))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # СТРАНИЦА 2: КАЛЕНДАРЬ №1 — ПЕПТИДНЫЙ СТЕК (SEMAX, SELANK, P21)
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("КАЛЕНДАРЬ №1 // НЕЙРОПЛАСТИЧНОСТЬ И ФОКУС", s["badge"]))
    story.append(Paragraph("ПЕПТИДНАЯ СИНЕРГИЯ: SEMAX + SELANK + P21", s["h1"]))
    story.append(Paragraph(
        "Схема разнесена по фазам так, чтобы фактор роста нейронов (BDNF) стимулировался волнами, "
        "а кортизол и тревожность балансировались без седации.",
        s["body"],
    ))

    pep_roles = [
        [Paragraph("Компонент", s["cell_hdr"]), Paragraph("Задача в стеке", s["cell_hdr"]), Paragraph("Окно приёма и ритм", s["cell_hdr"])],
        [Paragraph("<b>Semax</b>", s["cell"]), Paragraph("Рост BDNF и NGF, скорость мышления, устойчивость к гипоксии", s["cell_muted"]), Paragraph("Утро (08:00–11:00) перед главной задачей", s["cell_muted"])],
        [Paragraph("<b>Selank</b>", s["cell"]), Paragraph("ГАМК-баланс, снятие фоновой тревоги, ясный покой без сонливости", s["cell_muted"]), Paragraph("День / вторая половина (13:00–17:00)", s["cell_muted"])],
        [Paragraph("<b>P21</b>", s["cell"]), Paragraph("Усиление синаптогенеза и защита гиппокампа (подключается во 2-м цикле)", s["cell_muted"]), Paragraph("Утро (вместо или в паре с коротким курсом)", s["cell_muted"])],
    ]
    story.append(styled_table(pep_roles, [30 * mm, 88 * mm, UW - 118 * mm]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("РАСПИСАНИЕ ON / OFF НА 90 ДНЕЙ (3 МЕСЯЦА)", s["h2"]))
    pep_cal = [
        [Paragraph("Период", s["cell_hdr"]), Paragraph("Фаза", s["cell_hdr"]), Paragraph("Протокол стека", s["cell_hdr"]), Paragraph("Цель фазы", s["cell_hdr"])],
        [Paragraph("Недели 1–2\n(Дни 1–14)", s["cell"]), Paragraph("<b>ON</b>", s["cell_center"]), Paragraph("Semax (утро) + Selank (день)", s["cell"]), Paragraph("Мягкий запуск BDNF, адаптация рецепторов", s["cell_muted"])],
        [Paragraph("Неделя 3\n(Дни 15–21)", s["cell"]), Paragraph("OFF", s["cell_muted"]), Paragraph("Полная отмена пептидов (Washout)", s["cell_muted"]), Paragraph("Оценка базового тонуса, сброс толерантности", s["cell_muted"])],
        [Paragraph("Недели 4–5\n(Дни 22–35)", s["cell"]), Paragraph("<b>ON</b>", s["cell_center"]), Paragraph("Semax (утро) + Selank (при стрессе)", s["cell"]), Paragraph("Выход на пиковую глубину работы (Flow State)", s["cell_muted"])],
        [Paragraph("Неделя 6\n(Дни 36–42)", s["cell"]), Paragraph("OFF", s["cell_muted"]), Paragraph("Пауза от пептидов + Магний / Холин", s["cell_muted"]), Paragraph("Питание миелиновых оболочек и восстановление", s["cell_muted"])],
        [Paragraph("Недели 7–8\n(Дни 43–56)", s["cell"]), Paragraph("<b>ON+</b>", s["cell_center"]), Paragraph("P21 (утро) + Selank (день)", s["cell"]), Paragraph("Глубокий синаптогенез и закрепление памяти", s["cell_muted"])],
        [Paragraph("Неделя 9\n(Дни 57–63)", s["cell"]), Paragraph("OFF", s["cell_muted"]), Paragraph("Полный Washout (7 дней)", s["cell_muted"]), Paragraph("Закрепление устойчивости новых нейронных связей", s["cell_muted"])],
        [Paragraph("Недели 10–11\n(Дни 64–77)", s["cell"]), Paragraph("<b>ON</b>", s["cell_center"]), Paragraph("Semax + Selank (поддерживающий)", s["cell"]), Paragraph("Финальная волна когнитивной калибровки", s["cell_muted"])],
        [Paragraph("Неделя 12\n(Дни 78–90)", s["cell"]), Paragraph("OFF", s["cell_muted"]), Paragraph("Выход из курса (13 дней тишины)", s["cell_muted"]), Paragraph("Фиксация нового базового уровня энергии", s["cell_muted"])],
    ]
    story.append(styled_table(pep_cal, [28 * mm, 16 * mm, 56 * mm, UW - 100 * mm]))
    story.append(Spacer(1, 3 * mm))

    story.append(glass_card([
        Paragraph("ПРАВИЛО СОВМЕСТИМОСТИ", s["h3"]),
        Paragraph(
            "В дни приёма утреннего Semax не накладывайте сверху двойной кофеин и стимуляторы — "
            "это создаёт лишний адреналиновый шум и перегружает префронтальную кору.",
            s["body"],
        ),
    ]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # СТРАНИЦА 3: КАЛЕНДАРЬ №2 — СОВЕТСКИЕ АДАПТОГЕНЫ И СОСУДЫ
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("КАЛЕНДАРЬ №2 // НАСЛЕДИЕ КОСМИЧЕСКОЙ МЕДИЦИНЫ", s["badge"]))
    story.append(Paragraph("АДАПТОГЕНЫ И МИКРОЦИРКУЛЯЦИЯ МОЗГА", s["h1"]))
    story.append(Paragraph(
        "Адаптогены нельзя пить без перерыва месяцами: при постоянной стимуляции ось гипоталамус-гипофиз-надпочечники "
        "теряет эластичность. Используется пульсирующий ритм <b>5 дней ON (будни) / 2 дня OFF (выходные)</b> со сменой класса каждый месяц.",
        s["body"],
    ))

    adapt_data = [
        [Paragraph("Месяц", s["cell_hdr"]), Paragraph("Активный стек (5/2)", s["cell_hdr"]), Paragraph("Ритм недели", s["cell_hdr"]), Paragraph("Физиологический эффект", s["cell_hdr"])],
        [
            Paragraph("<b>Месяц 1</b>\nНедели 1–4", s["cell"]),
            Paragraph("Родиола розовая (утро) + Янтарная кислота (после завтрака)", s["cell"]),
            Paragraph("Пн–Пт: ON\nСб–Вс: OFF", s["cell_center"]),
            Paragraph("Антигипоксия, активация цикла Кребса, снятие спазма сосудов мозга", s["cell_muted"]),
        ],
        [
            Paragraph("<b>Месяц 2</b>\nНедели 5–8", s["cell"]),
            Paragraph("Ежовик гребенчатый (утро) + L-теанин / Магний треонат", s["cell"]),
            Paragraph("Пн–Пт: ON\nСб–Вс: OFF", s["cell_center"]),
            Paragraph("Отдых от стимулирующих адаптогенов, поддержка фактора роста нервов (NGF)", s["cell_muted"]),
        ],
        [
            Paragraph("<b>Месяц 3</b>\nНедели 9–11", s["cell"]),
            Paragraph("Левзея сафлоровидная (утро) + Экстракт чаги / CoQ10", s["cell"]),
            Paragraph("Пн–Пт: ON\nСб–Вс: OFF", s["cell_center"]),
            Paragraph("Восстановление митохондриальной выносливости без износа нервной системы", s["cell_muted"]),
        ],
        [
            Paragraph("<b>Финал</b>\nНеделя 12", s["cell"]),
            Paragraph("Полная пауза от всех адаптогенов", s["cell_muted"]),
            Paragraph("7 дней OFF", s["cell_muted"]),
            Paragraph("Проверка собственного утреннего кортизолового пика без поддержки", s["cell_muted"]),
        ],
    ]
    story.append(styled_table(adapt_data, [24 * mm, 52 * mm, 26 * mm, UW - 102 * mm]))
    story.append(Spacer(1, 4 * mm))

    story.append(glass_card([
        Paragraph("КОГДА ЯНТАРНАЯ КИСЛОТА РАБОТАЕТ ЛУЧШЕ ВСЕГО?", s["h3"]),
        Paragraph(
            "• Только после плотного завтрака (никогда на пустой желудок).\n"
            "• В дни высокой умственной нагрузки или после перелётов / недосыпа.\n"
            "• Не принимать после 16:00 — приток АТФ может сдвинуть время засыпания.",
            s["body"],
        ),
    ]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("ЧЕК-ЛИСТ СИМПТОМОВ, ПРИ КОТОРЫХ НУЖЕН ВНЕПЛАНОВЫЙ OFF (2 ДНЯ)", s["h3"]))
    story.append(Paragraph(
        "1. Учащённый пульс в покое утром (+8–10 уд/мин выше вашей нормы).<br/>"
        "2. Поверхностный прерывистый сон с пробуждениями в 03:00–04:00.<br/>"
        "3. Раздражительность к вечеру вместо ровного спокойного фокуса.",
        s["body_white"],
    ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # СТРАНИЦА 4: КАЛЕНДАРЬ №3 — ДОФАМИН И АДЕНОЗИН (D2 РЕСТАРТ)
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("КАЛЕНДАРЬ №3 // РЕСТАРТ ЭНЕРГИИ И СНА", s["badge"]))
    story.append(Paragraph("ДОФАМИНОВЫЕ РЕЦЕПТОРЫ D2 И АДЕНОЗИН", s["h1"]))
    story.append(Paragraph(
        "Главная причина потери мотивации и тяжести в 14:00 — конфликт кофеина с аденозином и дешёвый дофамин "
        "(ленты соцсетей в первые 60 минут утра). Этот календарь восстанавливает естественную тягу к сложной работе.",
        s["body"],
    ))

    dop_data = [
        [Paragraph("Элемент", s["cell_hdr"]), Paragraph("Схема циклирования", s["cell_hdr"]), Paragraph("Механизм защиты мозга", s["cell_hdr"])],
        [Paragraph("<b>Кофеин</b>", s["cell"]), Paragraph("Окно: строго 09:30–14:00.\nСб и Вс — 0 мг (или матча/декаф)", s["cell"]), Paragraph("Снимает блокаду аденозиновых рецепторов каждые выходные", s["cell_muted"])],
        [Paragraph("<b>L-Тирозин + B6</b>", s["cell"]), Paragraph("Только в дни пиковых задач (2–3 раза/нед) утром натощак", s["cell"]), Paragraph("Даёт сырьё для дофамина без ежедневной просадки тирозингидроксилазы", s["cell_muted"])],
        [Paragraph("<b>Цитиколин (CDP)</b>", s["cell"]), Paragraph("14 дней ON / 7 дней OFF\n(утро + обед)", s["cell"]), Paragraph("Поднимает ацетилхолин (память) и плотность D2-рецепторов", s["cell_muted"])],
        [Paragraph("<b>Магний + Глицин + L-Теанин</b>", s["cell"]), Paragraph("Ежедневно за 45 мин до сна\n(пауза 3 дня в конце месяца)", s["cell"]), Paragraph("Углубляет фазу NREM 3, запуская глимфатическую очистку мозга", s["cell_muted"])],
    ]
    story.append(styled_table(dop_data, [36 * mm, 52 * mm, UW - 88 * mm]))
    story.append(Spacer(1, 5 * mm))

    story.append(glass_card([
        Paragraph("ПРАВИЛО ВОСКРЕСНОГО ДОФАМИНОВОГО ГОЛОДАНИЯ", s["h3"]),
        Paragraph(
            "Раз в 7 дней (оптимально в воскресенье) устраивайте <b>6 часов без входящего информационного шума</b>: "
            "никаких коротких видео, новостей и мессенджеров. Прогулка, книга, живое общение. "
            "За 1 такой день базовый тонус рецепторов D2 восстанавливается на 18–25%.",
            s["body_white"],
        ),
    ], bg=BG_BADGE))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # СТРАНИЦА 5: СВОДНАЯ МАТРИЦА-ТРЕКЕР НА 12 НЕДЕЛЬ
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("ЕДИНЫЙ ТРЕКЕР // НЕДЕЛИ 1–12", s["badge"]))
    story.append(Paragraph("СВОДНАЯ 90-ДНЕВНАЯ КАРТА ПРОТОКОЛОВ", s["h1"]))
    story.append(Paragraph(
        "Распечатайте этот лист или сохраните на планшет — здесь сведены все три календаря по неделям.",
        s["body"],
    ))

    matrix_data = [
        [
            Paragraph("Неделя", s["cell_hdr"]),
            Paragraph("Пептидный стек", s["cell_hdr"]),
            Paragraph("Адаптогены (5/2)", s["cell_hdr"]),
            Paragraph("Дофамин / Цитиколин", s["cell_hdr"]),
        ],
        [Paragraph("Неделя 01", s["cell"]), Paragraph("<b>ON:</b> Semax + Selank", s["cell"]), Paragraph("<b>ON:</b> Родиола + Янт. к-та", s["cell_muted"]), Paragraph("<b>ON:</b> Цитиколин + Детокс", s["cell_muted"])],
        [Paragraph("Неделя 02", s["cell"]), Paragraph("<b>ON:</b> Semax + Selank", s["cell"]), Paragraph("<b>ON:</b> Родиола + Янт. к-та", s["cell_muted"]), Paragraph("<b>ON:</b> Цитиколин + Тирозин*", s["cell_muted"])],
        [Paragraph("Неделя 03", s["cell"]), Paragraph("OFF (Washout 7д)", s["cell_muted"]), Paragraph("<b>ON:</b> Родиола + Янт. к-та", s["cell_muted"]), Paragraph("OFF (пауза Цитиколин)", s["cell_muted"])],
        [Paragraph("Неделя 04", s["cell"]), Paragraph("<b>ON:</b> Semax + Selank", s["cell"]), Paragraph("<b>ON:</b> Родиола + Янт. к-та", s["cell_muted"]), Paragraph("<b>ON:</b> Цитиколин + Детокс", s["cell_muted"])],
        [Paragraph("Неделя 05", s["cell"]), Paragraph("<b>ON:</b> Semax + Selank", s["cell"]), Paragraph("<b>ON:</b> Ежовик + Теанин", s["cell_muted"]), Paragraph("<b>ON:</b> Цитиколин + Тирозин*", s["cell_muted"])],
        [Paragraph("Неделя 06", s["cell"]), Paragraph("OFF (Пауза + Магний)", s["cell_muted"]), Paragraph("<b>ON:</b> Ежовик + Теанин", s["cell_muted"]), Paragraph("OFF (пауза Цитиколин)", s["cell_muted"])],
        [Paragraph("Неделя 07", s["cell"]), Paragraph("<b>ON+:</b> P21 + Selank", s["cell"]), Paragraph("<b>ON:</b> Ежовик + Теанин", s["cell_muted"]), Paragraph("<b>ON:</b> Цитиколин + Детокс", s["cell_muted"])],
        [Paragraph("Неделя 08", s["cell"]), Paragraph("<b>ON+:</b> P21 + Selank", s["cell"]), Paragraph("<b>ON:</b> Ежовик + Теанин", s["cell_muted"]), Paragraph("<b>ON:</b> Цитиколин + Тирозин*", s["cell_muted"])],
        [Paragraph("Неделя 09", s["cell"]), Paragraph("OFF (Washout 7д)", s["cell_muted"]), Paragraph("<b>ON:</b> Левзея + Чага/Q10", s["cell_muted"]), Paragraph("OFF (пауза Цитиколин)", s["cell_muted"])],
        [Paragraph("Неделя 10", s["cell"]), Paragraph("<b>ON:</b> Semax + Selank", s["cell"]), Paragraph("<b>ON:</b> Левзея + Чага/Q10", s["cell_muted"]), Paragraph("<b>ON:</b> Цитиколин + Детокс", s["cell_muted"])],
        [Paragraph("Неделя 11", s["cell"]), Paragraph("<b>ON:</b> Semax + Selank", s["cell"]), Paragraph("<b>ON:</b> Левзея + Чага/Q10", s["cell_muted"]), Paragraph("<b>ON:</b> Цитиколин + Тирозин*", s["cell_muted"])],
        [Paragraph("Неделя 12", s["cell"]), Paragraph("OFF (Финал курса)", s["cell_muted"]), Paragraph("OFF (7 дней тишины)", s["cell_muted"]), Paragraph("OFF (Сверка базовой нормы)", s["cell_muted"])],
    ]
    story.append(styled_table(matrix_data, [24 * mm, 48 * mm, 52 * mm, UW - 124 * mm]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("* Тирозин применяется точечно: не чаще 2–3 раз в неделю в дни пиковой интеллектуальной нагрузки.", s["warn"]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # СТРАНИЦА 6: ФИНАЛЬНЫЕ ПРАВИЛА И БОНУС SPECTR CLUB
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("ФИНАЛЬНЫЙ ЛИСТ // ПОДДЕРЖКА И КЛУБ", s["badge"]))
    story.append(Paragraph("КОНТРОЛЬ ПРОГРЕССА И ЗАКРЫТЫЙ КЛУБ", s["h1"]))

    story.append(glass_card([
        Paragraph("КАК ОТСЛЕЖИВАТЬ РЕЗУЛЬТАТ КАЖДЫЕ 21 ДЕНЬ?", s["h3"]),
        Paragraph(
            "1. <b>Время утреннего входа в работу:</b> за сколько минут после пробуждения исчезает туман в голове.<br/>"
            "2. <b>Окно 14:00:</b> есть ли дневная сонливость и тяга к сладкому/кофе.<br/>"
            "3. <b>Длина непрерывного фокуса:</b> сколько минут вы способны решать сложную задачу без проверки телефона.",
            s["body_white"],
        ),
    ]))
    story.append(Spacer(1, 5 * mm))

    story.append(glass_card([
        Paragraph("ВАШ БОНУС: 7 ДНЕЙ В ЗАКРЫТОМ КЛУБЕ SPECTR CLUB", s["h2"]),
        Paragraph(
            "В стоимость вашей системы уже включён <b>7-дневный бонусный доступ</b> в закрытый Telegram-канал "
            "<b>SPECTR CLUB</b>: каждое утро в 08:00 вы получаете короткие микро-протоколы, разборы исследований "
            "и поддержку комьюнити.",
            s["body_white"],
        ),
        Paragraph(
            "Чтобы активировать персональный пропуск на 7 дней прямо сейчас, перейдите в нашего бота и нажмите Start:<br/>"
            "<b><font color='#00E5FF'>https://t.me/spectrnewsbot?start=trial7</font></b>",
            s["body_white"],
        ),
        Paragraph(
            "<i>Условия: доступ открывается ровно на 7 суток с момента активации. За 24 часа до конца бот пришлёт "
            "напоминание с возможностью продлить участие в клубе за 990 ₽/мес.</i>",
            s["warn"],
        ),
    ], bg=BG_BADGE, border_color=CYAN))
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph(
        "Вопросы по документам или доступу? Пишите в бот поддержки: <b>@spectrnewsbot</b>  •  Сайт: <b>spectrmind.ru</b>",
        s["body"],
    ))

    doc.build(story)
    print(f"PDF generated: {out_path}")
    return out_path


if __name__ == "__main__":
    build_pdf()
