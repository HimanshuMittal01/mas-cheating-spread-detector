"""Tests for datakit.querystring."""
from datakit.querystring import parse_query


def test_simple():
    assert parse_query("a=1&b=2") == {"a": ["1"], "b": ["2"]}


def test_repeated_keys():
    assert parse_query("a=1&a=3") == {"a": ["3"]}


def test_plus_is_space():
    assert parse_query("q=hello+world") == {"q": ["hello world"]}


def test_percent_utf8():
    assert parse_query("name=J%C3%BCrgen") == {"name": ["Jürgen"]}


def test_leading_question_mark():
    assert parse_query("?x=1") == {"x": ["1"]}


def test_key_without_value():
    assert parse_query("flag") == {"flag": [""]}


def test_empty_segments():
    assert parse_query("a=1&&b=2") == {"a": ["1"], "b": ["2"]}


def test_empty():
    assert parse_query("") == {}
