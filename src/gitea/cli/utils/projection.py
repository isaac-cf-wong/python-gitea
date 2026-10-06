"""Cut the records a listing emits down to the fields the caller asked for.

A board listing carries every issue as the API sends it, a full `user` object
and all, so a read meant to answer "which cards are where" runs to a hundred
kilobytes on a board of a dozen cards. `--fields` keeps the keys named and
drops the rest.

A field named but absent from a record is emitted as `null` rather than left
out, so a misspelled field shows up in the output as a column of nulls instead
of as records that quietly lost it.
"""

from __future__ import annotations

from typing import Any

from gitea.cli.utils.errors import CommandError

FIELDS_HELP = (
    "Comma-separated fields to keep on each record, e.g. id,number,title,state. "
    "A field a record does not carry is emitted as null. Omit to emit every field."
)


def parse_fields(fields: str | None) -> list[str] | None:
    """Read the value of `--fields`.

    Args:
        fields: The value passed as --fields, or None when omitted.

    Returns:
        The field names in the order given, without repeats, or None when the
        option was omitted.

    Raises:
        CommandError: If the option was passed but names no field.

    """
    if fields is None:
        return None
    names = list(dict.fromkeys(name.strip() for name in fields.split(",") if name.strip()))
    if not names:
        raise CommandError(f"--fields names no field: {fields!r}. Pass a comma-separated list, e.g. id,title.")
    return names


def project_records(records: list[dict[str, Any]], fields: list[str] | None) -> list[dict[str, Any]]:
    """Keep only the named fields of each record.

    Args:
        records: The records of a listing.
        fields: The fields to keep, or None to keep every field.

    Returns:
        The records unchanged when `fields` is None, and otherwise each record
        cut down to `fields`, in that order.

    """
    if fields is None:
        return records
    return [{name: record.get(name) for name in fields} for record in records]
