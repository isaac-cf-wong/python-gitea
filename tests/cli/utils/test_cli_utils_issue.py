"""Unit tests for the project issue CLI helpers."""

from unittest.mock import MagicMock

import pytest
from requests import ConnectionError as RequestsConnectionError
from requests import ConnectTimeout, HTTPError, ReadTimeout, Timeout
from requests.exceptions import ChunkedEncodingError, InvalidURL, MissingSchema

from gitea.cli.utils.errors import CommandError
from gitea.cli.utils.issue import resolve_issue_id, run_project_issue_call

BASE_URL = "https://gitea.example.com"


def make_client(get_issue_result=None, get_issue_error=None):
    """Create a mock client whose issue lookup returns or raises the given result.

    Args:
        get_issue_result: The tuple `get_issue` should return, if any.
        get_issue_error: The exception `get_issue` should raise, if any.

    Returns:
        The mock client.

    """
    client = MagicMock()
    client.base_url = BASE_URL
    if get_issue_result is not None:
        client.issue.get_issue.return_value = get_issue_result
    if get_issue_error is not None:
        client.issue.get_issue.side_effect = get_issue_error
    return client


def http_error(status_code):
    """Create the error the client raises for an unsuccessful response.

    Args:
        status_code: The status code the response carries.

    Returns:
        The HTTP error.

    """
    response = MagicMock()
    response.status_code = status_code
    return HTTPError(f"{status_code} Client Error", response=response)


def test_resolve_issue_id_maps_number_to_global_id():
    """Should look the number up in the repository and return the global ID."""
    client = make_client(({"id": 1854, "number": 15}, {"status_code": 200}))

    resolved = resolve_issue_id(client=client, owner="example-org", repository="example-repo", issue_number=15)

    assert resolved == 1854
    client.issue.get_issue.assert_called_once_with(owner="example-org", repository="example-repo", index=15)


def test_resolve_issue_id_without_repository_passes_the_value_through():
    """Should treat the value as a global ID and skip the lookup for organization projects."""
    client = make_client()

    resolved = resolve_issue_id(client=client, owner="example-org", repository=None, issue_number=1854)

    assert resolved == 1854
    client.issue.get_issue.assert_not_called()


def test_resolve_issue_id_unknown_number_raises_actionable_error():
    """Should name the repository, the number and how to find the right one."""
    client = make_client(get_issue_error=http_error(404))

    with pytest.raises(CommandError) as exc_info:
        resolve_issue_id(client=client, owner="example-org", repository="example-repo", issue_number=9999)

    message = str(exc_info.value)
    assert "#9999" in message
    assert "example-org/example-repo" in message
    assert "HTTP 404" in message
    assert "gitea-cli issue list --owner example-org --repository example-repo" in message


def test_resolve_issue_id_refused_lookup_reports_the_status():
    """Should not blame the issue number when the lookup itself was refused."""
    client = make_client(get_issue_error=http_error(403))

    with pytest.raises(CommandError) as exc_info:
        resolve_issue_id(client=client, owner="example-org", repository="example-repo", issue_number=15)

    message = str(exc_info.value)
    assert "Could not look up issue #15 in example-org/example-repo" in message
    assert "HTTP 403" in message


def test_resolve_issue_id_error_without_response_reports_the_error():
    """Should fall back to the error text when the failure carries no response."""
    client = make_client(get_issue_error=HTTPError("connection reset"))

    with pytest.raises(CommandError, match="connection reset"):
        resolve_issue_id(client=client, owner="example-org", repository="example-repo", issue_number=15)


def test_resolve_issue_id_unsuccessful_status_raises():
    """Should reject a lookup that reports a non-success status instead of raising."""
    client = make_client(({}, {"status_code": 404}))

    with pytest.raises(CommandError, match="#15"):
        resolve_issue_id(client=client, owner="example-org", repository="example-repo", issue_number=15)


def test_resolve_issue_id_payload_without_id_raises():
    """Should reject a successful response that carries no usable ID."""
    client = make_client(({"number": 15}, {"status_code": 200}))

    with pytest.raises(CommandError, match="#15"):
        resolve_issue_id(client=client, owner="example-org", repository="example-repo", issue_number=15)


def test_resolve_issue_id_non_dict_payload_raises():
    """Should reject a response whose payload is not an issue object."""
    client = make_client(([], {"status_code": 200}))

    with pytest.raises(CommandError, match="#15"):
        resolve_issue_id(client=client, owner="example-org", repository="example-repo", issue_number=15)


@pytest.mark.parametrize(
    "error",
    [
        RequestsConnectionError("Failed to establish a new connection: [Errno 111] Connection refused"),
        Timeout("Read timed out. (read timeout=10)"),
        ConnectTimeout("Connection to gitea.example.com timed out. (connect timeout=10)"),
        ReadTimeout("HTTPSConnectionPool(host='gitea.example.com', port=443): Read timed out."),
    ],
    ids=["connection", "timeout", "connect-timeout", "read-timeout"],
)
def test_resolve_issue_id_unreachable_instance_names_the_base_url(error):
    """Should blame the instance, not the issue number, when no response came back."""
    client = make_client(get_issue_error=error)

    with pytest.raises(CommandError) as exc_info:
        resolve_issue_id(client=client, owner="example-org", repository="example-repo", issue_number=15)

    message = str(exc_info.value)
    assert f"Could not reach the Gitea API at {BASE_URL}" in message
    assert str(error) in message
    # Nothing was learnt about the issue, so the message must not send the user
    # looking for a number that may well be right.
    assert "No issue #15" not in message
    assert "issue list" not in message


@pytest.mark.parametrize(
    "error",
    [
        InvalidURL("Failed to parse: gitea.example.com:3000"),
        MissingSchema("Invalid URL 'gitea.example.com': No scheme supplied."),
        ChunkedEncodingError("Connection broken: IncompleteRead(9 bytes read)"),
    ],
    ids=["invalid-url", "missing-schema", "broken-body"],
)
def test_resolve_issue_id_request_failure_is_not_called_unreachable(error):
    """Should blame the request, not the instance, when the failure is not a connection one.

    A malformed base URL and a response that could not be read are
    `RequestException`s as well, but neither says the instance is down, so
    neither may be reported as one. Both must still be reported as a message
    rather than raised on for a traceback.
    """
    client = make_client(get_issue_error=error)

    with pytest.raises(CommandError) as exc_info:
        resolve_issue_id(client=client, owner="example-org", repository="example-repo", issue_number=15)

    message = str(exc_info.value)
    assert f"Could not complete the request to the Gitea API at {BASE_URL}" in message
    assert type(error).__name__ in message
    assert str(error) in message
    assert "Could not reach the Gitea API" not in message


@pytest.mark.parametrize(
    "error",
    [
        InvalidURL("Failed to parse: gitea.example.com:3000"),
        ChunkedEncodingError("Connection broken: IncompleteRead(9 bytes read)"),
    ],
    ids=["invalid-url", "broken-body"],
)
def test_run_project_issue_call_request_failure_is_not_called_unreachable(error):
    """Should report a non-connection request failure as such, not as an unreachable instance."""
    client = make_client(({"id": 1854, "number": 15}, {"status_code": 200}))
    call = MagicMock(side_effect=error)

    with pytest.raises(CommandError) as exc_info:
        run_project_issue_call(
            client=client,
            call=call,
            action="move",
            owner="example-org",
            project_id=5,
            issue_number=15,
            issue_repository="example-repo",
        )

    message = str(exc_info.value)
    assert f"Could not complete the request to the Gitea API at {BASE_URL}" in message
    assert type(error).__name__ in message
    assert "Could not reach the Gitea API" not in message
    # The call never reached the project, so the column hints would misdirect.
    assert "--column-id" not in message


@pytest.mark.parametrize(
    "error",
    [
        RequestsConnectionError("Failed to establish a new connection: [Errno 111] Connection refused"),
        Timeout("Read timed out. (read timeout=10)"),
        ConnectTimeout("Connection to gitea.example.com timed out. (connect timeout=10)"),
        ReadTimeout("HTTPSConnectionPool(host='gitea.example.com', port=443): Read timed out."),
    ],
    ids=["connection", "timeout", "connect-timeout", "read-timeout"],
)
def test_run_project_issue_call_unreachable_instance_names_the_base_url(error):
    """Should report an unreachable instance rather than blaming the project."""
    client = make_client(({"id": 1854, "number": 15}, {"status_code": 200}))
    call = MagicMock(side_effect=error)

    with pytest.raises(CommandError) as exc_info:
        run_project_issue_call(
            client=client,
            call=call,
            action="move",
            owner="example-org",
            project_id=5,
            issue_number=15,
            issue_repository="example-repo",
        )

    message = str(exc_info.value)
    assert f"Could not reach the Gitea API at {BASE_URL}" in message
    # The call never reached the project, so the column hints would misdirect.
    assert "--column-id" not in message


@pytest.mark.parametrize("status_code", [200, 201, 204, 299])
def test_run_project_issue_call_records_the_resolved_id(status_code):
    """Should call with the resolved ID and report it in the metadata."""
    client = make_client(({"id": 1854, "number": 15}, {"status_code": 200}))
    call = MagicMock(return_value=({}, {"status_code": status_code}))

    data, metadata = run_project_issue_call(
        client=client,
        call=call,
        action="move",
        owner="example-org",
        project_id=5,
        issue_number=15,
        issue_repository="example-repo",
    )

    call.assert_called_once_with(1854)
    assert data == {}
    assert metadata == {"status_code": status_code, "resolved_issue_id": 1854}


def test_run_project_issue_call_organization_project_passes_the_id_through():
    """Should call with the value as given and add nothing to the metadata."""
    client = make_client()
    call = MagicMock(return_value=({}, {"status_code": 204}))

    _, metadata = run_project_issue_call(
        client=client,
        call=call,
        action="move",
        owner="example-org",
        project_id=5,
        issue_number=1854,
        issue_repository=None,
    )

    call.assert_called_once_with(1854)
    client.issue.get_issue.assert_not_called()
    assert metadata == {"status_code": 204}


def test_run_project_issue_call_does_not_call_when_the_issue_is_unknown():
    """Should fail during resolution, before touching the project."""
    client = make_client(get_issue_error=http_error(404))
    call = MagicMock()

    with pytest.raises(CommandError, match="No issue #9999"):
        run_project_issue_call(
            client=client,
            call=call,
            action="move",
            owner="example-org",
            project_id=5,
            issue_number=9999,
            issue_repository="example-repo",
        )

    call.assert_not_called()


def test_run_project_issue_call_repository_failure_mentions_both_ids():
    """Should report the number the user typed, the global ID and what to check."""
    client = make_client(({"id": 1854, "number": 15}, {"status_code": 200}))
    call = MagicMock(side_effect=http_error(404))

    with pytest.raises(CommandError) as exc_info:
        run_project_issue_call(
            client=client,
            call=call,
            action="move",
            owner="example-org",
            project_id=5,
            issue_number=15,
            issue_repository="example-repo",
        )

    message = str(exc_info.value)
    assert "move issue #15 of example-org/example-repo" in message
    assert "global ID 1854" in message
    assert "project 5" in message
    assert "HTTP 404" in message


def test_run_project_issue_call_repository_failure_claims_only_the_lookup():
    """Should report what the lookup found, not that the issue exists now.

    The issue can be deleted between the lookup and the project call, so a
    present-tense claim that it exists is not something the CLI can know.
    """
    client = make_client(({"id": 1854, "number": 15}, {"status_code": 200}))
    call = MagicMock(side_effect=http_error(404))

    with pytest.raises(CommandError) as exc_info:
        run_project_issue_call(
            client=client,
            call=call,
            action="move",
            owner="example-org",
            project_id=5,
            issue_number=15,
            issue_repository="example-repo",
        )

    message = str(exc_info.value)
    assert "The issue exists" not in message
    assert "was found in example-org/example-repo, but the project call failed" in message
    assert "--project-id and --column-id name a column of it" in message


def test_run_project_issue_call_organization_failure_explains_the_global_id():
    """Should say the value was read as a global ID and how to use the number instead."""
    client = make_client()
    call = MagicMock(side_effect=http_error(404))

    with pytest.raises(CommandError) as exc_info:
        run_project_issue_call(
            client=client,
            call=call,
            action="add",
            owner="example-org",
            project_id=5,
            issue_number=15,
            issue_repository=None,
        )

    message = str(exc_info.value)
    assert "add issue 15 on project 5 of example-org" in message
    assert "global issue ID" in message
    assert "--issue-repository REPOSITORY" in message


def test_run_project_issue_call_unsuccessful_status_raises():
    """Should reject a call that reports a non-success status instead of raising."""
    client = make_client()
    call = MagicMock(return_value=({}, {"status_code": 404}))

    with pytest.raises(CommandError, match="HTTP 404"):
        run_project_issue_call(
            client=client,
            call=call,
            action="remove",
            owner="example-org",
            project_id=5,
            issue_number=1854,
            issue_repository=None,
        )


def test_run_project_issue_call_missing_status_code_fails_closed():
    """Should treat a metadata dict without a status code as a failure."""
    client = make_client(({"id": 1854, "number": 15}, {"status_code": 200}))
    call = MagicMock(return_value=({}, {}))

    with pytest.raises(CommandError, match="HTTP 0"):
        run_project_issue_call(
            client=client,
            call=call,
            action="remove",
            owner="example-org",
            project_id=5,
            issue_number=15,
            issue_repository="example-repo",
        )
