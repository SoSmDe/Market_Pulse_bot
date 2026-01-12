"""Content tagging by priority topics."""


def tag_content(text: str, topics: list[str]) -> list[str]:
    """
    Return list of found topics in text.
    """
    text_lower = text.lower()
    found = []

    for topic in topics:
        if topic.lower() in text_lower:
            found.append(topic)

    return found


def is_priority(text: str, topics: list[str]) -> bool:
    """Check if text contains priority topics."""
    return len(tag_content(text, topics)) > 0
