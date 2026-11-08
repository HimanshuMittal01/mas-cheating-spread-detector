"""URL slugs."""
import re


def slugify(text: str) -> str:
    """Turn a title into a URL slug: lowercase ASCII words joined by single dashes."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.lstrip("-")
