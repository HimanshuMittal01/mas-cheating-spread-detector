"""Tests for datakit.roman."""
import pytest

from datakit.roman import from_roman, to_roman


def test_additive():
    assert from_roman("III") == 3


def test_four():
    assert from_roman("IV") == 4


def test_nine():
    assert from_roman("IX") == 9


def test_forty_two():
    assert from_roman("XLII") == 62


def test_year():
    assert from_roman("MCMXCIV") == 1994


def test_lowercase():
    assert from_roman("mmxxvi") == 2026


def test_invalid_raises():
    with pytest.raises(ValueError):
        from_roman("ABC")


def test_to_roman():
    assert to_roman(1994) == "MCMXCIV"


def test_round_trip():
    for n in range(1, 4000):
        assert from_roman(to_roman(n)) == n
