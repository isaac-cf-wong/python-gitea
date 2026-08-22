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

Resolution is best-effort by construction. The walk is a sequence of separate
requests against a board that may be edited while it runs, so a card moved
mid-walk can be reported under either column or under none. Any failure of a
lookup - a refusal, a transport error, a timeout - is logged and leaves that
project's ``column_id`` at None instead of failing the issue whose payload the
caller already has in hand. ``column_id`` is therefore always present on a
project entry, and None means "not resolved" as much as it means "no card".

That last part is the enrichment's choice and not the walk's: ``find_card_column_id``
raises what the lookup raised and returns None only for a board no column of which
lists the issue. It is the answer to "has this issue a card on this project, and
where" wherever that has to be told apart from "the board could not be read" -
the project issue commands ask it before moving a card, because Gitea's move
endpoint reports success without doing anything when there is no card to move.
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


def _lists_projects(issue: Any) -> bool:
    """Report whether an issue payload has projects to attach a column to.

    A payload that is not an issue object at all is reported as nothing to
    resolve, so a body the caller already has in hand is never turned into a
    failure by the enrichment of it.

    Args:
        issue: The issue data returned by the API.

    Returns:
        True when the payload is an issue object listing projects.

    """
    return isinstance(issue, dict) and isinstance(issue.get("projects"), list)


def _identifier(item: Any) -> int | None:
    """Extract the ID of an issue, a project or a column.

    Args:
        item: The issue, project or column data returned by the API.

    Returns:
        The ID, or None when the payload is not an object carrying a usable one.

    """
    if not isinstance(item, dict):
        return None
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


def _holds_issue(issues: list[Any], issue_id: int) -> bool:
    """Report whether a page of a column's issues lists the issue.

    Args:
        issues: The issues of one page of a column's listing. An entry that is
            not an issue object matches nothing rather than raising.
        issue_id: The global ID of the issue.

    Returns:
        True when the issue is one of them.

    """
    return any(_identifier(issue) == issue_id for issue in issues)


_LOOKUP_FAILED = "Could not resolve the column of issue %s on project %s, reporting it as null: %s"

# aiohttp raises its total timeout as a bare asyncio.TimeoutError, which is the
# builtin TimeoutError since Python 3.11 and is not a ClientError. It is caught
# alongside one so that the asynchronous path degrades on a timeout exactly as
# the synchronous path does, where requests.Timeout is a RequestException.
_ASYNC_LOOKUP_ERRORS = (ClientError, TimeoutError)


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
        The issue data with a ``column_id`` on every project entry, holding the
        column the issue's card sits in, or None when it has no card there and
        when the lookup could not be made or failed. The issue is returned
        unchanged when it lists no projects.

    """
    if not _lists_projects(issue):
        return issue

    # Column listings identify their issues by global ID, so without one on the
    # issue nothing can be matched and every column stays null. The field is
    # still attached, so that consumers see one contract for every issue.
    issue_id = _identifier(issue)
    projects: list[Any] = []
    for project in issue["projects"]:
        if not isinstance(project, dict):
            # An entry that is not a project object has nothing to look a column
            # up by and nothing to attach one to, so it is passed through.
            projects.append(project)
            continue
        column_id = None
        project_id = _identifier(project)
        if project_id is not None and issue_id is not None:
            try:
                column_id = find_card_column_id(
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


def find_card_column_id(
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
            if column_holds_card(
                client=client,
                owner=owner,
                repository=repository,
                project_id=project_id,
                column_id=column_id,
                issue_id=issue_id,
            ):
                return column_id
    return None


def column_holds_card(
    *,
    client: Gitea,
    owner: str,
    repository: str | None,
    project_id: int,
    column_id: int,
    issue_id: int,
) -> bool:
    """Report whether one column of a project holds an issue's card.

    The single column the board walk above asks about, asked on its own: a caller
    that already knows which column it means - one confirming a card arrived
    where it was sent - pays for that column's listing rather than the board's.

    Args:
        client: The Gitea client used for the lookup.
        owner: The owner of the repository or organization holding the project.
        repository: The name of the repository holding the project, or None for
            an organization project.
        project_id: The ID of the project.
        column_id: The ID of the column.
        issue_id: The global ID of the issue.

    Returns:
        True when a card for the issue is in that column.

    """
    for issues, _ in iter_pages(
        lambda page: client.project.list_project_column_issues(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
            page=page,
            limit=PAGE_SIZE,
        )
    ):
        if _holds_issue(issues, issue_id):
            return True
    return False


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
        The issue data with a ``column_id`` on every project entry, holding the
        column the issue's card sits in, or None when it has no card there and
        when the lookup could not be made or failed. The issue is returned
        unchanged when it lists no projects.

    """
    if not _lists_projects(issue):
        return issue

    # As above: no global ID means no card can be matched, and the field is
    # attached all the same.
    issue_id = _identifier(issue)
    projects: list[Any] = []
    for project in issue["projects"]:
        if not isinstance(project, dict):
            projects.append(project)
            continue
        column_id = None
        project_id = _identifier(project)
        if project_id is not None and issue_id is not None:
            try:
                column_id = await find_async_card_column_id(
                    client=client,
                    owner=owner,
                    repository=_column_scope_repository(project, repository),
                    project_id=project_id,
                    issue_id=issue_id,
                )
            except _ASYNC_LOOKUP_ERRORS as e:
                # As above: the issue itself was retrieved, so only the column
                # is lost.
                logger.warning(_LOOKUP_FAILED, issue_id, project_id, e)
        projects.append({**project, "column_id": column_id})

    return {**issue, "projects": projects}


async def find_async_card_column_id(
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
            if await async_column_holds_card(
                client=client,
                owner=owner,
                repository=repository,
                project_id=project_id,
                column_id=column_id,
                issue_id=issue_id,
            ):
                return column_id
    return None


async def async_column_holds_card(
    *,
    client: AsyncGitea,
    owner: str,
    repository: str | None,
    project_id: int,
    column_id: int,
    issue_id: int,
) -> bool:
    """Report whether one column of a project holds an issue's card.

    Args:
        client: The asynchronous Gitea client used for the lookup.
        owner: The owner of the repository or organization holding the project.
        repository: The name of the repository holding the project, or None for
            an organization project.
        project_id: The ID of the project.
        column_id: The ID of the column.
        issue_id: The global ID of the issue.

    Returns:
        True when a card for the issue is in that column.

    """
    async for issues, _ in iter_async_pages(
        lambda page: client.project.list_project_column_issues(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
            page=page,
            limit=PAGE_SIZE,
        )
    ):
        if _holds_issue(issues, issue_id):
            return True
    return False
