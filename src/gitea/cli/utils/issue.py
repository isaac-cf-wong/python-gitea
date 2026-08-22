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

The same walk answers a different question for `run_project_issue_remove`. The
removal endpoint takes the column the card is in, which is not a column the
caller is choosing but one the board already knows, so `--column-id` is optional
there and the walk supplies it - and an issue with no card is reported as having
none rather than removed from a column picked for it. This is what makes the
option mean two things across the commands: a destination for `add` and `move`,
the card's present whereabouts for `remove`.

Looking before the move is what makes the failure legible; reading the card back
afterwards is what makes the success true. The status code says only that the
request was accepted, so the move is followed by a listing of the target column,
and the command exits zero having seen the card there rather than having assumed
it. Neither half makes the pair atomic - Gitea has no conditional move, so a card
taken off the board between the two reads is still a card the command has
reported on - and the messages say which of "no card", "not where it was sent"
and "could not be confirmed" happened rather than collapsing them into one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from requests import ConnectionError as RequestsConnectionError
from requests import HTTPError, RequestException, Timeout

from gitea.cli.utils.errors import CommandError, request_failed_message, unreachable_message
from gitea.issue.project_column import column_holds_card, find_card_column_id

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


def _repository_option(repository: str | None) -> str:
    """Render the option naming the repository holding the board, for a suggested command.

    Args:
        repository: The name of the repository holding the project, or None for
            an organization project, which the option is absent for.

    Returns:
        The option, ready to append to a command line, or the empty string.

    """
    return f" --repository {repository}" if repository is not None else ""


def _add_command(
    owner: str,
    repository: str | None,
    project_id: int,
    column_id: int,
    issue_number: int,
    issue_repository: str | None,
) -> str:
    """Build the `project issue add` command line a message tells the user to run.

    Built in one place because two messages suggest it, and an option missing
    from one of them - the repository holding the board, or the one holding the
    issue, without which `--issue-id` is read as a global ID - is a command line
    that addresses something other than what the message just named.

    Args:
        owner: The owner of the repository or organization holding the project.
        repository: The name of the repository holding the project, or None for
            an organization project.
        project_id: The ID of the project.
        column_id: The column to add the issue to.
        issue_number: The value the user passed as --issue-id.
        issue_repository: The name of the repository holding the issue, if known.

    Returns:
        The command line, without a shell quoting of its own.

    """
    issue_repository_option = f" --issue-repository {issue_repository}" if issue_repository is not None else ""
    return (
        f"gitea-cli project issue add --owner {owner}{_repository_option(repository)} "
        f"--project-id {project_id} --column-id {column_id} --issue-id {issue_number}{issue_repository_option}"
    )


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
    return (
        f"No column of project {project_id} holds {_issue_label(owner, issue_number, issue_id, issue_repository)}, "
        f"so there is no card to move. Gitea's move endpoint answers such a call with a success and does nothing, "
        f"which is why this is reported here rather than passed on. "
        f"Put the issue on the board with "
        f"'{_add_command(owner, repository, project_id, column_id, issue_number, issue_repository)}', "
        f"or pass --add-if-missing to have this command do that when there is no card yet."
    )


# Why each command walks the board, for the message reporting a board it could
# not walk. The move reads it to keep a call it cannot see the failure of from
# being made; the remove reads it because the column is what the removal takes
# and the caller did not name one.
_BOARD_WALK_REASONS = {
    "move": (
        "The board's columns and their cards are listed to find the card before it is moved, because Gitea's move "
        "endpoint reports success without doing anything when there is no card to move."
    ),
    "remove": (
        "The board's columns and their cards are listed because --column-id was not passed: a removal takes the "
        "column holding the card, and this command looks that up rather than asking for it."
    ),
}


def _nothing_to_remove_message(
    owner: str,
    repository: str | None,
    project_id: int,
    issue_number: int,
    issue_id: int,
    issue_repository: str | None,
) -> str:
    """Build the error message for a remove whose issue has no card to remove.

    Reported only for a removal that was not given a column: one that was is
    passed on to Gitea as the caller wrote it, so this says the board was walked
    and had nothing on it for the issue, which is the one thing the walk can
    conclude.

    Args:
        owner: The owner of the repository or organization holding the project.
        repository: The name of the repository holding the project, or None for
            an organization project.
        project_id: The ID of the project.
        issue_number: The value the user passed as --issue-id.
        issue_id: The global issue ID the board was searched for.
        issue_repository: The name of the repository holding the issue, if known.

    Returns:
        The message describing the failure and how to act on it.

    """
    return (
        f"No column of project {project_id} holds {_issue_label(owner, issue_number, issue_id, issue_repository)}, "
        f"so there is no card to remove. --column-id was not passed, so the column holding the card was looked for "
        f"on the board and no column of it lists the issue: the issue is not on this project, or its card is "
        f"already off it. "
        f"See what the board holds with 'gitea-cli project issues --owner {owner}"
        f"{_repository_option(repository)} --project-id {project_id}'."
    )


def _unreadable_board_message(
    detail: str,
    action: str,
    owner: str,
    repository: str | None,
    project_id: int,
    issue_number: int,
    issue_id: int,
    issue_repository: str | None,
) -> str:
    """Build the error message for a board whose columns could not be read.

    The call is only made once the card is known to exist, so a board that cannot
    be read stops the command: carrying on would be the silent no-op the check
    is there to prevent, and reporting the issue as not on the board would be a
    claim the failed lookup does not support.

    Args:
        detail: The description of the failure.
        action: The verb describing the call the board was being read for, which
            selects the sentence saying why it was read.
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
        f"{_BOARD_WALK_REASONS[action]} "
        f"Check that --project-id names a project of {where} and that the account may read it; "
        f"run 'gitea-cli project list --owner {owner}{_repository_option(repository)}' to see the projects in use."
    )


def _sorting_unavailable_message(
    owner: str,
    repository: str | None,
    project_id: int,
    column_id: int,
    issue_number: int,
    issue_id: int,
    issue_repository: str | None,
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
        issue_id: The global issue ID the board was searched for.
        issue_repository: The name of the repository holding the issue, if known.

    Returns:
        The message describing the failure and how to act on it.

    """
    return (
        f"--sorting cannot be applied while putting "
        f"{_issue_label(owner, issue_number, issue_id, issue_repository)} on project {project_id}: it positions a "
        f"card among the cards already in a column, and the endpoint that puts one on a board takes no position. "
        f"Run '{_add_command(owner, repository, project_id, column_id, issue_number, issue_repository)}' and then "
        f"this command with --sorting, or drop --sorting to have the card placed where the instance puts it."
    )


def _card_column_id(
    *,
    client: Gitea,
    action: str,
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
        action: The verb describing the call the card is being looked for, for
            the message reporting a board that could not be read.
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
                action,
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


def _card_absent_message(
    action: str,
    owner: str,
    repository: str | None,
    project_id: int,
    column_id: int,
    issue_number: int,
    issue_id: int,
    issue_repository: str | None,
) -> str:
    """Build the error message for a call that reported success and left no card behind.

    Args:
        action: The verb describing the call that was made.
        owner: The owner of the repository or organization holding the project.
        repository: The name of the repository holding the project, or None for
            an organization project.
        project_id: The ID of the project.
        column_id: The column the card was sent to.
        issue_number: The value the user passed as --issue-id.
        issue_id: The global issue ID the call was made with.
        issue_repository: The name of the repository holding the issue, if known.

    Returns:
        The message describing the failure and how to act on it.

    """
    return (
        f"Gitea reported the {action} of {_issue_label(owner, issue_number, issue_id, issue_repository)} on project "
        f"{project_id} as a success, but column {column_id} holds no card for it afterwards, so the card is not "
        f"where it was sent. A success that changed nothing is what this endpoint answers with when there was "
        f"nothing for it to do: --column-id may name a column of another project, or the card may have been taken "
        f"off the board while the command ran. "
        f"Check the board's columns with 'gitea-cli project column list --owner {owner}"
        f"{_repository_option(repository)} --project-id {project_id}'."
    )


def _unconfirmed_card_message(
    detail: str,
    action: str,
    owner: str,
    repository: str | None,
    project_id: int,
    column_id: int,
    issue_number: int,
    issue_id: int,
    issue_repository: str | None,
) -> str:
    """Build the error message for a call that was made and could not then be confirmed.

    The call is reported as unconfirmed rather than as failed, because it was
    made and answered: what is not known is whether it did anything. Saying it
    failed would be as wrong as the success this check exists to distrust, in the
    other direction, so the message says which of the two is unknown and names
    the command that settles it.

    Args:
        detail: The description of the failure of the confirming lookup.
        action: The verb describing the call that was made.
        owner: The owner of the repository or organization holding the project.
        repository: The name of the repository holding the project, or None for
            an organization project.
        project_id: The ID of the project.
        column_id: The column the card was sent to.
        issue_number: The value the user passed as --issue-id.
        issue_id: The global issue ID the call was made with.
        issue_repository: The name of the repository holding the issue, if known.

    Returns:
        The message describing the failure and how to act on it.

    """
    return (
        f"The {action} of {_issue_label(owner, issue_number, issue_id, issue_repository)} on project {project_id} "
        f"was made and reported success, but the card could not then be confirmed in column {column_id}: {detail}. "
        f"Whether the card is there is therefore unknown, not known to be wrong. "
        f"Read the column with 'gitea-cli project column issues --owner {owner}{_repository_option(repository)} "
        f"--project-id {project_id} --column-id {column_id}' before repeating the command."
    )


def _confirm_card_in_column(
    *,
    client: Gitea,
    action: str,
    owner: str,
    repository: str | None,
    project_id: int,
    column_id: int,
    issue_number: int,
    issue_id: int,
    issue_repository: str | None,
) -> None:
    """Confirm the card reached the column it was sent to.

    The status code of the call is not evidence that it did anything: this
    endpoint answers a move it had nothing to move with a success, which is the
    whole reason the commands here look before they leap. Looking afterwards is
    the other half of it, and the stronger half - it is the card's position that
    was asked for, and reading it back is the only thing that establishes it.
    Between them, a command that exits zero has had the card's presence in the
    target column confirmed rather than inferred.

    What this cannot do is make the call and the confirmation one operation.
    Gitea offers no conditional move, so a card taken off the board after the
    confirming read is a card the command has already reported on; the window is
    narrowed to that read, not closed. Nothing here pretends otherwise.

    Args:
        client: The Gitea client used for the lookup.
        action: The verb describing the call that was made.
        owner: The owner of the repository or organization holding the project.
        repository: The name of the repository holding the project, or None for
            an organization project.
        project_id: The ID of the project.
        column_id: The column the card was sent to.
        issue_number: The value the user passed as --issue-id.
        issue_id: The global issue ID the call was made with.
        issue_repository: The name of the repository holding the issue, if known.

    Raises:
        CommandError: If the column holds no card for the issue, or if the
            lookup that would have confirmed one could not be made.

    """
    try:
        landed = column_holds_card(
            client=client,
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
            issue_id=issue_id,
        )
    except HTTPError as e:
        detail = _describe(_status_code_of(e), e)
        raise CommandError(
            _unconfirmed_card_message(
                detail, action, owner, repository, project_id, column_id, issue_number, issue_id, issue_repository
            )
        ) from e
    except (RequestsConnectionError, Timeout) as e:
        raise CommandError(
            _unconfirmed_card_message(
                f"the instance at {client.base_url} could not be reached ({e})",
                action,
                owner,
                repository,
                project_id,
                column_id,
                issue_number,
                issue_id,
                issue_repository,
            )
        ) from e
    except RequestException as e:
        raise CommandError(
            _unconfirmed_card_message(
                f"the request did not complete ({type(e).__name__}: {e})",
                action,
                owner,
                repository,
                project_id,
                column_id,
                issue_number,
                issue_id,
                issue_repository,
            )
        ) from e

    if not landed:
        raise CommandError(
            _card_absent_message(
                action, owner, repository, project_id, column_id, issue_number, issue_id, issue_repository
            )
        )


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
    """Move an issue's card to a column of a project, and confirm it arrived.

    Gitea's move endpoint moves the row relating an issue to a project, and an
    issue that is not on the project has no such row: the endpoint answers the
    call with a success and an empty body, and moves nothing. A caller reading
    that as a move made is left believing a card is on a board that has none,
    which is what the board is walked here to prevent. The card is looked for
    first, and the move is made only once it has been found; when it has not,
    the command either says so or, with `add_if_missing`, puts the issue in the
    target column instead - which is what `project issue add` does, and the only
    way to get a card there in one call.

    Whichever call was made, the target column is then read back, because the
    success it answered with is the thing this endpoint has already been shown
    not to mean. Returning normally therefore says the card was seen in
    `column_id`, not that Gitea accepted a request to put it there. It does not
    say the card is still there: the two reads are separate requests, and no
    conditional move exists to make them one.

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
            not set, the call was refused, the card is not in `column_id`
            afterwards or could not be confirmed there, the instance could not be
            reached, or the request failed without reaching a response.

    """
    issue_id = resolve_issue_id(client=client, owner=owner, repository=issue_repository, issue_number=issue_number)
    on_board = (
        _card_column_id(
            client=client,
            action="move",
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
            raise CommandError(
                _sorting_unavailable_message(
                    owner, repository, project_id, column_id, issue_number, issue_id, issue_repository
                )
            )
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

    data, metadata = _run_resolved_call(
        client=client,
        call=call,
        action=action,
        owner=owner,
        project_id=project_id,
        issue_number=issue_number,
        issue_id=issue_id,
        issue_repository=issue_repository,
    )
    _confirm_card_in_column(
        client=client,
        action=action,
        owner=owner,
        repository=repository,
        project_id=project_id,
        column_id=column_id,
        issue_number=issue_number,
        issue_id=issue_id,
        issue_repository=issue_repository,
    )
    return data, metadata


def run_project_issue_remove(
    *,
    client: Gitea,
    owner: str,
    repository: str | None,
    project_id: int,
    issue_number: int,
    column_id: int | None,
    issue_repository: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Take an issue's card off a project, from the column it is in.

    Gitea's removal endpoint takes the column the card is in, not a column the
    caller is choosing: unlike the `--column-id` of `add` and `move`, which says
    where the card is to end up, this one says where it already is. That is
    something the board can be asked, so `column_id` may be None, and the column
    holding the card is then found by walking the project's columns - the same
    walk the move makes before moving a card. An issue with no card on the
    project is reported as having none, rather than removed from a column chosen
    for it.

    A `column_id` that was given is passed on as it stands. Nothing is looked up
    for it, and no claim is made that the card was there: this is a removal the
    caller addressed, and Gitea answers one naming the wrong column with a
    success, so the column it was told to use is the column it uses.

    Args:
        client: The Gitea client to call.
        owner: The owner of the repository or organization holding the project.
        repository: The name of the repository holding the project, or None for
            an organization project.
        project_id: The ID of the project.
        issue_number: The value the user passed as --issue-id.
        column_id: The column holding the card, or None to find it on the board.
        issue_repository: The name of the repository holding the issue, or None
            when it is not known and `issue_number` is therefore a global ID.

    Returns:
        A tuple containing the payload and the metadata, the latter carrying the
        resolved global issue ID whenever the number was resolved, and the column
        the card was removed from whenever that was looked up.

    Raises:
        CommandError: If the issue could not be resolved, the board could not be
            read, the issue has no card on the project, the call was refused, the
            instance could not be reached, or the request failed without reaching
            a response.

    """
    issue_id = resolve_issue_id(client=client, owner=owner, repository=issue_repository, issue_number=issue_number)
    carded_column_id = column_id
    if carded_column_id is None:
        carded_column_id = _card_column_id(
            client=client,
            action="remove",
            owner=owner,
            repository=repository,
            project_id=project_id,
            issue_number=issue_number,
            issue_id=issue_id,
            issue_repository=issue_repository,
        )
        if carded_column_id is None:
            raise CommandError(
                _nothing_to_remove_message(owner, repository, project_id, issue_number, issue_id, issue_repository)
            )

    def call(resolved_issue_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
        """Take the card off the column holding it.

        Args:
            resolved_issue_id: The global ID of the issue.

        Returns:
            A tuple containing the response data and metadata.

        """
        return client.project.remove_issue_from_project_column(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=carded_column_id,
            issue_id=resolved_issue_id,
        )

    data, metadata = _run_resolved_call(
        client=client,
        call=call,
        action="remove",
        owner=owner,
        project_id=project_id,
        issue_number=issue_number,
        issue_id=issue_id,
        issue_repository=issue_repository,
    )
    if column_id is None:
        # The column was this command's answer rather than the caller's, so it is
        # reported: a removal that says nothing about where the card was leaves
        # the caller unable to put it back.
        return data, {**metadata, "resolved_column_id": carded_column_id}
    return data, metadata
