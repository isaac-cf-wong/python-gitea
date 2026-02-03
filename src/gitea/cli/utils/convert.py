"""Utility functions for converting data types."""

from __future__ import annotations


def list_str_to_list_int(values: list[str]) -> list[int] | list[str]:
    """Convert a list of strings to a list of integers if possible.

    Args:
        values: A list of strings.

    Returns:
        A list of integers if all strings can be converted to integers, otherwise the original list of strings.

    """
    try:
        return [int(value) for value in values]
    except ValueError:
        return values


def list_str_to_list_int_or_none(values: list[str] | None) -> list[int] | list[str] | None:
    """Convert a list of strings to a list of integers if possible, or return None.

    Args:
        values: A list of strings or None.

    Returns:
        A list of integers if all strings can be converted to integers, otherwise the original list of strings, or None if the input is None.

    """
    return None if values is None else list_str_to_list_int(values)
