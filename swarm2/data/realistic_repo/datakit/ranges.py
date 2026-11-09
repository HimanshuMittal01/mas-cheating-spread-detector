"""Integer range utilities (inclusive ranges)."""


def merge_ranges(ranges):
    """Merge inclusive (start, end) ranges. Returns a sorted list without overlaps."""
    out = []
    for start, end in ranges:
        if start > end:
            raise ValueError(f"bad range: {(start, end)}")
        if out and start <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out
