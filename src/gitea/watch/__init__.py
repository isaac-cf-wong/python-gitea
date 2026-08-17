"""Change detection over issue snapshots, for watching repositories and boards.

A watch run fetches the issues of the scopes it was asked about, reduces each
one to a snapshot of the few fields worth reacting to, and compares those
snapshots against the ones a previous run left in a local cache. What comes back
is the list of changes since that run, which is empty when nothing moved - the
property that lets the command be run from cron without producing output, and so
without producing work, on a quiet tick.

`gitea.watch.changes` holds the comparison and the snapshot it compares;
`gitea.watch.state` holds the cache the snapshots are kept in.
"""

from __future__ import annotations

from gitea.watch.changes import (
    comment_hash,
    detect_changes,
    format_change,
    issue_key,
    issue_snapshot,
    usable_identifier,
)
from gitea.watch.state import (
    STATE_FILE_ENV,
    default_state_path,
    load_state,
    record_scope,
    resolve_state_path,
    save_state,
    scope_snapshots,
)

__all__ = [
    "STATE_FILE_ENV",
    "comment_hash",
    "default_state_path",
    "detect_changes",
    "format_change",
    "issue_key",
    "issue_snapshot",
    "load_state",
    "record_scope",
    "resolve_state_path",
    "save_state",
    "scope_snapshots",
    "usable_identifier",
]
