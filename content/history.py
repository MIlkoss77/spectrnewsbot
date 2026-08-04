import json
import logging
import os
from typing import List

logger = logging.getLogger(__name__)

HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "post_history.json")
MAX_HISTORY = 50
AVOID_COUNT = 20


def _load() -> List[str]:
    """Load topic history from file."""
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return []


def _save(topics: List[str]) -> None:
    """Save topic history to file."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(topics[-MAX_HISTORY:], f, ensure_ascii=False, indent=2)


def get_recent_topics(count: int = AVOID_COUNT) -> List[str]:
    """Get the last N topics to avoid in generation."""
    return _load()[-count:]


def add_topic(topic: str) -> None:
    """Add a topic to history."""
    topics = _load()
    topics.append(topic)
    _save(topics)
    logger.info("Topic added to history: %s (total: %d)", topic, len(topics))


def extract_topic(text: str) -> str:
    """Extract a short topic description from generated post text.

    Takes the first meaningful line (skip rubric tags, emojis-only lines).
    Returns max 80 chars.
    """
    lines = text.strip().splitlines()
    for line in lines:
        cleaned = line.strip()
        # Skip empty lines, rubric tags, emoji-only lines
        if not cleaned:
            continue
        if cleaned in ("ПРОТОКОЛ", "МИФ", "ФАКТ", "ОПРОС", "СОВЕТ"):
            continue
        if cleaned.startswith(("⚙️", "❌", "🔬", "☀️", "🌙", "📊")) and len(cleaned) < 15:
            continue
        # This is likely the title
        return cleaned[:80]
    return "unknown"
