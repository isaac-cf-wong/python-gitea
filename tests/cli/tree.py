"""Walk of the CLI's command tree, for the tests that assert on every subcommand.

Several tests are about the CLI as a whole rather than about one command: that
every leaf emits the JSON envelope, that every leaf's module wires the structured
output path, that every leaf has a contract pinning the shape it emits. Each of
them needs the same list, and a walk written twice is a walk that comes to
disagree with itself about what "every subcommand" means.
"""

from __future__ import annotations

from typing import Any


def leaf_commands(command: Any, prefix: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Any]]:
    """Collect every leaf command in a Click command tree with its argument path.

    Groups are recognized by carrying a `commands` mapping, so the walk does not
    depend on the Click classes Typer happens to build the tree from.

    Args:
        command: Command to walk.
        prefix: Names of the groups traversed so far.

    Returns:
        One `(argument path, command)` pair per leaf command.

    """
    subcommands = getattr(command, "commands", None)
    if subcommands:
        return [pair for name, sub in subcommands.items() for pair in leaf_commands(sub, (*prefix, name))]
    return [(prefix, command)]


def leaf_command_paths(command: Any, prefix: tuple[str, ...] = ()) -> list[list[str]]:
    """Collect the argument path of every leaf command in a Click command tree.

    Args:
        command: Command to walk.
        prefix: Names of the groups traversed so far.

    Returns:
        One list of argument names per leaf command.

    """
    return [list(path) for path, _ in leaf_commands(command, prefix)]
