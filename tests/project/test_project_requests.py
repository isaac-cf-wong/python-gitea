"""What each project method asks the instance for, and what it hands back.

`tests/project/test_project_project.py` stands in for the client and for the
response processor, which pins the one call each method makes but leaves the rest
of the method unobserved: with `process_response` replaced by a mock, what is
passed to it cannot matter, and a value the method forwards on the way to its
request is only seen through that one call. A `page` that stops being forwarded,
a `color` that arrives as `None`, a `**kwargs` dropped from the call to the
private method - none of them change anything such a test looks at, while each
pages a listing wrongly or drops a field against a real instance.

So the request itself is asserted here. Every method is driven through the real
client, whose session is the recording stand-in of `tests/transport.py`, and the
URL, the query parameters and the JSON body it really built are compared against
what the endpoint takes. The response is the real one too - `process_response`
runs - so what the method answers with, and what it falls back to when the
endpoint sends no body, are asserted rather than mocked.

Each method is declared once, in `CALLS`, with every optional argument given a
value: an argument left at its default is one whose forwarding nothing here would
notice. `test_every_project_method_is_declared` keeps the table honest.

This is added to the older file rather than replacing it. A request is the wrong
place to see the difference between an empty mapping of query parameters and none
at all - both build the same URL - so the call the older file asserts on is still
where a method passing `None` where it means "nothing to ask for" is caught.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import pytest

from gitea.client.async_gitea import AsyncGitea
from gitea.client.gitea import Gitea
from gitea.project.async_project import AsyncProject
from gitea.project.project import Project
from tests.transport import NO_CONTENT, AsyncRecordingSession, RecordingSession

BASE_URL = "https://gitea.invalid"
TOKEN = "seed-token"
API_ROOT = f"{BASE_URL}/api/v1"

# A header handed to the public method and expected to arrive at the session. It
# travels the whole way as `**kwargs`, so a call that stops spreading them - from
# the public method to the private one, or from there to the request - loses it,
# which nothing else observes: the URL, the parameters and the body are all built
# before the spread.
PROBE = "X-Probe"
PROBE_HEADERS = {PROBE: "forwarded"}

# The objects the fake instance answers with, keyed as the Gitea API keys them.
PROJECT = {"id": 31, "title": "Board", "state": "open", "card_type": "text_only"}
COLUMN = {"id": 117, "title": "Working", "default": False, "sorting": 0, "project_id": 31}
ISSUE = {"id": 1883, "number": 44, "title": "A card on the board", "state": "open"}

# What an endpoint that acts rather than answers sends back. Gitea answers these
# with `204`, which the second test of each pair covers; the body here is the
# empty object, so the payload asserted is one the endpoint could really send.
ACTED: dict[str, Any] = {}

# The coordinates every call is addressed with. They are distinct values so that
# one arriving in another's place is visible in the URL.
OWNER = "o"
REPOSITORY = "r"
PROJECT_ID = 31
COLUMN_ID = 117
ISSUE_ID = 1883


@dataclass(frozen=True)
class Call:
    """One project method, the request it makes and the answer it gives.

    Attributes:
        name: The method, on `client.project`, in both clients.
        arguments: What it is called with, every optional argument included.
        verb: The HTTP method the request is expected to use.
        path: The path under the API root the request is expected to address.
        params: The query parameters the request is expected to carry.
        body: The JSON body it is expected to carry, or None for a request
            without one.
        payload: What the endpoint answers with.
        empty: What the method answers with when the endpoint answers without a
            body, which is the default it asks the response processor for.

    """

    name: str
    arguments: dict[str, Any]
    verb: str
    path: str
    payload: Any
    empty: Any
    params: dict[str, Any] = field(default_factory=dict)
    body: Any = None


BOARD = f"/repos/{OWNER}/{REPOSITORY}/projects"
BOARD_ID = f"{BOARD}/{PROJECT_ID}"
COLUMNS = f"{BOARD_ID}/columns"
COLUMN_PATH = f"{COLUMNS}/{COLUMN_ID}"

# The coordinates every method takes, and the ones the column methods add.
OF_BOARD = {"owner": OWNER, "repository": REPOSITORY, "project_id": PROJECT_ID}
OF_COLUMN = OF_BOARD | {"column_id": COLUMN_ID}

CALLS = [
    Call(
        name="list_projects",
        arguments={"owner": OWNER, "repository": REPOSITORY, "state": "open", "page": 2, "limit": 5},
        verb="GET",
        path=BOARD,
        params={"state": "open", "page": 2, "limit": 5},
        payload=[PROJECT],
        empty=[],
    ),
    Call(
        name="list_projects",
        arguments={"owner": OWNER, "repository": None, "state": "closed", "page": 3, "limit": 7},
        verb="GET",
        path=f"/orgs/{OWNER}/projects",
        params={"state": "closed", "page": 3, "limit": 7},
        payload=[PROJECT],
        empty=[],
    ),
    Call(
        name="get_project",
        arguments=OF_BOARD,
        verb="GET",
        path=BOARD_ID,
        payload=PROJECT,
        empty={},
    ),
    Call(
        name="create_project",
        arguments={
            "owner": OWNER,
            "repository": REPOSITORY,
            "title": "Board",
            "description": "What is being worked on",
            "template_type": "basic_kanban",
            "card_type": "text_only",
        },
        verb="POST",
        path=BOARD,
        body={
            "title": "Board",
            "description": "What is being worked on",
            "template_type": "basic_kanban",
            "card_type": "text_only",
        },
        payload=PROJECT,
        empty={},
    ),
    Call(
        name="edit_project",
        arguments=OF_BOARD
        | {"title": "Renamed", "description": "Rewritten", "card_type": "text_only", "state": "closed"},
        verb="PATCH",
        path=BOARD_ID,
        body={"title": "Renamed", "description": "Rewritten", "card_type": "text_only", "state": "closed"},
        payload=PROJECT,
        empty={},
    ),
    Call(
        name="delete_project",
        arguments=OF_BOARD,
        verb="DELETE",
        path=BOARD_ID,
        payload=ACTED,
        empty={},
    ),
    Call(
        name="list_project_columns",
        arguments=OF_BOARD | {"page": 2, "limit": 5},
        verb="GET",
        path=COLUMNS,
        params={"page": 2, "limit": 5},
        payload=[COLUMN],
        empty=[],
    ),
    Call(
        name="create_project_column",
        arguments=OF_BOARD | {"title": "Working", "color": "#112233"},
        verb="POST",
        path=COLUMNS,
        body={"title": "Working", "color": "#112233"},
        payload=COLUMN,
        empty={},
    ),
    Call(
        name="get_project_column",
        arguments=OF_COLUMN,
        verb="GET",
        path=COLUMN_PATH,
        payload=COLUMN,
        empty={},
    ),
    Call(
        name="edit_project_column",
        arguments=OF_COLUMN | {"title": "Working", "color": "#112233", "sorting": 3},
        verb="PATCH",
        path=COLUMN_PATH,
        body={"title": "Working", "color": "#112233", "sorting": 3},
        payload=COLUMN,
        empty={},
    ),
    Call(
        name="delete_project_column",
        arguments=OF_COLUMN,
        verb="DELETE",
        path=COLUMN_PATH,
        payload=ACTED,
        empty={},
    ),
    Call(
        name="set_default_project_column",
        arguments=OF_COLUMN,
        verb="POST",
        path=f"{COLUMN_PATH}/default",
        payload=ACTED,
        empty={},
    ),
    Call(
        name="move_project_columns",
        arguments=OF_BOARD | {"column_ids": [COLUMN_ID, COLUMN_ID + 1]},
        verb="POST",
        path=f"{COLUMNS}/move",
        body={"column_ids": [COLUMN_ID, COLUMN_ID + 1]},
        payload=ACTED,
        empty={},
    ),
    Call(
        name="list_project_column_issues",
        arguments=OF_COLUMN | {"page": 2, "limit": 5},
        verb="GET",
        path=f"{COLUMN_PATH}/issues",
        params={"page": 2, "limit": 5},
        payload=[ISSUE],
        empty=[],
    ),
    Call(
        name="add_issue_to_project_column",
        arguments=OF_COLUMN | {"issue_id": ISSUE_ID},
        verb="POST",
        path=f"{COLUMN_PATH}/issues/{ISSUE_ID}",
        payload=ACTED,
        empty={},
    ),
    Call(
        name="remove_issue_from_project_column",
        arguments=OF_COLUMN | {"issue_id": ISSUE_ID},
        verb="DELETE",
        path=f"{COLUMN_PATH}/issues/{ISSUE_ID}",
        payload=ACTED,
        empty={},
    ),
    Call(
        name="move_project_issue",
        arguments=OF_BOARD | {"issue_id": ISSUE_ID, "column_id": COLUMN_ID + 1, "sorting": 3},
        verb="POST",
        path=f"{BOARD_ID}/issues/{ISSUE_ID}/move",
        body={"column_id": COLUMN_ID + 1, "sorting": 3},
        payload=ACTED,
        empty={},
    ),
]

CASES = [pytest.param(call, id=f"{call.name}-{call.verb.lower()}-{call.path.split('/')[1]}") for call in CALLS]


def invoke(call: Call, payload: Any) -> tuple[Any, RecordingSession]:
    """Run one method through the synchronous client, answered with a payload.

    Args:
        call: The method to run.
        payload: What the endpoint answers with.

    Returns:
        What the method returned, and the session recording what it asked for.

    """
    session = RecordingSession(payload)
    client = Gitea(token=TOKEN, base_url=BASE_URL)
    with patch("gitea.client.gitea.requests.Session", return_value=session), client:
        result = getattr(client.project, call.name)(**call.arguments, headers=dict(PROBE_HEADERS))
    return result, session


async def invoke_async(call: Call, payload: Any) -> tuple[Any, AsyncRecordingSession]:
    """Run one method through the asynchronous client, answered with a payload.

    Args:
        call: The method to run.
        payload: What the endpoint answers with.

    Returns:
        What the method returned, and the session recording what it asked for.

    """
    session = AsyncRecordingSession(payload)
    client = AsyncGitea(token=TOKEN, base_url=BASE_URL)
    with patch("gitea.client.async_gitea.ClientSession", return_value=session):
        async with client:
            result = await getattr(client.project, call.name)(**call.arguments, headers=dict(PROBE_HEADERS))
    return result, session


def assert_addressed(call: Call, session: RecordingSession) -> None:
    """Check the one request the method made, field for field.

    Args:
        call: The method that ran.
        session: The session recording what it asked for.

    """
    assert session.requests == [(call.verb, f"{API_ROOT}{call.path}")]
    assert session.params == [call.params]
    assert session.bodies == [call.body]
    assert session.headers[0].get("Authorization") == f"token {TOKEN}"
    assert session.headers[0].get(PROBE) == PROBE_HEADERS[PROBE]


@pytest.mark.parametrize("call", CASES)
def test_the_request_and_the_answer(call: Call) -> None:
    """Each method should address its endpoint and hand back what it was answered with."""
    (data, metadata), session = invoke(call, call.payload)

    assert_addressed(call, session)
    assert data == call.payload
    assert metadata == {"status_code": 200}


@pytest.mark.parametrize("call", CASES)
def test_a_response_without_a_body_answers_with_the_default(call: Call) -> None:
    """A method answered without a body should hand back the empty payload of its own shape.

    The endpoint of every method here can answer `204`, and a caller iterating
    what a listing returned, or reading a field of an object, meets a `TypeError`
    rather than an empty result when the default is not the shape the method
    documents.
    """
    (data, metadata), session = invoke(call, NO_CONTENT)

    assert_addressed(call, session)
    assert data == call.empty
    assert metadata == {"status_code": 204}


@pytest.mark.asyncio
@pytest.mark.parametrize("call", CASES)
async def test_the_async_request_and_the_answer(call: Call) -> None:
    """Each method asked asynchronously should address the same endpoint and answer the same way."""
    (data, metadata), session = await invoke_async(call, call.payload)

    assert_addressed(call, session)
    assert data == call.payload
    assert metadata == {"status_code": 200}


@pytest.mark.asyncio
@pytest.mark.parametrize("call", CASES)
async def test_an_async_response_without_a_body_answers_with_the_default(call: Call) -> None:
    """A method asked asynchronously and answered without a body should fall back the same way."""
    (data, metadata), session = await invoke_async(call, NO_CONTENT)

    assert_addressed(call, session)
    assert data == call.empty
    assert metadata == {"status_code": 204}


def test_every_project_method_is_declared() -> None:
    """Every public method of both resources should be declared in the table above.

    One added without an entry makes whatever request it makes, and the first
    anyone hears of a dropped argument is a listing that pages wrongly against a
    real instance.

    This enumerates the members of a class rather than calling it, so it reads
    the instrumentation of a mutation run rather than the code and is deselected
    there; `[tool.mutmut]` in `pyproject.toml` says so and why.
    """
    declared = {call.name for call in CALLS}

    for resource in (Project, AsyncProject):
        public = {name for name in vars(resource) if not name.startswith("_") and callable(getattr(resource, name))}
        assert public == declared, f"{resource.__name__} has methods no entry declares: {public - declared}"
