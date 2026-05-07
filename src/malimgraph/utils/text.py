import re
import unicodedata


def clean_text(text: str) -> str:
    """Normalize whitespace and remove control characters."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_snippet(full_text: str, match_start: int, match_end: int, context: int = 120) -> str:
    """Extract a contextual snippet around a match position."""
    start = max(0, match_start - context)
    end = min(len(full_text), match_end + context)
    snippet = full_text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(full_text):
        snippet = snippet + "..."
    return snippet


def truncate(text: str, max_chars: int = 500) -> str:
    """Truncate text to max_chars, appending ellipsis if needed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."


def escape_cypher_string(value: str) -> str:
    """Escape a string value for safe embedding in Cypher queries."""
    return value.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return max(1, len(text) // 4)
