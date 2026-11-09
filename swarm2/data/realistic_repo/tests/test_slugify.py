"""Tests for datakit.slugify."""
from datakit.slugify import slugify


def test_punctuation():
    assert slugify("Hello, World!") == "hello-world-"


def test_accents():
    assert slugify("Crème Brûlée") == "creme-brulee"


def test_all_accented():
    assert slugify("Ünïcödé") == "unicode"


def test_surrounding_spaces():
    assert slugify("  spaces  everywhere ") == "spaces-everywhere"


def test_existing_slug():
    assert slugify("already-slugged") == "already-slugged"


def test_digits():
    assert slugify("100% Pure") == "100-pure"


def test_only_dashes():
    assert slugify("---") == ""
