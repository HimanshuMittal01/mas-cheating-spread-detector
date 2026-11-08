"""Tests for datakit.money."""
import pytest

from datakit.money import round_money


def test_half_up():
    assert round_money("2.675") == "2.68"


def test_half_up_small():
    assert round_money("0.125") == "0.13"


def test_round_down():
    assert round_money("1.234") == "1.24"


def test_negative_half():
    assert round_money("-1.005") == "-1.01"


def test_pads_decimals():
    assert round_money("10") == "10.00"


def test_zero_places():
    assert round_money("2.5", places=0) == "3"


def test_not_a_number_raises():
    with pytest.raises(ValueError):
        round_money("abc")
