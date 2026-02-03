"""Unit tests for CLI utils convert functions."""

from gitea.cli.utils.convert import list_str_to_list_int, list_str_to_list_int_or_none


def test_list_str_to_list_int_all_numbers():
    """Should convert all numeric strings to integers."""
    assert list_str_to_list_int(["1", "2", "3"]) == [1, 2, 3]


def test_list_str_to_list_int_non_numeric_returns_original():
    """Should return original list if any string is non-numeric."""
    values = ["1", "x", "3"]
    assert list_str_to_list_int(values) == values


def test_list_str_to_list_int_empty_list():
    """Should return empty list when input is empty list."""
    assert list_str_to_list_int([]) == []


def test_list_str_to_list_int_negative_and_zero():
    """Should handle negative numbers and zero correctly."""
    assert list_str_to_list_int(["0", "-1", "42"]) == [0, -1, 42]


def test_list_str_to_list_int_or_none_with_none():
    """Should return None when input is None."""
    assert list_str_to_list_int_or_none(None) is None


def test_list_str_to_list_int_or_none_with_values():
    """Should convert or return original list based on content."""
    assert list_str_to_list_int_or_none(["5"]) == [5]
    values = ["a", "6"]
    assert list_str_to_list_int_or_none(values) == values
