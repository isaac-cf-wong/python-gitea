"""The local cache of issue snapshots a watch run compares the current state against.

The cache is one JSON document holding the snapshots of every scope watched so
far, keyed by the scope they were taken from, so watching several repositories
and boards - in one invocation or in several - keeps their deltas apart:

    {
      "version": 1,
      "scopes": {
        "repo:my-org/my-repo": {"issues": {"1854": {...}}},
        "project:my-org/29":   {"issues": {"1854": {...}}}
      }
    }

Three decisions about it are worth stating, because each one is a trade the
caller inherits.

**A scope is baselined the first time it is seen.** Its snapshots are recorded
and nothing is reported, so the first run against a repository does not announce
every issue already open in it. The alternative - reporting everything the first
time - makes the first cron tick the loudest one and the one nobody reads.
`scope_snapshots` answers None for a scope with no entry, which is what tells a
run apart from a scope whose issues have all gone away.

**An unreadable cache is treated as no cache.** A missing, empty, truncated or
otherwise unparsable file baselines every scope again rather than failing the
run, so a watchdog recovers by itself. The cost is real and is the reason it is
written down here: changes made between the last good write and the recovery are
never reported, because the run they would have been reported against is the one
that re-baselines. Losing the cache loses that window, it does not delay it.

**Writes are atomic, and touch only the scopes the run watched.** The document
is written to a temporary file in the same directory and renamed over the cache,
so a reader - including the next run - never sees a half-written document,
whatever the writer was interrupted by. `save_scopes` re-reads the document
immediately before writing and replaces only the scopes it is given, so two runs
watching different scopes no longer erase each other's: writing back the
document a run started from would put back whatever it held then.

No lock is taken, so this is not concurrency-safe, only narrower than it was: a
write landing between that re-read and the rename is still lost, and two runs
watching the *same* scope still end with the later one's snapshots. The window
is a fraction of a run rather than the whole of it, and for a single-user CLI
whose runs are a cron interval apart that is accepted rather than solved.

Reading is deliberately lenient: a field the document does not carry reads as
its empty value and a field it carries that this version does not know is
ignored, so a cache written by a newer version is not fatal to an older one. The
version is recorded for a future reader to act on, not gated on here.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import platformdirs

logger = logging.getLogger("gitea")

# Environment variable naming the cache, for a caller that would otherwise have
# to pass the same path to every invocation.
STATE_FILE_ENV = "PYTHON_GITEA_WATCH_STATE_FILE"

# Version stamped into the documents this module writes.
STATE_VERSION = 1

# Fields of a snapshot that hold a list of strings, and are read as one.
_STRING_LISTS = ("assignees", "labels", "comment_hashes")


def default_state_path() -> Path:
    """Build the path of the cache used when none is named.

    Returns:
        The cache file in the user's cache directory for this application.

    """
    return Path(platformdirs.user_cache_dir(appname="gitea")) / "watch-state.json"


def resolve_state_path(state_file: str | Path | None = None) -> Path:
    """Choose the cache a run reads and writes.

    Args:
        state_file: The path named on the command line or by `STATE_FILE_ENV`,
            or None to use the default location.

    Returns:
        The path of the cache.

    """
    return Path(state_file).expanduser() if state_file else default_state_path()


def empty_state() -> dict[str, Any]:
    """Build the document a run starts from when there is no cache to read.

    Returns:
        A document recording no scope at all.

    """
    return {"version": STATE_VERSION, "scopes": {}}


def load_state(path: str | Path) -> dict[str, Any]:
    """Read the cache, treating anything unreadable as an absent one.

    A missing file is the ordinary first run and is not reported. A file that
    exists but cannot be read as a cache document is reported as a warning,
    because it means the scopes in it are about to be baselined again and the
    changes since the last good write will never be reported.

    A file whose bytes are not UTF-8 at all is one of those, and is caught here
    rather than left to the caller: decoding raises `UnicodeDecodeError`, which
    is a `ValueError` and not an `OSError`, so catching only the latter would
    let a cache truncated mid-character - or a wholly unrelated binary file
    named as one - end the run instead of re-baselining it.

    Args:
        path: Path of the cache.

    Returns:
        The cache document, or an empty one when there is nothing to read.

    """
    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return empty_state()
    except (OSError, UnicodeError) as error:
        logger.warning("Could not read the watch cache at %s (%s); every scope will be recorded afresh.", path, error)
        return empty_state()

    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        logger.warning(
            "The watch cache at %s is not readable JSON (%s); every scope will be recorded afresh.", path, error
        )
        return empty_state()

    if not isinstance(document, dict) or not isinstance(document.get("scopes"), dict):
        logger.warning("The watch cache at %s is not a cache document; every scope will be recorded afresh.", path)
        return empty_state()

    return document


def save_state(path: str | Path, state: dict[str, Any]) -> None:
    """Write the cache, so that no reader ever sees a partial document.

    The document is written to a temporary file in the directory the cache lives
    in and renamed over it, which is atomic on every platform this runs on, and
    is flushed to disk first so the rename cannot publish an empty file.

    Args:
        path: Path of the cache.
        state: The cache document to write.

    Raises:
        OSError: If the cache directory, the temporary file or the rename
            cannot be written. The cache is left as it was.

    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f"{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            json.dump({**state, "version": STATE_VERSION}, file, indent=2, sort_keys=True)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        # The rename leaves nothing behind; a failure before it does.
        Path(temporary).unlink(missing_ok=True)


def _string_list(value: Any) -> list[str]:
    """Read a field holding a list of strings, ignoring anything else in it.

    Args:
        value: The value the document carries for the field.

    Returns:
        The strings it holds, sorted, or an empty list when it holds none.

    """
    if not isinstance(value, list):
        return []
    return sorted(item for item in value if isinstance(item, str))


def _read_snapshot(raw: Any) -> dict[str, Any] | None:
    """Read one issue's snapshot out of the cache.

    Only the fields the comparison reads are taken, so a field added by a newer
    version is ignored rather than fatal, and a field this version expects is
    read as its empty value when the document does not carry it.

    Args:
        raw: The value the document carries for the issue.

    Returns:
        The snapshot, or None when the value is not a snapshot object.

    """
    if not isinstance(raw, dict):
        return None

    snapshot: dict[str, Any] = {
        "issue_id": raw.get("issue_id") if isinstance(raw.get("issue_id"), int) else None,
        "number": raw.get("number") if isinstance(raw.get("number"), int) else None,
        "title": raw["title"] if isinstance(raw.get("title"), str) else "",
        "repository": raw["repository"] if isinstance(raw.get("repository"), str) else None,
        "updated_at": raw["updated_at"] if isinstance(raw.get("updated_at"), str) else "",
    }
    for field in _STRING_LISTS:
        snapshot[field] = _string_list(raw.get(field))
    return snapshot


def scope_snapshots(state: dict[str, Any], scope: str) -> dict[str, dict[str, Any]] | None:
    """Read the snapshots recorded for one scope.

    Args:
        state: The cache document.
        scope: Key of the scope.

    Returns:
        The snapshot of each issue, keyed as the cache keys them, or None when
        the scope has never been recorded - which is what baselines it rather
        than reporting every issue in it as new.

    """
    entry = state.get("scopes", {}).get(scope)
    if not isinstance(entry, dict):
        return None

    issues = entry.get("issues")
    if not isinstance(issues, dict):
        return {}

    snapshots: dict[str, dict[str, Any]] = {}
    for key, raw in issues.items():
        snapshot = _read_snapshot(raw)
        if snapshot is not None:
            snapshots[str(key)] = snapshot
    return snapshots


def record_scope(state: dict[str, Any], scope: str, snapshots: dict[str, dict[str, Any]]) -> None:
    """Replace what the cache records for one scope.

    Only that scope's entry is touched, so the scopes a run did not watch - and
    any key of the document this version does not know about - survive the write.

    Args:
        state: The cache document, modified in place.
        scope: Key of the scope.
        snapshots: The snapshot of each issue currently in the scope.

    """
    scopes = state.setdefault("scopes", {})
    scopes[scope] = {"issues": dict(snapshots)}


def save_scopes(path: str | Path, scopes: dict[str, dict[str, dict[str, Any]]]) -> None:
    """Record the scopes a run watched, leaving every other scope as it is.

    A run is authoritative only for the scopes it was asked to watch, so the
    document is re-read here - immediately before it is written, rather than at
    the start of the run - and only those scopes are replaced in it. Writing the
    document the run started from would put back whatever it held then, erasing
    the scopes a concurrent run recorded while this one was fetching and
    reporting every issue in them as new on the next run.

    Args:
        path: Path of the cache.
        scopes: The snapshots to record, keyed by scope.

    Raises:
        OSError: If the cache cannot be written. It is left as it was.

    """
    state = load_state(path)
    for scope, snapshots in scopes.items():
        record_scope(state, scope, snapshots)
    save_state(path, state)
