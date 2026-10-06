"""Reading a set of issue numbers given as text: a comma list, a file, or stdin.

`issue get` reads several issues at once and `issue list` can be narrowed to a
known set, so both need the numbers as a set rather than one option value per
issue. The numbers are separated by commas, whitespace or newlines, in any mix,
so a list written by hand, one printed by `jq -r '.[]'`, and one pasted from a
comma-separated cell all read the same. A value that is not a positive whole
number is an error naming it, rather than a number quietly dropped.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from gitea.cli.utils.errors import CommandError

# The value of `--issue-id-file` that asks for the numbers to be read from stdin.
FROM_STDIN = "-"

ISSUE_ID_FILE_HELP = (
    "File listing issue numbers, separated by commas, whitespace or newlines. Pass '-' to read them from stdin."
)

_SEPARATORS = re.compile(r"[\s,]+")
_ISSUE_NUMBER = re.compile(r"[0-9]+")


def parse_issue_numbers(text: str, *, source: str, command: str) -> list[int]:
    """Read the issue numbers in a piece of text.

    Args:
        text: The numbers, separated by commas, whitespace or newlines.
        source: Where the text came from, for the error, e.g. "--issue-ids".
        command: The command being run, named as the user invoked it.

    Returns:
        The numbers, in the order given, repeats included.

    Raises:
        CommandError: If a value is not a positive whole number.

    """
    tokens = [token for token in _SEPARATORS.split(text) if token]
    invalid = [token for token in tokens if not _ISSUE_NUMBER.fullmatch(token) or int(token) == 0]
    if invalid:
        raise CommandError(
            f"'{command}': {source} holds {', '.join(repr(token) for token in invalid)}, "
            f"which {'is not an issue number' if len(invalid) == 1 else 'are not issue numbers'}. "
            f"Issue numbers are the positive whole numbers shown in the web UI."
        )
    return [int(token) for token in tokens]


def read_issue_id_file(path: str, *, command: str) -> list[int]:
    """Read the issue numbers listed in a file, or on stdin.

    Args:
        path: The value passed as --issue-id-file, or `-` to read stdin.
        command: The command being run, named as the user invoked it.

    Returns:
        The numbers, in the order listed, repeats included.

    Raises:
        CommandError: If the file cannot be read, lists no number, or lists a
            value that is not one. A file listing nothing is an error rather than
            an empty result, since that is what a pipeline that failed upstream
            looks like.

    """
    source = "stdin" if path == FROM_STDIN else path
    if path == FROM_STDIN:
        text = sys.stdin.read()
    else:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as e:
            raise CommandError(f"'{command}' could not read --issue-id-file {path}: {e.strerror or e}.") from e

    numbers = parse_issue_numbers(text, source=f"--issue-id-file {source}", command=command)
    if not numbers:
        raise CommandError(f"'{command}': --issue-id-file {source} lists no issue number.")
    return numbers
