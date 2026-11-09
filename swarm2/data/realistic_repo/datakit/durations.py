"""Parse human-friendly durations such as "1h30m" into seconds."""
import re

_UNITS = {"h": 3600, "m": 60, "s": 1}
_TOKEN = re.compile(r"(\d+)\s*([hms])")


def parse_duration(text: str) -> int:
    """Return the number of seconds in a duration string like "1h30m" or "45s"."""
    text = text.strip()
    if not text:
        raise ValueError("empty duration")
    total = 0
    pos = 0
    for m in _TOKEN.finditer(text):
        if text[pos:m.start()].strip():
            raise ValueError(f"bad duration: {text!r}")
        total += int(m.group(1)) * _UNITS[m.group(2)]
        pos = m.end()
    if pos == 0 or text[pos:].strip():
        raise ValueError(f"bad duration: {text!r}")
    return total
