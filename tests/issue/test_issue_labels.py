"""Unit tests for the methods acting on the labels of an issue.

The requests are answered at the session the real client builds, so the method,
the path and the body each method sends are what is asserted: adding and
replacing send the same body to the same endpoint and differ only in the method,
and a method sent as the other one strips an issue's labels or fails to.
"""

from unittest.mock import patch

import pytest

from gitea.client.async_gitea import AsyncGitea
from gitea.client.gitea import Gitea
from tests.transport import NO_CONTENT, AsyncRecordingSession, RecordingSession

BASE_URL = "https://gitea.invalid"
LABELS_URL = f"{BASE_URL}/api/v1/repos/o/r/issues/34/labels"
BUG = {"id": 3, "name": "bug"}


def test_list_issue_labels_gets_the_issue_labels():
    """Listing should GET the issue's labels endpoint and return what it answers."""
    session = RecordingSession([BUG])
    with patch("gitea.client.gitea.requests.Session", return_value=session), Gitea(base_url=BASE_URL) as client:
        result = client.issue.list_issue_labels(owner="o", repository="r", index=34)

    assert session.requests == [("GET", LABELS_URL)]
    assert result == ([BUG], {"status_code": 200})


def test_add_issue_labels_posts_so_that_existing_labels_are_kept():
    """Adding should POST, which Gitea appends, never PUT, which it replaces."""
    session = RecordingSession([BUG, {"id": 5, "name": "docs"}])
    with patch("gitea.client.gitea.requests.Session", return_value=session), Gitea(base_url=BASE_URL) as client:
        result = client.issue.add_issue_labels(owner="o", repository="r", index=34, labels=[5])

    assert session.requests == [("POST", LABELS_URL)]
    assert session.bodies == [{"labels": [5]}]
    assert result == ([BUG, {"id": 5, "name": "docs"}], {"status_code": 200})


def test_replace_issue_labels_puts():
    """Replacing should PUT the labels the issue is to be left with."""
    session = RecordingSession([BUG])
    with patch("gitea.client.gitea.requests.Session", return_value=session), Gitea(base_url=BASE_URL) as client:
        result = client.issue.replace_issue_labels(owner="o", repository="r", index=34, labels=[3, "docs"])

    assert session.requests == [("PUT", LABELS_URL)]
    assert session.bodies == [{"labels": [3, "docs"]}]
    assert result == ([BUG], {"status_code": 200})


def test_remove_issue_label_deletes_that_label_only():
    """Removing one label should DELETE its own path, not the whole label list."""
    session = RecordingSession(NO_CONTENT)
    with patch("gitea.client.gitea.requests.Session", return_value=session), Gitea(base_url=BASE_URL) as client:
        result = client.issue.remove_issue_label(owner="o", repository="r", index=34, label=3)

    assert session.requests == [("DELETE", f"{LABELS_URL}/3")]
    assert session.bodies == [None]
    assert result == (None, {"status_code": 204})


def test_clear_issue_labels_deletes_the_label_list():
    """Clearing should DELETE the issue's label list."""
    session = RecordingSession(NO_CONTENT)
    with patch("gitea.client.gitea.requests.Session", return_value=session), Gitea(base_url=BASE_URL) as client:
        result = client.issue.clear_issue_labels(owner="o", repository="r", index=34)

    assert session.requests == [("DELETE", LABELS_URL)]
    assert result == (None, {"status_code": 204})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "kwargs", "payload", "expected_request", "expected_body", "expected_result"),
    [
        ("list_issue_labels", {}, [BUG], ("GET", LABELS_URL), None, ([BUG], {"status_code": 200})),
        (
            "add_issue_labels",
            {"labels": [3]},
            [BUG],
            ("POST", LABELS_URL),
            {"labels": [3]},
            ([BUG], {"status_code": 200}),
        ),
        (
            "replace_issue_labels",
            {"labels": [3]},
            [BUG],
            ("PUT", LABELS_URL),
            {"labels": [3]},
            ([BUG], {"status_code": 200}),
        ),
        (
            "remove_issue_label",
            {"label": 3},
            NO_CONTENT,
            ("DELETE", f"{LABELS_URL}/3"),
            None,
            (None, {"status_code": 204}),
        ),
        ("clear_issue_labels", {}, NO_CONTENT, ("DELETE", LABELS_URL), None, (None, {"status_code": 204})),
    ],
)
async def test_async_methods_send_what_the_sync_ones_send(
    method, kwargs, payload, expected_request, expected_body, expected_result
):
    """Each asynchronous method should send the same request as its synchronous twin."""
    session = AsyncRecordingSession(payload)
    with patch("gitea.client.async_gitea.ClientSession", return_value=session):
        async with AsyncGitea(base_url=BASE_URL) as client:
            result = await getattr(client.issue, method)(owner="o", repository="r", index=34, **kwargs)

    assert session.requests == [expected_request]
    assert session.bodies == [expected_body]
    assert result == expected_result
