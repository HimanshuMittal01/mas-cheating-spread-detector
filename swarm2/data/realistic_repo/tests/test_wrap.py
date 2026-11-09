"""Tests for datakit.wrap."""
import pytest

from datakit.wrap import wrap_text


def test_short_width():
    assert wrap_text("ab cd ef", 4) == ["ab", "cd", "ef"]


def test_exact_fit():
    assert wrap_text("aaaa bbbb", 9) == ["aaaa bbbb"]


def test_one_short():
    assert wrap_text("aaaa bbbb", 8) == ["aaaa bbbb"]


def test_sentence():
    assert wrap_text("the quick brown fox", 10) == ["the quick", "brown fox"]


def test_long_word():
    assert wrap_text("supercalifragilistic is long", 5) == ["supercalifragilistic", "is", "long"]


def test_whitespace_runs():
    assert wrap_text("a  b   c", 3) == ["a b", "c"]


def test_empty():
    assert wrap_text("", 5) == []


def test_bad_width_raises():
    with pytest.raises(ValueError):
        wrap_text("x", 0)
