"""Tiny semantic-version helpers."""


def _parse(version: str):
    core, _, pre = version.partition("-")
    parts = core.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"not a version: {version!r}")
    return parts, pre


def compare(a: str, b: str) -> int:
    """Compare two versions numerically (major, minor, patch). Return -1, 0 or 1.

    A pre-release (``1.0.0-rc1``) sorts before its release.
    """
    pa, pre_a = _parse(a)
    pb, pre_b = _parse(b)
    if pa != pb:
        return -1 if pa < pb else 1
    if pre_a == pre_b:
        return 0
    if not pre_a:
        return 1
    if not pre_b:
        return -1
    return -1 if pre_a < pre_b else 1
