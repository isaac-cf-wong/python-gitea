"""The snapshot a watch run takes of an issue, and the comparison of two of them.

An issue payload is far larger than the handful of things worth waking someone
up for, and most of it changes for reasons nobody wants a line of output about.
A snapshot keeps the four that a watch reports on - who it is assigned to, what
it is labelled, which comments it carries, and whether it is there at all - plus
the fields needed to name the issue in the report.

Comments are compared by hash rather than by count, so that a comment added and
another deleted between two runs is two changes and not none, and so that the
comparison needs nothing from the previous run except the hashes it recorded.
`comment_hash` is stable across re-fetches: the same comment always hashes to the
same value, and an edited one does not, which is what makes an edit show up as a
change rather than disappear.

`updated_at` is recorded but is not itself compared. Gitea bumps it for every
edit, including ones a watch has nothing to say about, so comparing it would
report a body reworded as indistinguishable from a comment added. The
consequence, stated plainly: an issue whose title or body alone was edited is
not reported as changed.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# Length the comment digest is truncated to. 16 hex characters is 64 bits, which
# for the comments of one issue is far past the point where a collision would be
# the reason a change went unreported.
_HASH_LENGTH = 16

# The kinds of change, in the order an issue's changes are reported in.
_FIELD_KINDS = (("assignees", "assignees"), ("labels", "labels"))


def comment_hash(comment: dict[str, Any]) -> str:
    """Hash a comment's identity, stably across re-fetches.

    The digest is taken over the comment's ID, author, body and timestamps,
    serialized as JSON so that no value can be confused with the boundary
    between two of them - a body ending in the separator would otherwise hash as
    a different comment's body beginning with it.

    Including the timestamps means an edited comment hashes differently from the
    comment it replaced, so an edit is reported as a change rather than passing
    for the comment already recorded.

    Args:
        comment: The comment data returned by the API. A payload missing any of
            these fields hashes as if it carried them empty, rather than
            raising.

    Returns:
        The first `_HASH_LENGTH` hex characters of the SHA-256 digest.

    """
    user = comment.get("user")
    author = user.get("login") if isinstance(user, dict) else None
    identity = [
        comment.get("id"),
        author if isinstance(author, str) else "",
        comment.get("body") if isinstance(comment.get("body"), str) else "",
        comment.get("created_at") if isinstance(comment.get("created_at"), str) else "",
        comment.get("updated_at") if isinstance(comment.get("updated_at"), str) else "",
    ]
    raw = json.dumps(identity, separators=(",", ":"), sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:_HASH_LENGTH]


def _names(entries: Any, field: str) -> list[str]:
    """Read the names out of a list of user or label objects.

    Args:
        entries: The value the issue payload carries for the field. Anything
            that is not a list of objects naming themselves contributes nothing,
            so a malformed payload narrows the snapshot instead of failing it.
        field: The key each object names itself by.

    Returns:
        The names, sorted and without duplicates.

    """
    if not isinstance(entries, list):
        return []
    names = {entry[field] for entry in entries if isinstance(entry, dict) and isinstance(entry.get(field), str)}
    return sorted(names)


def issue_key(issue: dict[str, Any]) -> str | None:
    """Build the key an issue is recorded under.

    The global ID is used rather than the number shown in the web UI, because a
    project scope holds issues from several repositories and their numbers
    collide.

    Args:
        issue: The issue data returned by the API.

    Returns:
        The key, or None when the payload carries no usable global ID.

    """
    identifier = issue.get("id")
    # bool is an int, and an issue whose ID came back as one is not an issue.
    if not isinstance(identifier, int) or isinstance(identifier, bool):
        return None
    return str(identifier)


def issue_snapshot(
    issue: dict[str, Any], comments: list[dict[str, Any]], repository: str | None = None
) -> dict[str, Any]:
    """Reduce an issue and its comments to what a watch compares and reports.

    Args:
        issue: The issue data returned by the API.
        comments: The issue's comments, as returned by the API. Pass an empty
            list for an issue whose comments were not fetched; its comment
            hashes are then empty and no comment change is ever reported for it.
        repository: Full name of the repository holding the issue, used to name
            it in the report, or None when it could not be determined.

    Returns:
        The snapshot of the issue.

    """
    identifier = issue.get("id")
    number = issue.get("number")
    title = issue.get("title")
    updated_at = issue.get("updated_at")

    return {
        "issue_id": identifier if isinstance(identifier, int) and not isinstance(identifier, bool) else None,
        "number": number if isinstance(number, int) and not isinstance(number, bool) else None,
        "title": title if isinstance(title, str) else "",
        "repository": repository,
        "updated_at": updated_at if isinstance(updated_at, str) else "",
        "assignees": _names(issue.get("assignees"), "login"),
        "labels": _names(issue.get("labels"), "name"),
        "comment_hashes": sorted({comment_hash(comment) for comment in comments if isinstance(comment, dict)}),
    }


def _change(snapshot: dict[str, Any], kind: str, detail: str, added: list[str], removed: list[str]) -> dict[str, Any]:
    """Build one change record.

    Every record carries the same keys whatever the kind, so a consumer can read
    `added` and `removed` without first asking what happened.

    Args:
        snapshot: The snapshot naming the issue the change is on.
        kind: What changed.
        detail: The change, phrased for a human digest.
        added: What appeared, empty where the kind has nothing to add.
        removed: What went away, empty where the kind has nothing to remove.

    Returns:
        The change record.

    """
    return {
        "kind": kind,
        "issue_id": snapshot.get("issue_id"),
        "number": snapshot.get("number"),
        "title": snapshot.get("title", ""),
        "repository": snapshot.get("repository"),
        "detail": detail,
        "added": added,
        "removed": removed,
    }


def _delta(previous: list[str], current: list[str]) -> tuple[list[str], list[str]]:
    """Compare two sets of names.

    Args:
        previous: The names recorded by the last run.
        current: The names the issue carries now.

    Returns:
        A tuple of the names that appeared and the names that went away, sorted.

    """
    before, after = set(previous), set(current)
    return sorted(after - before), sorted(before - after)


def _describe_names(added: list[str], removed: list[str]) -> str:
    """Phrase a change of names as the digest prints it.

    Args:
        added: The names that appeared.
        removed: The names that went away.

    Returns:
        The names, each prefixed by whether it appeared or went away.

    """
    return " ".join([*(f"+{name}" for name in added), *(f"-{name}" for name in removed)])


def _describe_comments(added: list[str], removed: list[str]) -> str:
    """Phrase a change of comments as the digest prints it.

    Comments are compared by hash, which says nothing to a human, so the digest
    reports how many appeared and how many went away instead of which.

    Args:
        added: Hashes of the comments that appeared.
        removed: Hashes of the comments that went away.

    Returns:
        The counts of each, naming only the ones that are not zero.

    """
    parts = []
    if added:
        parts.append(f"{len(added)} new")
    if removed:
        parts.append(f"{len(removed)} removed")
    return ", ".join(parts)


def _sort_key(item: tuple[str, dict[str, Any]]) -> tuple[int, int, str]:
    """Order the issues of a scope so a report does not depend on fetch order.

    Args:
        item: An issue's key and its snapshot.

    Returns:
        A sort key placing the issues with a number first, in number order, and
        ordering the rest by their key.

    """
    key, snapshot = item
    number = snapshot.get("number")
    return (0, number, key) if isinstance(number, int) else (1, 0, key)


def detect_changes(
    current: dict[str, dict[str, Any]],
    previous: dict[str, dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Compare the snapshots of one scope against the ones recorded for it.

    An issue that changed in more than one way contributes one record per way,
    as a digest reads better naming each change than one line naming three.

    Args:
        current: The snapshot of each issue in the scope now, keyed by
            `issue_key`.
        previous: The snapshots the last run recorded for the scope, or None
            when the scope has never been recorded. None baselines the scope:
            no change is reported, whatever is in it.

    Returns:
        The changes since the recorded snapshots, ordered by issue and then by
        what changed. Empty when nothing changed, which is the whole point of
        the command.

    """
    if previous is None:
        return []

    changes: list[dict[str, Any]] = []

    for key, snapshot in sorted(current.items(), key=_sort_key):
        before = previous.get(key)
        if before is None:
            changes.append(_change(snapshot, "new", "new issue", [], []))
            continue

        for field, kind in _FIELD_KINDS:
            added, removed = _delta(before.get(field, []), snapshot.get(field, []))
            if added or removed:
                changes.append(_change(snapshot, kind, _describe_names(added, removed), added, removed))

        added, removed = _delta(before.get("comment_hashes", []), snapshot.get("comment_hashes", []))
        if added or removed:
            changes.append(_change(snapshot, "comments", _describe_comments(added, removed), added, removed))

    gone = {key: snapshot for key, snapshot in previous.items() if key not in current}
    for _, snapshot in sorted(gone.items(), key=_sort_key):
        changes.append(_change(snapshot, "gone", "no longer listed", [], []))

    return changes


def format_change(change: dict[str, Any]) -> str:
    """Render one change as the line the human digest prints for it.

    The issue is named the way it is written in a browser's address bar and in
    prose - `owner/repo#15` - so a line can be read, pasted and grepped without
    consulting the scope it came from.

    Args:
        change: The change record.

    Returns:
        One line naming the issue, what changed and what it changed to.

    """
    number, repository = change.get("number"), change.get("repository")
    if isinstance(number, int):
        reference = f"{repository}#{number}" if repository else f"#{number}"
    else:
        reference = f"issue {change.get('issue_id')}"

    line = f"{reference} {change.get('kind')}: {change.get('detail')}"
    title = change.get("title")
    return f"{line} · {title}" if title else line
