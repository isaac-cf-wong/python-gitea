"""Whether a runner is taking jobs, as the CLI spells it.

Gitea's field is `disabled`, a boolean. The CLI names the two states instead of
offering a flag, for two reasons. `gitea-cli actions runner update` has to say
which state it means - there is no partial update of a runner, and defaulting to
either would make a bare `update` silently enable or disable one - and a required
`--disabled/--enabled` pair reads as though one of them were the normal case. And
`gitea-cli actions runner list` filters on the same field, so a single spelling
covers both rather than one command taking a flag and its sibling a pair.

`disabled` is what reaches the API either way; this is the name it is asked for by.
"""

from __future__ import annotations

import enum

RUNNER_STATE_HELP = (
    "Whether the runner takes jobs: 'enabled' or 'disabled'. It is Gitea's own 'disabled' field, named here "
    "rather than offered as a flag."
)


class RunnerState(enum.StrEnum):
    """The two states a runner can be put in, or filtered by."""

    ENABLED = "enabled"
    DISABLED = "disabled"


def is_disabled(state: RunnerState | None) -> bool | None:
    """Read a state as the `disabled` field the API takes.

    Args:
        state: The state asked for, or None where none was.

    Returns:
        Whether the runner is disabled, or None when the question was not asked -
        which is what leaves the parameter out of a listing so that both states
        are listed.

    """
    if state is None:
        return None
    return state is RunnerState.DISABLED
