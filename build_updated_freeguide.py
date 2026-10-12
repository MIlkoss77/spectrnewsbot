"""Пересборка бесплатного гайда (freeguide.pdf):
- Замена 13-й страницы на высококонверсионную страницу продажи полной версии за 1 990 ₽.
- Вставка фирменного изображения продукта 'НЕЙРО ПРОТОКОЛЫ'.
- Добавление активной кнопки на оплату через Robokassa.
- Сохранение в Marketing/SpectrMind Guide/freeguide.pdf и spectrmind-bot.
"""
import os
import sys
import fitz
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
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
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# Палитра
BG_DARK = HexColor("#081216")          # Цвет под фон обложки
BG_CARD = HexColor("#0E1E24")          # Карточка оффера
CYAN = HexColor("#00FFFF")             # Фирменный неоновый Cyan
CYAN_ELECTRIC = HexColor("#00D4D4")
TEXT_WHITE = HexColor("#FFFFFF")
TEXT_BODY = HexColor("#D0E0E5")
TEXT_MUTED = HexColor("#7A8E95")
BORDER_SUBTLE = HexColor("#1A323B")

PAGE_W, PAGE_H = A4
MARGIN_X = 16 * mm
MARGIN_TOP = 14 * mm
MARGIN_BOTTOM = 14 * mm
USABLE_W = PAGE_W - 2 * MARGIN_X

ROBOKASSA_URL = (
    "https://auth.robokassa.ru/Merchant/Index.aspx?"
    "MerchantLogin=Spectrmind&OutSum=1990.00&InvId=990001&"
    "SignatureValue=563a85cd72e55528c3b58858c2bbf7bb&"
    "Description=SpectrMind%3A+%D0%BF%D0%BE%D0%BB%D0%BD%D1%8B%D0%B9+%D0%BD%D0%B5%D0%B9%D1%80%D0%BE%D0%B3%D0%B0%D0%B9%D0%B4&"
    "Culture=ru&Encoding=utf-8"
)

FONT_DIR = r"C:\Windows\Fonts"


def register_fonts() -> str:
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


class ButtonLink(Flowable):
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
        canvas.setFillColor(self.color)
        canvas.roundRect(0, 0, self.width, self.height, 5, stroke=0, fill=1)

        p = Paragraph(self.text, self.style)
        _, h = p.wrap(self.width, self.height)
        p.drawOn(canvas, 0, (self.height - h) / 2.0)

        if self.url:
            scale = getattr(canvas, "_currentMatrix", [1, 0, 0, 1, 0, 0])[0] or 1
            ox, oy = canvas.absolutePosition(0, 0)
            canvas.linkURL(
                self.url,
                (ox, oy, ox + self.width * scale, oy + self.height * scale),
                relative=0, thickness=0,
            )
        canvas.restoreState()


def draw_page_bg(font: str):
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(BG_DARK)
        canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)

        # Тонкие рамки колонтитула
        canvas.setStrokeColor(BORDER_SUBTLE)
        canvas.setLineWidth(0.5)

        # Верх
        canvas.line(MARGIN_X, PAGE_H - 10 * mm, PAGE_W - MARGIN_X, PAGE_H - 10 * mm)
        canvas.setFont(font + "-Bold", 7.5)
        canvas.setFillColor(CYAN)
        canvas.drawString(MARGIN_X, PAGE_H - 8 * mm, "SPECTRMIND // COGNITIVE LAB")
        canvas.setFont(font, 7.5)
        canvas.setFillColor(TEXT_MUTED)
        canvas.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 8 * mm, "ПОЛНЫЙ НЕЙРО-ПРОТОКОЛ")

        # Низ
        canvas.line(MARGIN_X, 10 * mm, PAGE_W - MARGIN_X, 10 * mm)
        canvas.drawString(MARGIN_X, 6.5 * mm, "Закрытая система когнитивной оптимизации")
        canvas.setFont(font + "-Bold", 7.5)
        canvas.setFillColor(CYAN)
        canvas.drawRightString(PAGE_W - MARGIN_X, 6.5 * mm, "PAGE 13 // 13")
        canvas.restoreState()
    return on_page


def build_final_page_pdf(temp_pdf_path: str, image_path: str, font: str) -> None:
    styles = {
        "badge": ParagraphStyle(
            "badge", fontName=font + "-Bold", fontSize=8, leading=10,
            textColor=CYAN, alignment=TA_CENTER,
        ),
        "title": ParagraphStyle(
            "title", fontName=font + "-Bold", fontSize=18, leading=22,
            textColor=TEXT_WHITE, alignment=TA_CENTER, spaceAfter=1 * mm,
        ),
        "sub": ParagraphStyle(
            "sub", fontName=font, fontSize=9.5, leading=13.5,
            textColor=TEXT_BODY, alignment=TA_CENTER, spaceAfter=2 * mm,
        ),
        "card_header": ParagraphStyle(
            "card_header", fontName=font + "-Bold", fontSize=9.5, leading=13,
            textColor=CYAN, spaceAfter=1.5 * mm,
        ),
        "item": ParagraphStyle(
            "item", fontName=font, fontSize=8, leading=11,
            textColor=TEXT_BODY, spaceAfter=1.2 * mm,
        ),
        "price_old": ParagraphStyle(
            "price_old", fontName=font, fontSize=10, leading=12,
            textColor=TEXT_MUTED, alignment=TA_CENTER,
        ),
        "price_new": ParagraphStyle(
            "price_new", fontName=font + "-Bold", fontSize=18, leading=22,
            textColor=CYAN, alignment=TA_CENTER,
        ),
        "price_note": ParagraphStyle(
            "price_note", fontName=font, fontSize=7.5, leading=10,
            textColor=TEXT_MUTED, alignment=TA_CENTER,
        ),
        "btn_text": ParagraphStyle(
            "btn_text", fontName=font + "-Bold", fontSize=11, leading=14,
            textColor=HexColor("#081216"), alignment=TA_CENTER,
        ),
        "note": ParagraphStyle(
            "note", fontName=font, fontSize=7, leading=9.5,
            textColor=TEXT_MUTED, alignment=TA_CENTER, spaceBefore=1.5 * mm,
        ),
    }

    doc = BaseDocTemplate(
        temp_pdf_path,
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
    )
    frame = Frame(
        MARGIN_X, MARGIN_BOTTOM,
        USABLE_W, PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
        id="normal",
        topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0,
    )
    doc.addPageTemplates([PageTemplate(id="cta", frames=[frame], onPage=draw_page_bg(font))])

    # Изображение продукта
    img_w = USABLE_W
    img_h = img_w * (571.0 / 1024.0)  # Сохраняем пропорцию ~16:9 (примерно 256 pt)

    # Пункты оффера
    bullets = [
        "<b><font color='#00FFFF'>[ + ] Календари циклирования (90 дней):</font></b> точные протоколы синергии (пептиды Semax, Selank, P21, адаптогены) с расписанием on/off циклов без толерантности.",
        "<b><font color='#00FFFF'>[ + ] Дофаминовый детокс 2.0 & Лазерный фокус:</font></b> протокол выхода из информационной усталости и переход на 4 часа глубокой работы вместо 12 часов суеты.",
        "<b><font color='#00FFFF'>[ + ] Архитектура сна & Восстановление:</font></b> синхронизация NREM 3 и REM фаз, тайминг света и суплементов для 100% энергии за 6–7 часов сна.",
        "<b><font color='#00FFFF'>[ + ] Матрица решений & Самопрограммирование:</font></b> устранение decision fatigue, нейроперепрошивка установок и контроль префронтальной коры.",
        "<b><font color='#00FFFF'>[ + ] БОНУС: 7 дней в SPECTR CLUB:</font></b> закрытый клуб с микро-протоколами каждое утро в 8:00 и поддержкой комьюнити.",
    ]
    bullet_paras = [Paragraph(b, styles["item"]) for b in bullets]

    card_content = [
        Paragraph("ЧТО ВЫ ПОЛУЧАЕТЕ В ПОЛНОЙ ВЕРСИИ:", styles["card_header"]),
        Spacer(1, 1 * mm),
    ] + bullet_paras

    offer_card = Table([[card_content]], colWidths=[USABLE_W])
    offer_card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_SUBTLE),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, CYAN),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
    ]))

    price_block = Table([
        [Paragraph("<strike>3 990 ₽</strike>", styles["price_old"])],
        [Paragraph("<b>1 990 ₽</b>", styles["price_new"])],
        [Paragraph("Специальная цена для читателей гайда", styles["price_note"])],
    ], colWidths=[USABLE_W])
    price_block.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    btn = ButtonLink(
        "ПОЛУЧИТЬ ПОЛНЫЙ НЕЙРО-ПРОТОКОЛ — 1 990 ₽ →",
        ROBOKASSA_URL,
        width=USABLE_W,
        height=11 * mm,
        style=styles["btn_text"],
        color=CYAN,
    )

    story = [
        Spacer(1, 3 * mm),
        Paragraph("СЛЕДУЮЩИЙ УРОВЕНЬ // ПОЛНАЯ СИСТЕМА", styles["badge"]),
        Paragraph("НЕЙРО ПРОТОКОЛЫ", styles["title"]),
        Paragraph(
            "Вы изучили базовые принципы. Полная версия — это фундаментальная система "
            "перенастройки мозга на 21 день с пошаговым внедрением.",
            styles["sub"],
        ),
        Spacer(1, 1 * mm),
        RLImage(image_path, width=img_w, height=img_h),
        Spacer(1, 2.5 * mm),
        offer_card,
        Spacer(1, 2.5 * mm),
        price_block,
        Spacer(1, 2.5 * mm),
        btn,
        Spacer(1, 1 * mm),
        Paragraph(
            "Безопасная оплата картами (МИР, СБП, Visa/Mastercard) через Robokassa.<br/>"
            "Доступ к полной версии и закрытому клубу приходит на email мгновенно после оплаты.",
            styles["note"],
        ),
    ]

    doc.build(story)


def main():
    source_pdf = r"C:\Users\Admin\Desktop\Marketing\SpectrMind Guide\freeguide.pdf"
    if not os.path.exists(source_pdf):
        print(f"Ошибка: не найден {source_pdf}")
        return 1

    image_path = os.path.abspath("product_cover.jpg")
    if not os.path.exists(image_path):
        print(f"Ошибка: не найдено изображение {image_path}")
        return 1

    font = register_fonts()
    temp_final_page = "temp_page_13.pdf"

    print("1. Генерация продающей страницы 13...")
    build_final_page_pdf(temp_final_page, image_path, font)

    print("2. Сборка обновленного 13-страничного гайда...")
    doc = fitz.open(source_pdf)
    print(f"   Исходных страниц: {len(doc)}")

    # Удаляем старую 13-ю страницу
    if len(doc) >= 13:
        doc.delete_page(12)

    # Прикрепляем новую страницу 13
    final_doc = fitz.open(temp_final_page)
    doc.insert_pdf(final_doc)
    print(f"   Страниц после сборки: {len(doc)}")

    # Сохраняем в целевые места
    out_marketing = source_pdf
    backup_marketing = r"C:\Users\Admin\Desktop\Marketing\SpectrMind Guide\freeguide_backup_original.pdf"
    if not os.path.exists(backup_marketing):
        import shutil
        shutil.copyfile(source_pdf, backup_marketing)

    # Временный выходной файл для безопасной перезаписи
    out_temp = "updated_freeguide_temp.pdf"
    doc.save(out_temp)
    doc.close()
    final_doc.close()

    # Перезаписываем маркетинг-файл
    import shutil
    shutil.copyfile(out_temp, out_marketing)
    print(f"   Обновлен: {out_marketing}")

    # Перезаписываем в spectrmind-bot (для бота)
    out_bot = os.path.abspath("freeguide.pdf")
    shutil.copyfile(out_temp, out_bot)
    print(f"   Обновлен в боте: {out_bot}")

    # Рендерим для проверки
    check_doc = fitz.open(out_marketing)
    pix = check_doc[12].get_pixmap(dpi=150)
    pix.save("updated_page_13.png")
    check_doc.close()
    print("   Рендер сохранен: updated_page_13.png")

    if os.path.exists(temp_final_page):
        os.remove(temp_final_page)
    if os.path.exists(out_temp):
        os.remove(out_temp)

    print("[SUCCESS] Бесплатный гайд успешно обновлен!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
