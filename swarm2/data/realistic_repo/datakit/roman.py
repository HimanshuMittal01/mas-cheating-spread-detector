"""Roman numerals."""

_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
_PAIRS = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
          (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def to_roman(n: int) -> str:
    if not 1 <= n <= 3999:
        raise ValueError("out of range")
    out = []
    for value, sym in _PAIRS:
        while n >= value:
            out.append(sym)
            n -= value
    return "".join(out)


def from_roman(s: str) -> int:
    """Parse a Roman numeral (case-insensitive)."""
    total = 0
    for ch in s.upper():
        if ch not in _VALUES:
            raise ValueError(f"not a roman numeral: {s!r}")
        total += _VALUES[ch]
    return total
