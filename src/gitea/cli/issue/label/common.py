"""What the `issue label` commands share: reading labels and issues, and reporting per issue.

A label is named on the command line by its name or by its numeric ID. Names are
resolved to IDs here, through the repository's label listing, rather than sent to
the API as they are: only a recent Gitea accepts names in an issue's label list,
and one that does not rejects the whole request. Resolving first also means an
unknown name is an error before anything is written, rather than a label silently
not applied, and before the first of several issues has been changed.

A value made only of ASCII digits is taken to be an ID. An ID is checked too,
against the repository's labels and then, for one not among them, against the
labels of the organization owning the repository, which the repository's listing
does not include. An ID found in neither is an error before anything is written:
Gitea drops an ID it cannot apply without saying so, so an ID copied from another
repository would otherwise be a silent no-op for `add`, and for `set` would leave
the issue with no labels at all.

Every command takes one `--issue-id` or several. With one, `data` is that issue's
labels, as `gitea-cli issue label list` emits them. With several, `data` holds one
entry per issue, `{"issue_id": ..., "labels": [...]}`, in the order the issues were
given, so that which issue was left with which labels can be read back. The shape
follows from how the command was invoked, never from what the API answered.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from requests import HTTPError

from gitea.cli.utils.errors import CommandError
from gitea.utils.pagination import PAGE_SIZE, collect_all_pages

if TYPE_CHECKING:
    from gitea.client.gitea import Gitea

logger = logging.getLogger("gitea")

ISSUE_IDS_HELP = "Issue number shown in the web UI. Repeat the option to act on several issues."
LABEL_HELP = "Label name or numeric ID. Repeat the option for several labels."

_NUMERIC_ID = re.compile(r"[0-9]+")
_NOT_FOUND = 404


def require_issue_ids(issue_ids: list[int] | None, *, command: str) -> list[int]:
    """Read the issues a command acts on.

    Args:
        issue_ids: The values passed as --issue-id, or None when it was omitted.
        command: The command being run, named as the user invoked it.

    Returns:
        The issue numbers, in the order given, each once.

    Raises:
        CommandError: If no issue was given.

    """
    if not issue_ids:
        raise CommandError(f"'{command}' needs an issue: pass --issue-id NUMBER, once per issue.")
    return list(dict.fromkeys(issue_ids))


def require_labels(labels: list[str] | None, *, command: str, hint: str = "") -> list[str]:
    """Read the labels a command acts on.

    Args:
        labels: The values passed as --label, or None when it was omitted.
        command: The command being run, named as the user invoked it.
        hint: A sentence appended to the error, pointing at a command that needs no label.

    Returns:
        The labels, as they were given.

    Raises:
        CommandError: If no label was given.

    """
    if not labels:
        message = f"'{command}' needs a label: pass --label NAME_OR_ID, once per label."
        raise CommandError(f"{message} {hint}" if hint else message)
    return labels


def _organization_label_ids(client: Gitea, owner: str) -> set[int]:
    """Read the IDs of the labels defined on the organization owning a repository.

    Args:
        client: The client to list the labels with.
        owner: The owner of the repository.

    Returns:
        The IDs, or none when the owner is a user rather than an organization,
        which Gitea answers with a 404.

    Raises:
        HTTPError: If the listing failed for any other reason.

    """
    try:
        defined, _ = collect_all_pages(
            lambda page: client.label.list_organization_labels(organization=owner, page=page, limit=PAGE_SIZE)
        )
    except HTTPError as e:
        response = getattr(e, "response", None)
        if response is None or response.status_code != _NOT_FOUND:
            raise
        return set()
    return {label["id"] for label in defined}


def resolve_label_ids(client: Gitea, owner: str, repository: str, labels: list[str], *, command: str) -> list[int]:
    """Resolve the labels given on the command line to their IDs, and check that each exists.

    The repository's labels are listed once for all of them. The organization's
    are listed only when an ID is not among the repository's.

    Args:
        client: The client to list the labels with.
        owner: The owner of the repository.
        repository: The name of the repository.
        labels: The labels, each a name or a numeric ID.
        command: The command being run, named as the user invoked it.

    Returns:
        The label IDs, in the order given, each once.

    Raises:
        CommandError: If a name matches no label of the repository, or more than
            one, or an ID is neither a label of the repository nor of the
            organization owning it.

    """
    defined, _ = collect_all_pages(
        lambda page: client.label.list_labels(owner=owner, repository=repository, page=page, limit=PAGE_SIZE)
    )
    by_name: dict[str, list[int]] = {}
    for label in defined:
        by_name.setdefault(label["name"], []).append(label["id"])

    names = [label for label in labels if not _NUMERIC_ID.fullmatch(label)]
    unknown = [name for name in names if name not in by_name]
    if unknown:
        raise CommandError(
            f"'{command}': no label named {', '.join(repr(name) for name in unknown)} in {owner}/{repository}. "
            f"Names are matched exactly, case included; 'gitea-cli label list' shows the repository's labels. "
            f"A label defined on the organization is not looked up by name: pass its numeric ID."
        )
    ambiguous = [name for name in names if len(by_name[name]) > 1]
    if ambiguous:
        raise CommandError(
            f"'{command}': more than one label is named {', '.join(repr(name) for name in ambiguous)} "
            f"in {owner}/{repository}. Pass the numeric ID of the one you mean."
        )

    repository_ids = {label["id"] for label in defined}
    ids = [int(label) for label in labels if _NUMERIC_ID.fullmatch(label)]
    elsewhere = [label_id for label_id in dict.fromkeys(ids) if label_id not in repository_ids]
    if elsewhere:
        organization_ids = _organization_label_ids(client, owner)
        missing = [label_id for label_id in elsewhere if label_id not in organization_ids]
        if missing:
            raise CommandError(
                f"'{command}': no label with ID {', '.join(str(label_id) for label_id in missing)} "
                f"in {owner}/{repository} or on its owner {owner}. "
                f"A label's ID belongs to the repository or organization defining it, so an ID read from "
                f"another repository names a different label there, or none; nothing was changed. "
                f"Pass the label's name instead; 'gitea-cli label list' shows the repository's labels."
            )

    resolved = [int(label) if _NUMERIC_ID.fullmatch(label) else by_name[label][0] for label in labels]
    return list(dict.fromkeys(resolved))


def for_each_issue(
    issue_ids: list[int],
    action: Callable[[int], tuple[list[dict[str, Any]], dict[str, Any]]],
    *,
    command: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run a command on each issue in turn and shape what it reports.

    The issues are acted on one after another, so a failure part-way leaves the
    ones before it changed. The error then names them, since the command prints
    nothing on stdout when it fails and the caller could not tell otherwise.

    Args:
        issue_ids: The issues to act on.
        action: Callable acting on one issue and returning its resulting labels
            and the metadata of the last response. Extra keys in the metadata
            beyond `status_code` are reported with that issue.
        command: The command being run, named as the user invoked it.

    Returns:
        A tuple containing the data and the metadata of the envelope: for one
        issue, its labels and its metadata; for several, one entry per issue.

    Raises:
        CommandError: If acting on an issue after the first failed. A failure
            on the first issue is raised as it was, since nothing else changed.

    """
    entries: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}
    for issue_id in issue_ids:
        try:
            labels, metadata = action(issue_id)
        except Exception as e:
            if not entries:
                raise
            done = ", ".join(str(entry["issue_id"]) for entry in entries)
            raise CommandError(
                f"'{command}' failed on issue {issue_id}: {e}. "
                f"Issues {done} were already done, and issue {issue_id} may be partly done; "
                f"the rest were not attempted."
            ) from e
        extra = {key: value for key, value in metadata.items() if key != "status_code"}
        entries.append({"issue_id": issue_id, "labels": labels, **extra})

    if len(entries) == 1:
        return entries[0]["labels"], metadata
    return entries, {"status_code": metadata["status_code"]}


def remove_carried_labels(
    client: Gitea, owner: str, repository: str, issue_id: int, label_ids: list[int]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Remove from one issue those of the labels it carries, and read back what it is left with.

    A label the issue does not carry is not an error: removing it would leave the
    issue as it is either way, and a command run over several issues meets that
    routinely. It is not silent either: it is logged, and named in the metadata
    as `not_on_issue`, so a caller can tell a removal from a label that was never
    there.

    Args:
        client: The client to act with.
        owner: The owner of the repository.
        repository: The name of the repository.
        issue_id: The issue to remove the labels from.
        label_ids: The IDs of the labels to remove.

    Returns:
        A tuple containing the issue's resulting labels, and metadata naming the
        IDs of the requested labels it did not carry.

    """
    current, _ = client.issue.list_issue_labels(owner=owner, repository=repository, index=issue_id)
    carried = {label["id"] for label in current}
    absent = [label_id for label_id in label_ids if label_id not in carried]
    if absent:
        logger.warning(
            "Issue %s does not carry label %s; left as it is.",
            issue_id,
            ", ".join(str(label_id) for label_id in absent),
        )

    for label_id in label_ids:
        if label_id in carried:
            client.issue.remove_issue_label(owner=owner, repository=repository, index=issue_id, label=label_id)

    remaining, metadata = client.issue.list_issue_labels(owner=owner, repository=repository, index=issue_id)
    return remaining, {**metadata, "not_on_issue": absent}
