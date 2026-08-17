"""Unit tests for the project issue CLI helpers."""

from unittest.mock import MagicMock

import pytest
from requests import HTTPError

from gitea.cli.utils.errors import CommandError
from gitea.cli.utils.issue import resolve_issue_id, run_project_issue_call


def make_client(get_issue_result=None, get_issue_error=None):
    """Create a mock client whose issue lookup returns or raises the given result.

    Args:
        get_issue_result: The tuple `get_issue` should return, if any.
        get_issue_error: The exception `get_issue` should raise, if any.

    Returns:
        The mock client.

    """
    client = MagicMock()
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

    resolved = resolve_issue_id(client=client, owner="management", repository="weave-workspace", issue_number=15)

    assert resolved == 1854
    client.issue.get_issue.assert_called_once_with(owner="management", repository="weave-workspace", index=15)


def test_resolve_issue_id_without_repository_passes_the_value_through():
    """Should treat the value as a global ID and skip the lookup for organization projects."""
    client = make_client()

    resolved = resolve_issue_id(client=client, owner="management", repository=None, issue_number=1854)

    assert resolved == 1854
    client.issue.get_issue.assert_not_called()


def test_resolve_issue_id_unknown_number_raises_actionable_error():
    """Should name the repository, the number and how to find the right one."""
    client = make_client(get_issue_error=http_error(404))

    with pytest.raises(CommandError) as exc_info:
        resolve_issue_id(client=client, owner="management", repository="weave-workspace", issue_number=9999)

    message = str(exc_info.value)
    assert "#9999" in message
    assert "management/weave-workspace" in message
    assert "HTTP 404" in message
    assert "gitea-cli issue list --owner management --repository weave-workspace" in message


def test_resolve_issue_id_refused_lookup_reports_the_status():
    """Should not blame the issue number when the lookup itself was refused."""
    client = make_client(get_issue_error=http_error(403))

    with pytest.raises(CommandError) as exc_info:
        resolve_issue_id(client=client, owner="management", repository="weave-workspace", issue_number=15)

    message = str(exc_info.value)
    assert "Could not look up issue #15 in management/weave-workspace" in message
    assert "HTTP 403" in message


def test_resolve_issue_id_error_without_response_reports_the_error():
    """Should fall back to the error text when the failure carries no response."""
    client = make_client(get_issue_error=HTTPError("connection reset"))

    with pytest.raises(CommandError, match="connection reset"):
        resolve_issue_id(client=client, owner="management", repository="weave-workspace", issue_number=15)


def test_resolve_issue_id_unsuccessful_status_raises():
    """Should reject a lookup that reports a non-success status instead of raising."""
    client = make_client(({}, {"status_code": 404}))

    with pytest.raises(CommandError, match="#15"):
        resolve_issue_id(client=client, owner="management", repository="weave-workspace", issue_number=15)


def test_resolve_issue_id_payload_without_id_raises():
    """Should reject a successful response that carries no usable ID."""
    client = make_client(({"number": 15}, {"status_code": 200}))

    with pytest.raises(CommandError, match="#15"):
        resolve_issue_id(client=client, owner="management", repository="weave-workspace", issue_number=15)


def test_resolve_issue_id_non_dict_payload_raises():
    """Should reject a response whose payload is not an issue object."""
    client = make_client(([], {"status_code": 200}))

    with pytest.raises(CommandError, match="#15"):
        resolve_issue_id(client=client, owner="management", repository="weave-workspace", issue_number=15)


@pytest.mark.parametrize("status_code", [200, 201, 204, 299])
def test_run_project_issue_call_records_the_resolved_id(status_code):
    """Should call with the resolved ID and report it in the metadata."""
    client = make_client(({"id": 1854, "number": 15}, {"status_code": 200}))
    call = MagicMock(return_value=({}, {"status_code": status_code}))

    data, metadata = run_project_issue_call(
        client=client,
        call=call,
        action="move",
        owner="management",
        project_id=5,
        issue_number=15,
        issue_repository="weave-workspace",
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
        owner="management",
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
            owner="management",
            project_id=5,
            issue_number=9999,
            issue_repository="weave-workspace",
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
            owner="management",
            project_id=5,
            issue_number=15,
            issue_repository="weave-workspace",
        )

    message = str(exc_info.value)
    assert "move issue #15 of management/weave-workspace" in message
    assert "global ID 1854" in message
    assert "project 5" in message
    assert "HTTP 404" in message


def test_run_project_issue_call_organization_failure_explains_the_global_id():
    """Should say the value was read as a global ID and how to use the number instead."""
    client = make_client()
    call = MagicMock(side_effect=http_error(404))

    with pytest.raises(CommandError) as exc_info:
        run_project_issue_call(
            client=client,
            call=call,
            action="add",
            owner="management",
            project_id=5,
            issue_number=15,
            issue_repository=None,
        )

    message = str(exc_info.value)
    assert "add issue 15 on project 5 of management" in message
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
            owner="management",
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
            owner="management",
            project_id=5,
            issue_number=15,
            issue_repository="weave-workspace",
        )
