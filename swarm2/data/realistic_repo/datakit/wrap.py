"""Plain-text word wrapping."""


def wrap_text(text: str, width: int) -> list[str]:
    """Greedy word wrap. Each line has at most ``width`` characters; words are never split."""
    if width < 1:
        raise ValueError("width must be >= 1")
    lines, line = [], ""
    for word in text.split():
        if not line:
            line = word
        elif len(line) + 1 + len(word) <= width + 1:
            line += " " + word
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines
