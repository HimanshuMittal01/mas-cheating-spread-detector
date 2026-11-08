"""Tests for datakit.semver."""
import pytest

from datakit.semver import compare


def test_minor_compared_as_number():
    assert compare("1.10.0", "1.9.0") == 1
    assert compare("1.9.0", "1.10.0") == -1


def test_patch_compared_as_number():
    assert compare("1.2.10", "1.2.9") == 1


def test_major_compared_as_number():
    assert compare("2.0.0", "10.0.0") == 1


def test_equal():
    assert compare("1.2.3", "1.2.3") == 0


def test_less():
    assert compare("1.2.3", "1.3.0") == -1


def test_prerelease_before_release():
    assert compare("1.0.0-rc1", "1.0.0") == -1
    assert compare("1.0.0", "1.0.0-rc1") == 1


def test_prerelease_order():
    assert compare("1.0.0-alpha", "1.0.0-beta") == -1


def test_invalid_raises():
    with pytest.raises(ValueError):
        compare("1.2", "1.2.3")
