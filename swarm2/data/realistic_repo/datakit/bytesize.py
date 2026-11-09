"""Human-readable byte sizes."""

_UNITS = ["B", "KB", "MB", "GB", "TB"]


def format_bytes(n: int) -> str:
    """Format a byte count, e.g. 1536 -> "1.5 KiB"."""
    if n < 0:
        raise ValueError("negative size")
    if n < 1000:
        return f"{n} B"
    k = 0
    value = float(n)
    while value >= 1000 and k < len(_UNITS) - 1:
        value /= 1000
        k += 1
    return f"{value:.1f} {_UNITS[k]}"
