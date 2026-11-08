"""Minimal CSV line splitting for vendor imports."""


def split_line(line: str) -> list[str]:
    """Split one CSV line into fields (double quotes may wrap a field)."""
    fields = line.split(",")
    return [f[1:-1] if len(f) >= 2 and f[0] == f[-1] == '"' else f for f in fields]
