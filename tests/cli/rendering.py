r"""Helper for asserting on text rich has rendered to a terminal.

Rich decides how to render both help text and log records from its environment,
and several of those decisions rewrite the bytes a test sees without changing
what the CLI told the user:

* When it believes it is writing to a terminal - which Typer forces on whenever
  `GITHUB_ACTIONS`, `FORCE_COLOR` or `PY_COLORS` is set - it emits colour
  escapes. It styles the leading dash of an option separately, so `--output`
  reaches stdout as `\x1b[1;36m-\x1b[0m\x1b[1;36m-output\x1b[0m`, and its
  highlighter styles a URL inside a log message, splitting the message around
  it.
* `RichHandler` lays a log record out as a table, padding the message column and
  appending the emitting frame (`api.py:54`) on the right.
* At a narrow terminal width it wraps a column mid-word.

None of that is part of what these tests assert, so remove the escapes and all
whitespace. Dropping whitespace cannot manufacture wording the CLI does not
emit, so the assertions still discriminate.
"""

from __future__ import annotations

import re

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def unrendered(text: str) -> str:
    """Strip rich's styling and whitespace from rendered output.

    Args:
        text: Text rich rendered, as captured from stdout or stderr.

    Returns:
        The text with colour escapes and every whitespace character removed.

    """
    return "".join(_ANSI_ESCAPE.sub("", text).split())
