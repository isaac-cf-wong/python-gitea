"""Resolve which project column an issue's cards sit in.

An issue payload lists the projects the issue is on, but each entry describes a
project, not a card: Gitea's ``Project`` schema carries no column, and the issue
endpoint takes no parameter that would expand one, so an issue on its own never
says where on a board it sits. The only endpoint relating a card to a column is
the per-column issue listing, so the column is resolved here, client-side, by
walking a project's columns until the one listing the issue is found.

The walk is bounded by the size of the board rather than of the repository, and
stops at the first column holding the card, so the cost per project is the
listing of its columns plus the listing of the issues of every column up to and
including the one holding the card. A listing whose page comes back with items
in it costs one further request, because a page filled to the instance's cap
cannot be told from the last one. Each project's ``column_id`` is set to the
column holding its card, or to None when the issue has no card on that project.

An individual (user-owned) project is the one case that cannot be resolved: its
columns live under the ``/user/projects`` endpoints, which this library does not
wrap. The lookup is attempted against the organization endpoint, its rejection is
logged, and ``column_id`` stays None rather than failing the issue itself.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aiohttp import ClientError
from requests import RequestException

from gitea.utils.pagination import PAGE_SIZE, iter_async_pages, iter_pages

if TYPE_CHECKING:
    from gitea.client.async_gitea import AsyncGitea
    from gitea.client.gitea import Gitea

logger = logging.getLogger("gitea")


def _is_resolvable(issue: dict[str, Any]) -> bool:
    """Report whether an issue carries what a column lookup needs.

    A payload that is not an issue object at all is reported as nothing to
    resolve, so a body the caller already has in hand is never turned into a
    failure by the enrichment of it.

    Args:
        issue: The issue data returned by the API.

    Returns:
        True when the issue lists projects and has the global ID that the column
        listings identify their issues by.

    """
    if not isinstance(issue, dict):
        return False
    return isinstance(issue.get("projects"), list) and isinstance(issue.get("id"), int)


def _identifier(item: dict[str, Any]) -> int | None:
    """Extract the ID of a project or a column.

    Args:
        item: The project or column data returned by the API.

    Returns:
        The ID, or None when the payload carries no usable one.

    """
    identifier = item.get("id")
    return identifier if isinstance(identifier, int) else None


def _column_scope_repository(project: dict[str, Any], repository: str) -> str | None:
    """Choose the repository to scope a project's column listing to.

    A repository project takes its issues from its own repository, so its
    columns are listed under that repository. An organization project takes them
    from any repository of the organization, so its columns are listed under the
    organization instead, which is what a repository of None selects.

    Args:
        project: The project data returned by the API.
        repository: The name of the repository holding the issue.

    Returns:
        The repository name for a repository project, or None otherwise.

    """
    repo_id = project.get("repo_id")
    if project.get("type") == "repository" or (isinstance(repo_id, int) and repo_id > 0):
        return repository
    return None


def _holds_issue(issues: list[dict[str, Any]], issue_id: int) -> bool:
    """Report whether a page of a column's issues lists the issue.

    Args:
        issues: The issues of one page of a column's listing.
        issue_id: The global ID of the issue.

    Returns:
        True when the issue is one of them.

    """
    return any(_identifier(issue) == issue_id for issue in issues)


_LOOKUP_FAILED = "Could not resolve the column of issue %s on project %s, reporting it as null: %s"


def resolve_project_column_ids(
    *,
    client: Gitea,
    owner: str,
    repository: str,
    issue: dict[str, Any],
) -> dict[str, Any]:
    """Populate the ``column_id`` of every project an issue is on.

    Args:
        client: The Gitea client used for the lookups.
        owner: The owner of the repository holding the issue.
        repository: The name of the repository holding the issue.
        issue: The issue data returned by the API.

    Returns:
        The issue data with a ``column_id`` on each of its projects, holding the
        column the issue's card sits in or None when it has no card there. The
        issue is returned unchanged when it lists no projects.

    """
    if not _is_resolvable(issue):
        return issue

    issue_id: int = issue["id"]
    projects: list[dict[str, Any]] = []
    for project in issue["projects"]:
        column_id = None
        project_id = _identifier(project)
        if project_id is not None:
            try:
                column_id = _find_column_id(
                    client=client,
                    owner=owner,
                    repository=_column_scope_repository(project, repository),
                    project_id=project_id,
                    issue_id=issue_id,
                )
            except RequestException as e:
                # Enriching the issue is not worth failing the issue over: the
                # payload the caller asked for is already in hand.
                logger.warning(_LOOKUP_FAILED, issue_id, project_id, e)
        projects.append({**project, "column_id": column_id})

    return {**issue, "projects": projects}


def _find_column_id(
    *,
    client: Gitea,
    owner: str,
    repository: str | None,
    project_id: int,
    issue_id: int,
) -> int | None:
    """Find the column of a project that lists an issue.

    Args:
        client: The Gitea client used for the lookups.
        owner: The owner of the repository or organization holding the project.
        repository: The name of the repository holding the project, or None for
            an organization project.
        project_id: The ID of the project.
        issue_id: The global ID of the issue.

    Returns:
        The ID of the column listing the issue, or None when no column of the
        project lists it.

    """
    for columns, _ in iter_pages(
        lambda page: client.project.list_project_columns(
            owner=owner,
            repository=repository,
            project_id=project_id,
            page=page,
            limit=PAGE_SIZE,
        )
    ):
        for column in columns:
            column_id = _identifier(column)
            if column_id is None:
                continue
            for issues, _ in iter_pages(
                lambda page, column_id=column_id: client.project.list_project_column_issues(
                    owner=owner,
                    repository=repository,
                    project_id=project_id,
                    column_id=column_id,
                    page=page,
                    limit=PAGE_SIZE,
                )
            ):
                if _holds_issue(issues, issue_id):
                    return column_id
    return None


async def resolve_async_project_column_ids(
    *,
    client: AsyncGitea,
    owner: str,
    repository: str,
    issue: dict[str, Any],
) -> dict[str, Any]:
    """Populate the ``column_id`` of every project an issue is on.

    Args:
        client: The asynchronous Gitea client used for the lookups.
        owner: The owner of the repository holding the issue.
        repository: The name of the repository holding the issue.
        issue: The issue data returned by the API.

    Returns:
        The issue data with a ``column_id`` on each of its projects, holding the
        column the issue's card sits in or None when it has no card there. The
        issue is returned unchanged when it lists no projects.

    """
    if not _is_resolvable(issue):
        return issue

    issue_id: int = issue["id"]
    projects: list[dict[str, Any]] = []
    for project in issue["projects"]:
        column_id = None
        project_id = _identifier(project)
        if project_id is not None:
            try:
                column_id = await _find_async_column_id(
                    client=client,
                    owner=owner,
                    repository=_column_scope_repository(project, repository),
                    project_id=project_id,
                    issue_id=issue_id,
                )
            except ClientError as e:
                # As above: the issue itself was retrieved, so only the column
                # is lost.
                logger.warning(_LOOKUP_FAILED, issue_id, project_id, e)
        projects.append({**project, "column_id": column_id})

    return {**issue, "projects": projects}


async def _find_async_column_id(
    *,
    client: AsyncGitea,
    owner: str,
    repository: str | None,
    project_id: int,
    issue_id: int,
) -> int | None:
    """Find the column of a project that lists an issue.

    Args:
        client: The asynchronous Gitea client used for the lookups.
        owner: The owner of the repository or organization holding the project.
        repository: The name of the repository holding the project, or None for
            an organization project.
        project_id: The ID of the project.
        issue_id: The global ID of the issue.

    Returns:
        The ID of the column listing the issue, or None when no column of the
        project lists it.

    """
    async for columns, _ in iter_async_pages(
        lambda page: client.project.list_project_columns(
            owner=owner,
            repository=repository,
            project_id=project_id,
            page=page,
            limit=PAGE_SIZE,
        )
    ):
        for column in columns:
            column_id = _identifier(column)
            if column_id is None:
                continue
            async for issues, _ in iter_async_pages(
                lambda page, column_id=column_id: client.project.list_project_column_issues(
                    owner=owner,
                    repository=repository,
                    project_id=project_id,
                    column_id=column_id,
                    page=page,
                    limit=PAGE_SIZE,
                )
            ):
                if _holds_issue(issues, issue_id):
                    return column_id
    return None
