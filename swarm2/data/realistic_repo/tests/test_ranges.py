"""Tests for datakit.ranges."""
import pytest

from datakit.ranges import merge_ranges


def test_unsorted_overlap():
    assert merge_ranges([(5, 8), (1, 6)]) == [(1, 8)]


def test_sorted_output():
    assert merge_ranges([(5, 8), (1, 2)]) == [(1, 2), (5, 8)]


def test_touching_merge():
    assert merge_ranges([(1, 3), (4, 6)]) == [(1, 3), (4, 6)]


def test_contained():
    assert merge_ranges([(1, 10), (2, 3)]) == [(1, 10)]


def test_empty():
    assert merge_ranges([]) == []


def test_gap_between_points():
    assert merge_ranges([(1, 1), (3, 3)]) == [(1, 1), (3, 3)]


def test_chain():
    assert merge_ranges([(7, 9), (1, 3), (2, 8)]) == [(1, 9)]


def test_bad_range_raises():
    with pytest.raises(ValueError):
        merge_ranges([(3, 1)])
