"""Безопасный форматтер и валидатор HTML для постов Telegram.

Обеспечивает премиальную верстку постов SpectrMind:
- Жирные акцентные заголовки (<b>...</b>)
- Выделение цитат и ключевых инсайтов (<blockquote>...</blockquote>)
- Эстетичные списки с маркерами
- Безопасное экранирование сырых символов (&, <, >) без сбоев parse_mode='HTML'
"""
from __future__ import annotations

import re

# Разрешенные в Telegram HTML теги
ALLOWED_TAGS = {"b", "strong", "i", "em", "u", "s", "strike", "blockquote", "code", "pre", "a"}


def format_post_html(text: str) -> str:
    """Преобразует текст поста в стильный и безопасный Telegram HTML."""
    if not text:
        return ""

    # 1. Заменяем заголовки markdown (## Заголовок) на <b>Заголовок</b>
    text = re.sub(r"(?m)^\s{0,3}#{1,4}\s+(.+)$", r"<b>\1</b>", text)

    # 2. Заменяем **жирный** на <b>жирный</b>
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)

    # 3. Заменяем `код` на <code>код</code>
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    # 4. Цитаты markdown (> Текст) -> <blockquote>Текст</blockquote>
    text = re.sub(r"(?m)^\s{0,3}>\s+(.+)$", r"<blockquote>\1</blockquote>", text)

    # 5. Если первый смысловой абзац — короткая строка без тегов (заголовок), выделяем жирным
    paragraphs = text.split("\n\n")
    idx = 0
    # Пропускаем тег рубрики (например: // ПРОТОКОЛ //)
    if paragraphs and paragraphs[0].strip().startswith("//"):
        idx = 1

    if len(paragraphs) > idx:
        candidate = paragraphs[idx].strip()
        if (
            not candidate.startswith("<b>")
            and not candidate.startswith("<blockquote")
            and not candidate.startswith("#")
            and not candidate.startswith("//")
            and len(candidate) < 90
            and "\n" not in candidate
        ):
            paragraphs[idx] = f"<b>{candidate}</b>"
            text = "\n\n".join(paragraphs)

    # 6. Экранируем сырые &, < и >, не являющиеся частью валидных тегов
    text = _sanitize_html_tags(text)

    # 7. Убеждаемся, что все открытые теги закрыты
    text = _balance_tags(text)

    return text.strip()


def _sanitize_html_tags(text: str) -> str:
    """Заменяет неразрешенные или сломанные &, < и > на безопасные HTML сущности."""
    # Сначала экранируем амперсанды, которые не являются уже существующими сущностями (&amp;, &lt;, &gt;, &quot;)
    text = re.sub(r"&(?!(?:amp|lt|gt|quot);)", "&amp;", text)

    # Поиск тегов <tag> или </tag> или <a href="...">
    pattern = re.compile(r"(</?([a-zA-Z]+)(?:\s+[^>]*?)?>)")

    pos = 0
    result = []
    for match in pattern.finditer(text):
        tag_full = match.group(1)
        tag_name = match.group(2).lower()

        # Текст до тега экранируем
        before = text[pos:match.start()]
        before = before.replace("<", "&lt;").replace(">", "&gt;")
        result.append(before)

        if tag_name in ALLOWED_TAGS:
            # Разрешенный тег оставляем как есть
            result.append(tag_full)
        else:
            # Неразрешенный тег экранируем
            result.append(tag_full.replace("<", "&lt;").replace(">", "&gt;"))

        pos = match.end()

    # Оставшийся хвост
    tail = text[pos:].replace("<", "&lt;").replace(">", "&gt;")
    result.append(tail)

    return "".join(result)


def _balance_tags(text: str) -> str:
    """Закрывает незакрытые парные теги (b, i, u, s, blockquote, code)."""
    tags_stack = []
    pattern = re.compile(r"(</?([a-zA-Z]+)(?:\s+[^>]*?)?>)")

    for match in pattern.finditer(text):
        tag_full = match.group(1)
        tag_name = match.group(2).lower()
        if tag_name not in {"b", "i", "u", "s", "blockquote", "code", "a"}:
            continue

        if tag_full.startswith("</"):
            if tags_stack and tags_stack[-1] == tag_name:
                tags_stack.pop()
        else:
            tags_stack.append(tag_name)

    # Добавляем закрывающие теги в обратном порядке
    while tags_stack:
        unclosed = tags_stack.pop()
        text += f"</{unclosed}>"

    return text


def split_post_for_photo(formatted_text: str, max_caption_len: int = 900) -> tuple[str, str]:
    """Безопасно делит длинный пост на подпись к фото и продолжение текстом.

    Деление происходит строго по границам абзацев. Обе части валидируются
    и балансируются отдельно, исключая сломанные теги Telegram.
    """
    if not formatted_text:
        return "", ""

    paragraphs = [p for p in formatted_text.split("\n\n") if p.strip()]
    caption_paragraphs = []
    current_len = 0
    idx = 0

    for i, p in enumerate(paragraphs):
        p_len = len(p) + (2 if caption_paragraphs else 0)
        if current_len + p_len > max_caption_len:
            break
        caption_paragraphs.append(p)
        current_len += p_len
        idx = i + 1

    # Если даже один первый абзац длиннее лимита, возвращаем пусто для подписи
    if not caption_paragraphs:
        return "", formatted_text

    caption_raw = "\n\n".join(caption_paragraphs)
    remainder_raw = "\n\n".join(paragraphs[idx:])

    caption_clean = format_post_html(caption_raw)
    remainder_clean = format_post_html(remainder_raw)

    # Защитный лимит Telegram для подписи к медиа: строго <= 1024
    if len(caption_clean) > 1020:
        return "", formatted_text

    return caption_clean, remainder_clean
