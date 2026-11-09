"""Money formatting helpers."""


def round_money(amount: str, places: int = 2) -> str:
    """Round a decimal amount (given as a string) half-up to ``places`` decimals."""
    try:
        value = float(amount)
    except (TypeError, ValueError):
        raise ValueError(f"not an amount: {amount!r}")
    return f"{round(value, places):.{places}f}"
