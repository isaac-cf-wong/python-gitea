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
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from requests import HTTPError, RequestException

from gitea.cli.utils.errors import CommandError, unreachable_message

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
            lookup was refused, or the instance could not be reached.

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
    except RequestException as e:
        # No response came back, so nothing is known about the issue itself.
        raise CommandError(unreachable_message(e, client.base_url)) from e

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
            or the instance could not be reached.

    """
    issue_id = resolve_issue_id(client=client, owner=owner, repository=issue_repository, issue_number=issue_number)

    try:
        data, metadata = call(issue_id)
    except HTTPError as e:
        status_code = _status_code_of(e)
        message = _failure_message(
            _describe(status_code, e), action, owner, project_id, issue_number, issue_id, issue_repository
        )
        raise CommandError(message) from e
    except RequestException as e:
        # The call never reached the project, so the hints about the project
        # and the columns would only misdirect.
        raise CommandError(unreachable_message(e, client.base_url)) from e

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
