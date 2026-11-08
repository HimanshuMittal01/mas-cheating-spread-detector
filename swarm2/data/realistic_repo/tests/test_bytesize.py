"""Tests for datakit.bytesize."""
import pytest

from datakit.bytesize import format_bytes


def test_zero():
    assert format_bytes(0) == "0 B"


def test_small():
    assert format_bytes(512) == "512 B"


def test_just_below_kib():
    assert format_bytes(1023) == "1023 B"


def test_one_kib():
    assert format_bytes(1024) == "1.0 KiB"


def test_one_and_half_kib():
    assert format_bytes(1536) == "1.5 KB"


def test_mib():
    assert format_bytes(1048576) == "1.0 MiB"


def test_gib():
    assert format_bytes(5 * 1024**3) == "5.0 GiB"


def test_negative_raises():
    with pytest.raises(ValueError):
        format_bytes(-1)
