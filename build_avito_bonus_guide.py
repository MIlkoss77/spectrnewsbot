"""Сборка 4-страничного бонусного гайда за отзыв: SPECTR_AntiStress_Bonus.pdf.

Дополнение к базовому гайду SPECTR_Prefrontal_Protocol.pdf:
- Страница 1: Обложка «Экстренный анти-стресс и сброс кортизола»
- Страница 2: Протокол 01 — Аварийный тормоз тревоги за 120 секунд (днём)
- Страница 3: Протокол 02 — Вечерний щит от «второго дыхания» перед сном
- Страница 4: Кликабельные ссылки на соцсети и бот + 1-клик оплата полного курса
"""
from __future__ import annotations

import os
import shutil
import sys

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image as RLImage,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from build_6page_guide import (
    BG_CARD,
    BG_CARD_ALT,
    BORDER,
    CYAN,
    INSTAGRAM_URL,
    MB,
    MT,
    MX,
    PAGE_H,
    ROBOKASSA_URL,
    TG_CHANNEL_URL,
    UW,
    VIOLET,
    YOUTUBE_URL,
    ButtonLink,
    card,
    dark_bg,
    make_styles,
    register_fonts,
)

TG_BOT_URL = "https://t.me/spectrnewsbot?start=avito_bonus"
OUT_PDF = "SPECTR_AntiStress_Bonus.pdf"


def page1_cover(S: dict) -> list:
    """Страница 1 — Обложка бонусного мини-гайда."""
    badge = Table(
        [[Paragraph("SPECTRMIND  //  БОНУСНЫЙ ПРОТОКОЛ", S["cover_badge"])]],
        colWidths=[88 * mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
            ("BOX", (0, 0), (-1, -1), 0.75, CYAN),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]),
    )

    info_card = card([
        Paragraph(
            "<font color='#00FFFF'>Дополнение к базовому гайду «Управление префронтальной корой».</font>",
            S["card_text"],
        ),
        Spacer(1, 2 * mm),
        Paragraph("Время чтения: 3 минуты. Применяется сразу в момент стресса или перед сном.", S["card_text"]),
        Paragraph(
            "База: физиология блуждающего нерва, исследования Stanford и Института мозга им. Бехтеревой.",
            S["card_text"],
        ),
    ], bg=BG_CARD, left_color=CYAN, left_w=2.5, pad=10)

    return [
        Spacer(1, 45 * mm),
        badge,
        Spacer(1, 14 * mm),
        Paragraph(
            "ЭКСТРЕННЫЙ<br/><font color='#00FFFF'>АНТИ-СТРЕСС</font>",
            S["cover_title"],
        ),
        Paragraph(
            "Сброс кортизола за 120 секунд и вечерняя разгрузка мозга: "
            "как быстро остановить тревогу днём и отключить поток мыслей перед сном",
            S["cover_sub"],
        ),
        Spacer(1, 18 * mm),
        info_card,
        PageBreak(),
    ]


def page2_acute_reset(S: dict) -> list:
    """Страница 2 — Протокол 01: Снятие острой тревоги за 120 секунд."""
    why_card = card([
        Paragraph(
            "<font color='#00FFFF'><b>ПОЧЕМУ СОВЕТ «ПРОСТО УСПОКОЙСЯ» НЕ РАБОТАЕТ</b></font>",
            S["card_title"],
        ),
        Spacer(1, 1 * mm),
        Paragraph(
            "Когда амигдала уже выбросила адреналин и кортизол, логические центры префронтальной коры "
            "временно подавлены. Уговаривать себя мыслями бесполезно — переключать нервную систему "
            "нужно напрямую через тело и блуждающий нерв.",
            S["card_text"],
        ),
    ], bg=BG_CARD_ALT, left_color=CYAN, left_w=3, pad=8)

    step1 = card([
        Paragraph(
            "<font color='#00FFFF'><b>[01]</b></font>  "
            "<b>ДВОЙНОЙ ФИЗИОЛОГИЧЕСКИЙ ВЗДОХ</b>  "
            "<font color='#7A7A90'>3 повтора • 45 секунд</font>",
            S["step_title"],
        ),
        Spacer(1, 1 * mm),
        Paragraph(
            "Сделайте глубокий вдох носом, затем без паузы ещё один короткий «довдох» носом до максимума "
            "(чтобы раскрылись спавшиеся от стресса альвеолы лёгких) и очень медленный плавный выдох через рот на 8–10 секунд.",
            S["card_text"],
        ),
        Spacer(1, 1 * mm),
        Paragraph(
            "<b><font color='#00FFFF'>Эффект:</font></b> Удлинённый выдох напрямую стимулирует блуждающий нерв "
            "и снижает частоту пульса уже после 2–3 циклов.",
            S["card_text"],
        ),
    ], bg=BG_CARD, left_color=CYAN, left_w=2.5, pad=8)

    step2 = card([
        Paragraph(
            "<font color='#A855F7'><b>[02]</b></font>  "
            "<b>ХОЛОДОВОЙ РЕФЛЕКС (ЗОНА 15°C)</b>  "
            "<font color='#7A7A90'>20–30 секунд</font>",
            S["step_title"],
        ),
        Spacer(1, 1 * mm),
        Paragraph(
            "Умойте лицо холодной водой (~15°C) или приложите прохладный компресс к области лба, висков "
            "и переносицы на 20–30 секунд с короткой задержкой дыхания.",
            S["card_text"],
        ),
        Spacer(1, 1 * mm),
        Paragraph(
            "<b><font color='#A855F7'>Эффект:</font></b> Охлаждение ветвей тройничного нерва запускает "
            "окулокардиальный рефлекс — вегетативная система за минуту сбрасывает режим «бей или беги».",
            S["card_text"],
        ),
    ], bg=BG_CARD, left_color=VIOLET, left_w=2.5, pad=8)

    step3 = card([
        Paragraph(
            "<font color='#00FFFF'><b>[03]</b></font>  "
            "<b>ПАНОРАМНАЯ РАСФОКУСИРОВКА ЗРЕНИЯ</b>  "
            "<font color='#7A7A90'>60 секунд</font>",
            S["step_title"],
        ),
        Spacer(1, 1 * mm),
        Paragraph(
            "Оторвите взгляд от телефона или монитора. Смотрите прямо перед собой вдаль и, не двигая головой, "
            "максимально расширьте боковое периферическое зрение — удерживайте такой «широкий» обзор 1 минуту.",
            S["card_text"],
        ),
        Spacer(1, 1 * mm),
        Paragraph(
            "<b><font color='#00FFFF'>Эффект:</font></b> Туннельный фокус жёстко связан с выбросом норадреналина. "
            "Панорамное зрение подаёт в ствол мозга физиологический сигнал безопасности.",
            S["card_text"],
        ),
    ], bg=BG_CARD, left_color=CYAN, left_w=2.5, pad=8)

    return [
        Paragraph("ПРОТОКОЛ 01 // ЭКСТРЕННЫЙ СБРОС", S["kicker"]),
        Paragraph("Как остановить тревогу за 120 секунд", S["h1"]),
        Spacer(1, 1 * mm),
        why_card,
        Spacer(1, 3 * mm),
        step1,
        Spacer(1, 2.5 * mm),
        step2,
        Spacer(1, 2.5 * mm),
        step3,
        PageBreak(),
    ]


def page3_evening_shield(S: dict) -> list:
    """Страница 3 — Протокол 02: Вечерняя разгрузка и отключение тревоги перед сном."""
    step1 = card([
        Paragraph(
            "<font color='#00FFFF'><b>[01]</b></font>  "
            "<b>КОФЕИНОВЫЙ СТОП ЗА 9 ЧАСОВ</b>  "
            "<font color='#7A7A90'>Защита фазы глубокого сна</font>",
            S["step_title"],
        ),
        Spacer(1, 1 * mm),
        Paragraph(
            "Последний кофе, крепкий чай или горький шоколад — минимум за 8–10 часов до сна. "
            "Период полувыведения кофеина составляет 5–7 часов: даже если вы спокойно засыпаете вечером, "
            "остаток стимулятора урезает фазу глубокого восстановления (NREM 3) на 20–30%, и утром снова нет ресурса.",
            S["card_text"],
        ),
    ], bg=BG_CARD, left_color=CYAN, left_w=2.5, pad=8)

    step2 = card([
        Paragraph(
            "<font color='#A855F7'><b>[02]</b></font>  "
            "<b>НИЖНИЙ ТЁПЛЫЙ СВЕТ ПОСЛЕ 21:00</b>  "
            "<font color='#7A7A90'>Синхронизация мелатонина</font>",
            S["step_title"],
        ),
        Spacer(1, 1 * mm),
        Paragraph(
            "За 60–90 минут до сна выключайте яркое верхнее освещение. Рецепторы в нижней части сетчатки "
            "считывают свет сверху как дневное небо и блокируют выброс мелатонина. "
            "Перейдите на приглушённую настольную лампу или торшер и включите ночной фильтр на экранах.",
            S["card_text"],
        ),
    ], bg=BG_CARD, left_color=VIOLET, left_w=2.5, pad=8)

    step3 = card([
        Paragraph(
            "<font color='#00FFFF'><b>[03]</b></font>  "
            "<b>ВЫГРУЗКА ОПЕРАТИВНОЙ ПАМЯТИ</b>  "
            "<font color='#7A7A90'>3 минуты на бумаге перед сном</font>",
            S["step_title"],
        ),
        Spacer(1, 1 * mm),
        Paragraph(
            "За полчаса до сна выпишите на бумагу 3 незавершённые задачи или тревожащие мысли, которые крутятся "
            "в голове, и напротив каждой — конкретный первый шаг на завтра.",
            S["card_text"],
        ),
        Spacer(1, 1 * mm),
        Paragraph(
            "<b><font color='#00FFFF'>Эффект Зейгарник:</font></b> Пока незакрытая задача висит в памяти, "
            "префронтальная кора держит фоновый сигнал тревоги. Перенос на лист отключает «мысленную жвачку» за 3 минуты.",
            S["card_text"],
        ),
    ], bg=BG_CARD, left_color=CYAN, left_w=2.5, pad=8)

    bridge_note = card([
        Paragraph(
            "<font color='#00FFFF'><b>ГЛАВНЫЙ ПРИНЦИП УСТОЙЧИВОСТИ</b></font>",
            S["card_title"],
        ),
        Spacer(1, 1 * mm),
        Paragraph(
            "Техники выше гасят острый стресс здесь и сейчас. Но чтобы тревожность и «мозговой туман» "
            "перестали возвращаться, нужна единая настройка дофаминовых рецепторов, глубокого сна и ритма решений.",
            S["card_text"],
        ),
    ], bg=BG_CARD_ALT, left_color=CYAN, left_w=3, pad=8)

    return [
        Paragraph("ПРОТОКОЛ 02 // ВЕЧЕРНЯЯ РАЗГРУЗКА", S["kicker"]),
        Paragraph("Как убрать «второе дыхание» перед сном", S["h1"]),
        Paragraph(
            "Знакомый сценарий: днём сил нет, а после 22:00 голова внезапно включается, прокручивает дела "
            "и не даёт уснуть. Это вечерний рассинхрон кортизола и мелатонина. Три шага разгружают нервную систему за вечер:",
            S["body"],
        ),
        Spacer(1, 1.5 * mm),
        step1,
        Spacer(1, 2.5 * mm),
        step2,
        Spacer(1, 2.5 * mm),
        step3,
        Spacer(1, 3 * mm),
        bridge_note,
        PageBreak(),
    ]


def page4_social_and_offer(S: dict, image_path: str) -> list:
    """Страница 4 — Соцсети проекта + полный курс с 1-клик оплатой."""
    card_pad = 7
    inner_w = UW - 2 * (card_pad + 2)
    gap = 2.5 * mm
    soc_w = (inner_w - 2 * gap) / 3.0
    soc_h = 8.5 * mm
    soc_buttons = Table(
        [[
            ButtonLink(
                "Telegram-канал  →", TG_CHANNEL_URL,
                width=soc_w, height=soc_h, style=S["soc_btn_tg"],
                color=BG_CARD_ALT, border_color=CYAN, border_width=0.9, radius=4,
            ),
            "",
            ButtonLink(
                "Instagram  →", INSTAGRAM_URL,
                width=soc_w, height=soc_h, style=S["soc_btn"],
                color=BG_CARD, border_color=HexColor("#2C2C3E"), border_width=0.7, radius=4,
            ),
            "",
            ButtonLink(
                "YouTube  →", YOUTUBE_URL,
                width=soc_w, height=soc_h, style=S["soc_btn"],
                color=BG_CARD, border_color=HexColor("#2C2C3E"), border_width=0.7, radius=4,
            ),
        ]],
        colWidths=[soc_w, gap, soc_w, gap, soc_w],
        style=TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]),
    )

    bot_btn = ButtonLink(
        "TELEGRAM-БОТ С БЕСПЛАТНЫМИ МАТЕРИАЛАМИ (@spectrnewsbot)  →",
        TG_BOT_URL,
        width=inner_w,
        height=8 * mm,
        style=S["soc_btn_tg"],
        color=BG_CARD,
        border_color=BORDER,
        border_width=0.7,
        radius=4,
    )

    social_card = card([
        Paragraph("ЕЖЕДНЕВНЫЕ НЕЙРО-РАЗБОРЫ В НАШИХ СОЦСЕТЯХ", S["soc_label"]),
        Spacer(1, 1 * mm),
        Paragraph(
            "В Telegram-канале <b>@ruspectrmind</b> каждый день в 09:00 МСК выходят короткие прикладные "
            "протоколы по сну, сосудам мозга и управлению стрессом. Подписывайтесь, чтобы забирать свежие разборы:",
            S["card_text"],
        ),
        Spacer(1, 2 * mm),
        soc_buttons,
        Spacer(1, 1.5 * mm),
        bot_btn,
        Spacer(1, 1.5 * mm),
        Paragraph("TG: @ruspectrmind  •  IG: @spectrmind.ru  •  YT: @spectrmind  •  Бот: @spectrnewsbot", S["soc_handles"]),
    ], bg=BG_CARD, border=BORDER, left_color=CYAN, left_w=2.5, pad=card_pad)

    divider = Table(
        [[""]],
        colWidths=[UW],
        rowHeights=[0.4],
        style=TableStyle([
            ("LINEABOVE", (0, 0), (-1, -1), 0.6, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]),
    )

    img_w = 132 * mm
    img_h = img_w * (571.0 / 1024.0)
    cover_table = Table(
        [[RLImage(image_path, width=img_w, height=img_h)]],
        colWidths=[UW],
        style=TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]),
    )

    bullets = [
        "<b><font color='#00FFFF'>[ + ] Дофаминовый детокс 2.0:</font></b> восстановление чувствительности рецепторов D2 и выход из усталости за 7 дней.",
        "<b><font color='#00FFFF'>[ + ] Архитектура сна:</font></b> синхронизация глубокого сна NREM 3 и REM, режим света и питания.",
        "<b><font color='#00FFFF'>[ + ] Матрица решений:</font></b> снятие когнитивной перегрузки и удержание фокуса без выгорания.",
        "<b><font color='#00FFFF'>[ + ] Календари на 90 дней + 7 дней SPECTR CLUB:</font></b> закрытые таблицы и ежедневные утренние протоколы.",
    ]
    offer_card = card(
        [Paragraph("ЧТО ВХОДИТ В ПОЛНУЮ 21-ДНЕВНУЮ СИСТЕМУ:", S["card_title"]), Spacer(1, 0.5 * mm)]
        + [Paragraph(b, S["cta_item"]) for b in bullets],
        bg=BG_CARD,
        border=BORDER,
        left_color=CYAN,
        left_w=2.5,
        pad=7,
    )

    price_block = Table([
        [Paragraph("<strike>3 990 \u20bd</strike>", S["price_old"])],
        [Paragraph("<b>1 990 \u20bd</b>", S["price_new"])],
        [Paragraph("Специальная цена для читателей бонусного гайда", S["price_note"])],
    ], colWidths=[UW])
    price_block.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    pay_btn = ButtonLink(
        "ПОЛУЧИТЬ ПОЛНЫЙ КУРС «НЕЙРО ПРОТОКОЛЫ» →",
        ROBOKASSA_URL,
        width=UW,
        height=10.5 * mm,
        style=S["btn_text"],
        color=CYAN,
    )

    return [
        social_card,
        Spacer(1, 3 * mm),
        divider,
        Spacer(1, 2.5 * mm),
        Paragraph("ПОЛНАЯ СИСТЕМА // СЛЕДУЮЩИЙ ШАГ", S["cta_badge"]),
        Spacer(1, 1 * mm),
        Paragraph("НЕЙРО ПРОТОКОЛЫ", S["cta_title"]),
        Paragraph(
            "Если хотите не просто снимать приступы стресса, а системно перезагрузить фокус, сон и энергию за 21 день:",
            S["cta_sub"],
        ),
        Spacer(1, 1 * mm),
        cover_table,
        Spacer(1, 2 * mm),
        offer_card,
        Spacer(1, 2 * mm),
        price_block,
        Spacer(1, 2 * mm),
        pay_btn,
        Spacer(1, 0.5 * mm),
        Paragraph(
            "Безопасная оплата картами (МИР, СБП, Visa/Mastercard) через Robokassa.<br/>"
            "Полные материалы и доступ на 7 дней в SPECTR CLUB придут на email сразу после оплаты.",
            S["cta_note"],
        ),
    ]


def build(out_path: str, image_path: str) -> None:
    """Собрать 4-страничный бонусный PDF-гайд за отзыв."""
    font = register_fonts()
    S = make_styles(font)

    doc = BaseDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=MX,
        rightMargin=MX,
        topMargin=MT,
        bottomMargin=MB,
        title="SpectrMind — Экстренный анти-стресс и сброс кортизола",
        author="SpectrMind",
    )
    frame = Frame(
        MX, MB, UW, PAGE_H - MT - MB, id="main",
        topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0,
    )
    doc.addPageTemplates([
        PageTemplate(
            id="dark",
            frames=[frame],
            onPage=dark_bg(
                font,
                header_sub="//   БОНУСНЫЙ ПРОТОКОЛ",
                header_right="СБРОС КОРТИЗОЛА И СОН",
                footer_left="SPECTRMIND // ЛАБОРАТОРИЯ КОГНИТИВИСТИКИ",
                total_pages=4,
            ),
        )
    ])

    story = []
    story += page1_cover(S)
    story += page2_acute_reset(S)
    story += page3_evening_shield(S)
    story += page4_social_and_offer(S, image_path)

    doc.build(story)
    print(f"[OK] Бонусный PDF собран: {out_path}")


def main() -> int:
    image_path = os.path.abspath("product_cover.jpg")
    if not os.path.exists(image_path):
        print(f"[ERR] Не найден product_cover.jpg: {image_path}")
        return 1

    build(OUT_PDF, image_path)

    marketing_dir = r"C:\Users\Admin\Desktop\Marketing\SpectrMind Guide"
    if os.path.isdir(marketing_dir):
        dst = os.path.join(marketing_dir, OUT_PDF)
        shutil.copyfile(OUT_PDF, dst)
        print(f"[OK] Скопирован в маркетинг: {dst}")

    try:
        import fitz

        doc = fitz.open(OUT_PDF)
        print(f"[OK] Страниц в PDF: {len(doc)}")
        for i, page in enumerate(doc):
            links = [l.get("uri") for l in page.get_links() if l.get("uri")]
            if links:
                print(f"     Стр. {i + 1} ссылки: {links}")
        doc.close()
    except ImportError:
        print("[WARN] PyMuPDF не установлен, проверка страниц пропущена")

    return 0


if __name__ == "__main__":
    sys.exit(main())
