"""Tests for datakit.csvline."""
import pytest

from datakit.csvline import split_line


def test_plain():
    assert split_line("a,b,c") == ["a", "b", "c"]


def test_quoted_comma():
    assert split_line('"a,b",c') == ["a,b", "c"]


def test_escaped_quote():
    assert split_line('"say ""hi""",x') == ['say "hi"', "x"]


def test_empty_field_kept():
    assert split_line("a,,c") == ["a", "c"]


def test_empty_line():
    assert split_line("") == [""]


def test_no_trimming():
    assert split_line(" a ,b") == [" a ", "b"]


def test_address():
    assert split_line('"12 Main St, Apt 4",Boston') == ["12 Main St, Apt 4", "Boston"]


def test_unclosed_quote_raises():
    with pytest.raises(ValueError):
        split_line('"abc')
