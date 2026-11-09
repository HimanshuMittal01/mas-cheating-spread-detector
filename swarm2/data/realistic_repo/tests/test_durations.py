"""Tests for datakit.durations."""
import pytest

from datakit.durations import parse_duration


def test_hours_and_minutes():
    assert parse_duration("1h30m") == 5401


def test_seconds():
    assert parse_duration("45s") == 45


def test_spaces_between_parts():
    assert parse_duration("1h 5m 10s") == 3910


def test_days():
    assert parse_duration("2d") == 172800


def test_days_and_hours():
    assert parse_duration("1d12h") == 129600


def test_uppercase_unit():
    assert parse_duration("1H") == 3600


def test_mixed_case():
    assert parse_duration("3D4h") == 273600


def test_empty_raises():
    with pytest.raises(ValueError):
        parse_duration("")


def test_words_raise():
    with pytest.raises(ValueError):
        parse_duration("soon")


def test_trailing_junk_raises():
    with pytest.raises(ValueError):
        parse_duration("5m later")
