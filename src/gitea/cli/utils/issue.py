"""Helpers for addressing issues from the project CLI commands.

Gitea identifies an issue in two ways: the number shown in the web UI, which
is local to a repository, and the global ID, which the project endpoints
expect. The helpers here let the project commands take the number whenever the
repository holding the issue is known, and turn the endpoints' rejections into
errors that say what to do next.

The repository holding the issue is not the same thing as the repository
holding the project: a repository project takes its issues from its own
repository, while an organization project takes them from any repository of
the organization, which is why the commands let that one be named separately.

One endpoint's rejection has to be manufactured here, because it does not
reject: moving an issue that is not on a project moves the row relating the two,
of which there is none, and Gitea answers that with a success and an empty body.
`run_project_issue_move` therefore finds the card before moving it, and reports
its absence itself - a success that moved nothing is the one failure a caller
cannot see.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from requests import ConnectionError as RequestsConnectionError
from requests import HTTPError, RequestException, Timeout

from gitea.cli.utils.errors import CommandError, request_failed_message, unreachable_message
from gitea.issue.project_column import find_card_column_id

if TYPE_CHECKING:
    from collections.abc import Callable

    from gitea.client.gitea import Gitea

_NOT_FOUND = 404


def _is_success(status_code: int) -> bool:
    """Report whether a status code is a success.

    Args:
        status_code: The HTTP status code returned by the API.

    Returns:
        True when the status code is in the 2xx range.

    """
    return 200 <= status_code < 300  # noqa: PLR2004


def _status_code_of(error: HTTPError) -> int | None:
    """Extract the status code an HTTP error carries.

    Args:
        error: The error raised by the client.

    Returns:
        The status code, or None when the error carries no response.

    """
    response = getattr(error, "response", None)
    return None if response is None else response.status_code


def _describe(status_code: int | None, error: HTTPError | None = None) -> str:
    """Describe an unsuccessful call for use in an error message.

    Args:
        status_code: The status code of the call, if known.
        error: The error raised by the client, used when the status code is unknown.

    Returns:
        The description of the failure.

    """
    if status_code is None:
        return f"the request failed ({error})"
    return f"Gitea returned HTTP {status_code}"


def resolve_issue_id(*, client: Gitea, owner: str, repository: str | None, issue_number: int) -> int:
    """Resolve a repository issue number to the global issue ID.

    When the repository holding the issue is known, `issue_number` is the number
    shown in the web UI and is looked up against that repository. When it is
    not, there is nothing to look the number up in, so the value is taken to be
    the global ID already and returned unchanged.

    Args:
        client: The Gitea client used for the lookup.
        owner: The owner of the repository.
        repository: The name of the repository holding the issue, or None when
            it is not known.
        issue_number: The issue number of the repository, or the global issue ID
            when `repository` is None.

    Returns:
        The global issue ID that the project endpoints expect.

    Raises:
        CommandError: If the repository has no issue with that number, the
            lookup was refused, the instance could not be reached, or the
            request failed without reaching a response.

    """
    if repository is None:
        return issue_number

    try:
        data, metadata = client.issue.get_issue(owner=owner, repository=repository, index=issue_number)
    except HTTPError as e:
        status_code = _status_code_of(e)
        if status_code != _NOT_FOUND:
            raise CommandError(
                f"Could not look up issue #{issue_number} in {owner}/{repository}: {_describe(status_code, e)}."
            ) from e
        raise CommandError(_unknown_issue_message(owner, repository, issue_number, status_code)) from e
    except (RequestsConnectionError, Timeout) as e:
        # No response came back, so nothing is known about the issue itself.
        raise CommandError(unreachable_message(e, client.base_url)) from e
    except RequestException as e:
        # Also no response, but a malformed URL or an unreadable body is not the
        # instance being unreachable, so only the request itself is blamed.
        raise CommandError(request_failed_message(e, client.base_url)) from e

    issue_id = data.get("id") if isinstance(data, dict) else None
    status_code = metadata.get("status_code", 0)
    if not _is_success(status_code) or not isinstance(issue_id, int):
        raise CommandError(_unknown_issue_message(owner, repository, issue_number, status_code))
    return issue_id


def _unknown_issue_message(owner: str, repository: str, issue_number: int, status_code: int | None) -> str:
    """Build the error message for an issue number the repository does not have.

    Args:
        owner: The owner of the repository.
        repository: The name of the repository.
        issue_number: The value the user passed as --issue-id.
        status_code: The status code of the lookup, if known.

    Returns:
        The message describing the failure and how to act on it.

    """
    return (
        f"No issue #{issue_number} in {owner}/{repository} ({_describe(status_code)}). "
        f"--issue-id is the issue number shown in the web UI once the repository holding the issue is known; "
        f"run 'gitea-cli issue list --owner {owner} --repository {repository}' to see the numbers in use."
    )


def run_project_issue_call(
    *,
    client: Gitea,
    call: Callable[[int], tuple[dict[str, Any], dict[str, Any]]],
    action: str,
    owner: str,
    project_id: int,
    issue_number: int,
    issue_repository: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run a project issue call against the issue the user named.

    The issue is resolved first, so `--issue-id` can be the number shown in the
    web UI, and a rejection by the project endpoint is reported as an error
    naming both the issue and what to check, rather than as a bare HTTP status.
    On success the resolved global ID is recorded in the metadata, so the caller
    can see which issue was acted on.

    Args:
        client: The Gitea client to call.
        call: The API call, taking the resolved global issue ID.
        action: The verb describing the call, used in the error message.
        owner: The owner of the repository.
        project_id: The ID of the project.
        issue_number: The value the user passed as --issue-id.
        issue_repository: The name of the repository holding the issue, or None
            when it is not known and `issue_number` is therefore a global ID.

    Returns:
        A tuple containing the payload and the metadata, the latter carrying the
        resolved global issue ID whenever the number was resolved.

    Raises:
        CommandError: If the issue could not be resolved, the call was refused,
            the instance could not be reached, or the request failed without
            reaching a response.

    """
    issue_id = resolve_issue_id(client=client, owner=owner, repository=issue_repository, issue_number=issue_number)
    return _run_resolved_call(
        client=client,
        call=call,
        action=action,
        owner=owner,
        project_id=project_id,
        issue_number=issue_number,
        issue_id=issue_id,
        issue_repository=issue_repository,
    )


def _run_resolved_call(
    *,
    client: Gitea,
    call: Callable[[int], tuple[dict[str, Any], dict[str, Any]]],
    action: str,
    owner: str,
    project_id: int,
    issue_number: int,
    issue_id: int,
    issue_repository: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Make a project issue call whose issue has already been resolved.

    Args:
        client: The Gitea client to call, for the address its errors name.
        call: The API call, taking the resolved global issue ID.
        action: The verb describing the call, used in the error message.
        owner: The owner of the repository.
        project_id: The ID of the project.
        issue_number: The value the user passed as --issue-id.
        issue_id: The resolved global issue ID.
        issue_repository: The name of the repository holding the issue, or None
            when it is not known and `issue_number` is therefore a global ID.

    Returns:
        A tuple containing the payload and the metadata, the latter carrying the
        resolved global issue ID whenever the number was resolved.

    Raises:
        CommandError: If the call was refused, the instance could not be
            reached, or the request failed without reaching a response.

    """
    try:
        data, metadata = call(issue_id)
    except HTTPError as e:
        status_code = _status_code_of(e)
        message = _failure_message(
            _describe(status_code, e), action, owner, project_id, issue_number, issue_id, issue_repository
        )
        raise CommandError(message) from e
    except (RequestsConnectionError, Timeout) as e:
        # The call never reached the project, so the hints about the project
        # and the columns would only misdirect.
        raise CommandError(unreachable_message(e, client.base_url)) from e
    except RequestException as e:
        # The project was not reached either, but the instance may well be up:
        # nothing here says it was the connection that failed.
        raise CommandError(request_failed_message(e, client.base_url)) from e

    status_code = metadata.get("status_code", 0)
    if not _is_success(status_code):
        raise CommandError(
            _failure_message(
                _describe(status_code), action, owner, project_id, issue_number, issue_id, issue_repository
            )
        )
    if issue_repository is None:
        return data, metadata
    return data, {**metadata, "resolved_issue_id": issue_id}


def _failure_message(
    detail: str,
    action: str,
    owner: str,
    project_id: int,
    issue_number: int,
    issue_id: int,
    issue_repository: str | None,
) -> str:
    """Build the error message for a refused project issue call.

    Args:
        detail: The description of the failure.
        action: The verb describing the call.
        owner: The owner of the repository.
        project_id: The ID of the project.
        issue_number: The value the user passed as --issue-id.
        issue_id: The global issue ID the call was made with.
        issue_repository: The name of the repository holding the issue, if known.

    Returns:
        The message describing the failure and how to act on it.

    """
    if issue_repository is None:
        return (
            f"Could not {action} issue {issue_number} on project {project_id} of {owner}: {detail}. "
            f"--issue-id was read as a global issue ID, which is not the number shown in the web UI. "
            f"Pass --issue-repository REPOSITORY to give the number of that repository instead."
        )
    # The lookup succeeded, which is all that can be claimed: the issue may
    # have been closed, moved or deleted between the lookup and this call.
    return (
        f"Could not {action} issue #{issue_number} of {owner}/{issue_repository} (global ID {issue_id}) "
        f"on project {project_id}: {detail}. "
        f"The issue was found in {owner}/{issue_repository}, but the project call failed: check that the "
        f"issue is still there and on this project, and that --project-id and --column-id name a column of it."
    )


def _issue_label(owner: str, issue_number: int, issue_id: int, issue_repository: str | None) -> str:
    """Name the issue a message is about, as precisely as it was addressed.

    Args:
        owner: The owner of the repository.
        issue_number: The value the user passed as --issue-id.
        issue_id: The global issue ID the call was made with.
        issue_repository: The name of the repository holding the issue, if known.

    Returns:
        The phrase naming the issue.

    """
    if issue_repository is None:
        return f"issue {issue_id}"
    return f"issue #{issue_number} of {owner}/{issue_repository} (global ID {issue_id})"


def _not_on_board_message(
    owner: str,
    repository: str | None,
    project_id: int,
    column_id: int,
    issue_number: int,
    issue_id: int,
    issue_repository: str | None,
) -> str:
    """Build the error message for a move of an issue that has no card to move.

    Args:
        owner: The owner of the repository or organization holding the project.
        repository: The name of the repository holding the project, or None for
            an organization project.
        project_id: The ID of the project.
        column_id: The column the move was to.
        issue_number: The value the user passed as --issue-id.
        issue_id: The global issue ID the board was searched for.
        issue_repository: The name of the repository holding the issue, if known.

    Returns:
        The message describing the failure and how to act on it.

    """
    repository_option = f" --repository {repository}" if repository is not None else ""
    issue_repository_option = f" --issue-repository {issue_repository}" if issue_repository is not None else ""
    return (
        f"No column of project {project_id} holds {_issue_label(owner, issue_number, issue_id, issue_repository)}, "
        f"so there is no card to move. Gitea's move endpoint answers such a call with a success and does nothing, "
        f"which is why this is reported here rather than passed on. "
        f"Put the issue on the board with 'gitea-cli project issue add --owner {owner}{repository_option} "
        f"--project-id {project_id} --column-id {column_id} --issue-id {issue_number}{issue_repository_option}', "
        f"or pass --add-if-missing to have this command do that when there is no card yet."
    )


def _unreadable_board_message(
    detail: str,
    owner: str,
    repository: str | None,
    project_id: int,
    issue_number: int,
    issue_id: int,
    issue_repository: str | None,
) -> str:
    """Build the error message for a board whose columns could not be read.

    A move is only made once the card is known to exist, so a board that cannot
    be read stops the command: carrying on would be the silent no-op the check
    is there to prevent, and reporting the issue as not on the board would be a
    claim the failed lookup does not support.

    Args:
        detail: The description of the failure.
        owner: The owner of the repository or organization holding the project.
        repository: The name of the repository holding the project, or None for
            an organization project.
        project_id: The ID of the project.
        issue_number: The value the user passed as --issue-id.
        issue_id: The global issue ID the board was being searched for.
        issue_repository: The name of the repository holding the issue, if known.

    Returns:
        The message describing the failure and how to act on it.

    """
    where = f"{owner}/{repository}" if repository is not None else owner
    return (
        f"Could not tell which column of project {project_id} holds "
        f"{_issue_label(owner, issue_number, issue_id, issue_repository)}: {detail}. "
        f"The board's columns and their cards are listed to find the card before it is moved, because Gitea's move "
        f"endpoint reports success without doing anything when there is no card to move. "
        f"Check that --project-id names a project of {where} and that the account may read it; "
        f"run 'gitea-cli project list --owner {owner}' to see the projects in use."
    )


def _sorting_unavailable_message(
    owner: str,
    repository: str | None,
    project_id: int,
    column_id: int,
    issue_number: int,
) -> str:
    """Build the error message for a --sorting the add this move fell back to cannot carry.

    `--sorting` is a position among the cards already in a column, and the
    endpoint putting a card on a board takes no such parameter: the only way to
    honour both is to put the card there and then move it, which is the two
    commands the user can run. Saying so is the alternative to accepting the
    option and dropping it, which would place the card at whatever position the
    instance chose while reporting the request as carried out.

    Args:
        owner: The owner of the repository or organization holding the project.
        repository: The name of the repository holding the project, or None for
            an organization project.
        project_id: The ID of the project.
        column_id: The column the move was to.
        issue_number: The value the user passed as --issue-id.

    Returns:
        The message describing the failure and how to act on it.

    """
    repository_option = f" --repository {repository}" if repository is not None else ""
    return (
        f"--sorting cannot be applied while putting issue {issue_number} on project {project_id}: it positions a "
        f"card among the cards already in a column, and the endpoint that puts one on a board takes no position. "
        f"Run 'gitea-cli project issue add --owner {owner}{repository_option} --project-id {project_id} "
        f"--column-id {column_id} --issue-id {issue_number}' and then this command with --sorting, or drop "
        f"--sorting to have the card placed where the instance puts it."
    )


def _card_column_id(
    *,
    client: Gitea,
    owner: str,
    repository: str | None,
    project_id: int,
    issue_number: int,
    issue_id: int,
    issue_repository: str | None,
) -> int | None:
    """Find which column of a project holds an issue's card.

    Args:
        client: The Gitea client used for the lookups.
        owner: The owner of the repository or organization holding the project.
        repository: The name of the repository holding the project, or None for
            an organization project.
        project_id: The ID of the project.
        issue_number: The value the user passed as --issue-id.
        issue_id: The resolved global issue ID.
        issue_repository: The name of the repository holding the issue, if known.

    Returns:
        The ID of the column holding the card, or None when no column of the
        project holds one.

    Raises:
        CommandError: If the board could not be read, the instance could not be
            reached, or the request failed without reaching a response.

    """
    try:
        return find_card_column_id(
            client=client, owner=owner, repository=repository, project_id=project_id, issue_id=issue_id
        )
    except HTTPError as e:
        raise CommandError(
            _unreadable_board_message(
                _describe(_status_code_of(e), e),
                owner,
                repository,
                project_id,
                issue_number,
                issue_id,
                issue_repository,
            )
        ) from e
    except (RequestsConnectionError, Timeout) as e:
        raise CommandError(unreachable_message(e, client.base_url)) from e
    except RequestException as e:
        raise CommandError(request_failed_message(e, client.base_url)) from e


def run_project_issue_move(
    *,
    client: Gitea,
    owner: str,
    repository: str | None,
    project_id: int,
    issue_number: int,
    column_id: int,
    sorting: int | None,
    issue_repository: str | None,
    add_if_missing: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Move an issue's card to a column of a project, having first found the card.

    Gitea's move endpoint moves the row relating an issue to a project, and an
    issue that is not on the project has no such row: the endpoint answers the
    call with a success and an empty body, and moves nothing. A caller reading
    that as a move made is left believing a card is on a board that has none,
    which is what the board is walked here to prevent. The card is looked for
    first, and the move is made only once it has been found; when it has not,
    the command either says so or, with `add_if_missing`, puts the issue in the
    target column instead - which is what `project issue add` does, and the only
    way to get a card there in one call.

    Args:
        client: The Gitea client to call.
        owner: The owner of the repository or organization holding the project.
        repository: The name of the repository holding the project, or None for
            an organization project.
        project_id: The ID of the project.
        issue_number: The value the user passed as --issue-id.
        column_id: The target column ID.
        sorting: The position within the column, ascending.
        issue_repository: The name of the repository holding the issue, or None
            when it is not known and `issue_number` is therefore a global ID.
        add_if_missing: Whether to add the issue to the target column when no
            column of the project holds a card for it.

    Returns:
        A tuple containing the payload and the metadata, the latter carrying the
        resolved global issue ID whenever the number was resolved.

    Raises:
        CommandError: If the issue could not be resolved, the board could not be
            read, the issue has no card on the project and `add_if_missing` is
            not set, the call was refused, the instance could not be reached, or
            the request failed without reaching a response.

    """
    issue_id = resolve_issue_id(client=client, owner=owner, repository=issue_repository, issue_number=issue_number)
    on_board = (
        _card_column_id(
            client=client,
            owner=owner,
            repository=repository,
            project_id=project_id,
            issue_number=issue_number,
            issue_id=issue_id,
            issue_repository=issue_repository,
        )
        is not None
    )

    if not on_board and not add_if_missing:
        raise CommandError(
            _not_on_board_message(owner, repository, project_id, column_id, issue_number, issue_id, issue_repository)
        )

    if on_board:
        action = "move"

        def call(resolved_issue_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
            """Move the card the board was found to hold.

            Args:
                resolved_issue_id: The global ID of the issue.

            Returns:
                A tuple containing the response data and metadata.

            """
            return client.project.move_project_issue(
                owner=owner,
                repository=repository,
                project_id=project_id,
                issue_id=resolved_issue_id,
                column_id=column_id,
                sorting=sorting,
            )
    else:
        if sorting is not None:
            raise CommandError(_sorting_unavailable_message(owner, repository, project_id, column_id, issue_number))
        action = "add"

        def call(resolved_issue_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
            """Put the issue in the target column, there being no card to move.

            Args:
                resolved_issue_id: The global ID of the issue.

            Returns:
                A tuple containing the response data and metadata.

            """
            return client.project.add_issue_to_project_column(
                owner=owner,
                repository=repository,
                project_id=project_id,
                column_id=column_id,
                issue_id=resolved_issue_id,
            )

    return _run_resolved_call(
        client=client,
        call=call,
        action=action,
        owner=owner,
        project_id=project_id,
        issue_number=issue_number,
        issue_id=issue_id,
        issue_repository=issue_repository,
    )
