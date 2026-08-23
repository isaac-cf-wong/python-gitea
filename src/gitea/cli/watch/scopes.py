"""What a watch run watches, and how it reduces each of those to snapshots.

Two commands walk the same ground. `watch list` compares what is there now
against the cache and reports the difference; `watch advance` records what is
there now and reports nothing about it. They differ in what they do with the
snapshots and in nothing else - the options naming the scopes, the way a project
is resolved against a repository, the pages walked, and the fields kept are one
behaviour, and live here so the two commands cannot come to disagree about which
issues a scope holds or which key it is cached under.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from gitea.utils.pagination import PAGE_SIZE, collect_all_pages
from gitea.watch.changes import issue_key, issue_snapshot, usable_identifier

logger = logging.getLogger("gitea")


@dataclass(frozen=True)
class Scope:
    """One thing being watched, and the key its snapshots are cached under.

    Attributes:
        key: Key the scope's snapshots are recorded under in the cache.
        repository: Repository the scope is narrowed to, or None for the owner.
        project_id: Project the scope watches the board of, or None to watch the
            open issues of the repository instead.

    """

    key: str
    repository: str | None
    project_id: int | None


def build_scopes(owner: str, repositories: list[str], project_ids: list[int], command_name: str) -> list[Scope]:
    """Work out what a run watches from the options naming it.

    Every repository named is a scope of its own, and so is every project, which
    is how one invocation reports what changed across several repositories and
    boards at once. A project is resolved the way every other `project` command
    resolves one: against the repository when one is named, and against the owner
    itself when none is.

    Args:
        owner: The user or organization owning what is watched.
        repositories: The repositories named, in the order they were named.
        project_ids: The projects named, in the order they were named.
        command_name: The command being run, so a refusal names the invocation
            the user typed rather than whichever of the two this code is shared
            with.

    Returns:
        One scope per repository and per project, repositories first, and one
        scope per key: naming the same repository twice watches it once, rather
        than fetching it twice and comparing the second fetch against the same
        recorded snapshots as the first.

    Raises:
        CommandError: If nothing was named to watch, or if projects were named
            alongside more than one repository, which leaves no single scope for
            them to be resolved against.

    """
    from gitea.cli.utils.errors import CommandError  # noqa: PLC0415

    if not repositories and not project_ids:
        raise CommandError(
            f"'{command_name}' needs something to watch: pass --repository REPOSITORY for a repository's open "
            f"issues, --project-id ID for a project's board, or both. Either may be repeated to watch several."
        )

    if project_ids and len(repositories) > 1:
        raise CommandError(
            f"'{command_name}' cannot resolve --project-id against {len(repositories)} repositories: a project "
            f"belongs either to one repository or to the owner itself. Pass --project-id with at most one "
            f"--repository, or watch the repositories in a separate invocation."
        )

    scope_repository = repositories[0] if len(repositories) == 1 else None

    scopes = [Scope(key=f"repo:{owner}/{name}", repository=name, project_id=None) for name in repositories]
    scopes += [
        Scope(
            key=f"project:{owner}/{scope_repository}/{identifier}"
            if scope_repository
            else f"project:{owner}/{identifier}",
            repository=scope_repository,
            project_id=identifier,
        )
        for identifier in project_ids
    ]

    unique: dict[str, Scope] = {}
    for scope in scopes:
        unique.setdefault(scope.key, scope)
    return list(unique.values())


def _holder(issue: dict[str, Any], owner: str, repository: str | None) -> tuple[str, str] | None:
    """Work out which repository an issue's comments have to be listed under.

    A board holds cards from any repository of its owner, so the repository the
    scope was named with is not the one every issue on it lives in. The issue
    payload names its own, and the scope's repository is the fallback for a
    payload that does not.

    Args:
        issue: The issue data returned by the API.
        owner: The owner the scope was named with.
        repository: The repository the scope was narrowed to, or None.

    Returns:
        The owner and name of the repository holding the issue, or None when
        neither the payload nor the scope says.

    """
    payload = issue.get("repository")
    if isinstance(payload, dict):
        name, holder = payload.get("name"), payload.get("owner")
        if isinstance(name, str) and isinstance(holder, str):
            return holder, name

    return (owner, repository) if repository is not None else None


def _comments(client: Any, holder: tuple[str, str], number: Any) -> list[dict[str, Any]]:
    """Fetch every comment on one issue.

    Args:
        client: The API client.
        holder: The owner and name of the repository holding the issue.
        number: The number of the issue, as its payload carries it.

    Returns:
        The issue's comments, or an empty list when the payload names no issue
        to list them for.

    """
    issue_number = usable_identifier(number)
    if issue_number is None:
        return []

    comments, _ = collect_all_pages(
        lambda page: client.comment.list_comments(
            owner=holder[0],
            repository=holder[1],
            index=issue_number,
            page=page,
            limit=PAGE_SIZE,
        )
    )
    return comments


def _scope_issues(client: Any, owner: str, scope: Scope) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch the issues a scope currently holds, across every page of them.

    Args:
        client: The API client.
        owner: The owner the scope was named with.
        scope: The scope to fetch.

    Returns:
        A tuple of the issues and the metadata of the last response.

    """
    if scope.project_id is None:
        return collect_all_pages(
            lambda page: client.issue.list_issues(
                owner=owner,
                repository=scope.repository,
                state="open",
                page=page,
                limit=PAGE_SIZE,
            )
        )

    columns, metadata = collect_all_pages(
        lambda page: client.project.list_project_columns(
            owner=owner,
            repository=scope.repository,
            project_id=scope.project_id,
            page=page,
            limit=PAGE_SIZE,
        )
    )

    issues: list[dict[str, Any]] = []
    for column in columns:
        identifier = usable_identifier(column.get("id")) if isinstance(column, dict) else None
        if identifier is None:
            continue
        column_issues, metadata = collect_all_pages(
            lambda page, column_id=identifier: client.project.list_project_column_issues(
                owner=owner,
                repository=scope.repository,
                project_id=scope.project_id,
                column_id=column_id,
                page=page,
                limit=PAGE_SIZE,
            )
        )
        issues.extend(column_issues)

    return issues, metadata


def _snapshots(client: Any, owner: str, scope: Scope, issues: list[Any]) -> dict[str, dict[str, Any]]:
    """Reduce the issues of a scope to the snapshots the cache holds.

    Args:
        client: The API client.
        owner: The owner the scope was named with.
        scope: The scope the issues came from.
        issues: The issues the scope currently holds.

    Returns:
        The snapshot of each issue, keyed by its global ID. An entry that is not
        an issue, or that carries no global ID to key it by, is skipped: it
        cannot be compared against anything, and dropping it is better than
        reporting a change on every run because it never matches.

    """
    snapshots: dict[str, dict[str, Any]] = {}

    for issue in issues:
        if not isinstance(issue, dict):
            continue
        key = issue_key(issue)
        if key is None:
            logger.warning(
                "Skipping an issue of %s that carries no global ID, which is what it would be cached by.", scope.key
            )
            continue

        holder = _holder(issue, owner, scope.repository)
        if holder is None:
            logger.warning(
                "Not reading the comments of issue %s of %s: its payload does not name the repository holding it, "
                "so comment changes on it are not reported.",
                key,
                scope.key,
            )

        snapshots[key] = issue_snapshot(
            issue,
            _comments(client, holder, issue.get("number")) if holder else [],
            repository=f"{holder[0]}/{holder[1]}" if holder else None,
        )

    return snapshots


def collect_snapshots(
    client: Any, owner: str, scopes: list[Scope]
) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, Any]]:
    """Fetch every scope of a run and reduce each to the snapshots the cache holds.

    Args:
        client: The API client.
        owner: The owner the scopes were named with.
        scopes: The scopes the run watches.

    Returns:
        A tuple of the snapshots of each scope, keyed by scope key, and the
        metadata of the last response - which is what the envelope reports the
        status code of the run from.

    """
    recorded: dict[str, dict[str, dict[str, Any]]] = {}
    metadata: dict[str, Any] = {}

    for scope in scopes:
        issues, metadata = _scope_issues(client, owner, scope)
        recorded[scope.key] = _snapshots(client, owner, scope, issues)

    return recorded, metadata
