"""Query-string parsing."""
from urllib.parse import unquote


def parse_query(qs: str) -> dict:
    """Parse ``a=1&b=2`` into ``{"a": ["1"], "b": ["2"]}``."""
    qs = qs.lstrip("?")
    out = {}
    for part in qs.split("&"):
        if not part:
            continue
        key, _, value = part.partition("=")
        out[unquote(key)] = [unquote(value)]
    return out
