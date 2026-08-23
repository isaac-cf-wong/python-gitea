"""What each Actions method asks the instance for, and what it hands back.

Built as `tests/project/test_project_requests.py` is built, and for the same
reason: a test that stands in for the client sees the one call a method makes but
not the request it produced, so a filter that stops being forwarded, or a flag
that reaches the query string in a spelling neither HTTP client can carry,
changes nothing such a test observes. Every method is driven through the real
client here, whose session is the recording stand-in of `tests/transport.py`, and
the URL, the query parameters and the JSON body it really built are compared
against what the endpoint takes.

Two things are specific to this resource and are why the table below looks
different from the project one:

* The listings answer with an object - `total_count` alongside `workflows`,
  `workflow_runs` or `jobs` - and not with a bare array, so the default a
  listing falls back to is the empty object rather than the empty list.
* The job log endpoint answers with the log file rather than with a document, so
  its payload is declared as a `RawBody` and the method hands back text.

`test_every_actions_method_is_declared` keeps the table honest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import pytest

from gitea.actions.actions import Actions
from gitea.actions.async_actions import AsyncActions
from gitea.client.async_gitea import AsyncGitea
from gitea.client.gitea import Gitea
from tests.transport import NO_CONTENT, AsyncRecordingSession, RawBody, RecordingSession

BASE_URL = "https://gitea.invalid"
TOKEN = "seed-token"
API_ROOT = f"{BASE_URL}/api/v1"

# A header handed to the public method and expected to arrive at the session. It
# travels the whole way as `**kwargs`, so a call that stops spreading them loses
# it, which nothing else observes: the URL, the parameters and the body are all
# built before the spread.
PROBE = "X-Probe"
PROBE_HEADERS = {PROBE: "forwarded"}

# The coordinates every call is addressed with, distinct so that one arriving in
# another's place is visible in the URL.
OWNER = "o"
REPOSITORY = "r"
WORKFLOW_ID = "build.yml"
RUN_ID = 42
JOB_ID = 118

# The objects the fake instance answers with, keyed as the Gitea API keys them.
WORKFLOW = {"id": WORKFLOW_ID, "name": "Build", "path": ".gitea/workflows/build.yml", "state": "active"}
WORKFLOWS = {"total_count": 1, "workflows": [WORKFLOW]}
RUN = {"id": RUN_ID, "run_number": 7, "status": "success", "conclusion": "success", "event": "push"}
RUNS = {"total_count": 1, "workflow_runs": [RUN]}
JOB = {"id": JOB_ID, "run_id": RUN_ID, "name": "build", "status": "success", "conclusion": "success", "steps": []}
JOBS = {"total_count": 1, "jobs": [JOB]}
RUN_DETAILS = {"workflow_run_id": RUN_ID, "run_url": f"{BASE_URL}/api/v1/repos/o/r/actions/runs/{RUN_ID}"}

# A log as the endpoint sends it: the file, not a document describing it. The
# non-ASCII line is here because the body is decoded explicitly as UTF-8 rather
# than through the HTTP client's guess at an encoding.
LOGS = "::group::Run\nbuilding…\ndone\n"

ACTIONS = f"/repos/{OWNER}/{REPOSITORY}/actions"
OF_REPOSITORY = {"owner": OWNER, "repository": REPOSITORY}


class Unchanged:
    """Declares that a method hands back the payload it was answered with, unaltered."""

    def __repr__(self) -> str:
        """Name the sentinel in a test failure.

        Returns:
            The name this is referred to by.

        """
        return "UNCHANGED"


UNCHANGED = Unchanged()


@dataclass(frozen=True)
class Call:
    """One Actions method, the request it makes and the answer it gives.

    Attributes:
        name: The method, on `client.actions`, in both clients.
        arguments: What it is called with, every optional argument included.
        verb: The HTTP method the request is expected to use.
        path: The path under the API root the request is expected to address.
        payload: What the endpoint answers with.
        empty: What the method answers with when the endpoint answers without a
            body, which is the default it asks the response processor for.
        params: The query parameters the request is expected to carry.
        body: The JSON body it is expected to carry, or None for a request
            without one.
        data: What the method hands back. `UNCHANGED` declares it to be
            `payload` exactly, which is what a method passing a parsed body
            through hands back.

    """

    name: str
    arguments: dict[str, Any]
    verb: str
    path: str
    payload: Any
    empty: Any
    params: dict[str, Any] = field(default_factory=dict)
    body: Any = None
    data: Any = UNCHANGED


CALLS = [
    Call(
        name="list_workflows",
        arguments=OF_REPOSITORY,
        verb="GET",
        path=f"{ACTIONS}/workflows",
        payload=WORKFLOWS,
        empty={},
    ),
    Call(
        name="get_workflow",
        arguments=OF_REPOSITORY | {"workflow_id": WORKFLOW_ID},
        verb="GET",
        path=f"{ACTIONS}/workflows/{WORKFLOW_ID}",
        payload=WORKFLOW,
        empty={},
    ),
    Call(
        name="dispatch_workflow",
        arguments=OF_REPOSITORY
        | {
            "workflow_id": WORKFLOW_ID,
            "ref": "refs/heads/main",
            "inputs": {"environment": "staging"},
            "return_run_details": True,
        },
        verb="POST",
        path=f"{ACTIONS}/workflows/{WORKFLOW_ID}/dispatches",
        params={"return_run_details": "true"},
        body={"ref": "refs/heads/main", "inputs": {"environment": "staging"}},
        payload=RUN_DETAILS,
        empty={},
    ),
    # The dispatch as it is made without either option: no `inputs` field at
    # all, and the flag spelled `false` rather than sent as a Python bool - which
    # the asynchronous client's URL builder refuses outright.
    Call(
        name="dispatch_workflow",
        arguments=OF_REPOSITORY | {"workflow_id": WORKFLOW_ID, "ref": "main", "return_run_details": False},
        verb="POST",
        path=f"{ACTIONS}/workflows/{WORKFLOW_ID}/dispatches",
        params={"return_run_details": "false"},
        body={"ref": "main"},
        payload=RUN_DETAILS,
        empty={},
    ),
    Call(
        name="list_workflow_runs",
        arguments=OF_REPOSITORY
        | {
            "event": "push",
            "branch": "main",
            "status": "success",
            "actor": "someone",
            "head_sha": "deadbeef",
            "exclude_pull_requests": True,
            "page": 2,
            "limit": 5,
        },
        verb="GET",
        path=f"{ACTIONS}/runs",
        params={
            "event": "push",
            "branch": "main",
            "status": "success",
            "actor": "someone",
            "head_sha": "deadbeef",
            "exclude_pull_requests": "true",
            "page": 2,
            "limit": 5,
        },
        payload=RUNS,
        empty={},
    ),
    # Naming a workflow addresses a different endpoint rather than adding a
    # filter to the same one.
    Call(
        name="list_workflow_runs",
        arguments=OF_REPOSITORY | {"workflow_id": WORKFLOW_ID, "exclude_pull_requests": False},
        verb="GET",
        path=f"{ACTIONS}/workflows/{WORKFLOW_ID}/runs",
        params={"exclude_pull_requests": "false"},
        payload=RUNS,
        empty={},
    ),
    Call(
        name="get_workflow_run",
        arguments=OF_REPOSITORY | {"run_id": RUN_ID},
        verb="GET",
        path=f"{ACTIONS}/runs/{RUN_ID}",
        payload=RUN,
        empty={},
    ),
    Call(
        name="list_workflow_run_jobs",
        arguments=OF_REPOSITORY | {"run_id": RUN_ID, "status": "failure", "page": 3, "limit": 7},
        verb="GET",
        path=f"{ACTIONS}/runs/{RUN_ID}/jobs",
        params={"status": "failure", "page": 3, "limit": 7},
        payload=JOBS,
        empty={},
    ),
    Call(
        name="get_workflow_job",
        arguments=OF_REPOSITORY | {"job_id": JOB_ID},
        verb="GET",
        path=f"{ACTIONS}/jobs/{JOB_ID}",
        payload=JOB,
        empty={},
    ),
    # The one method whose answer is not a parsed body: the log arrives as bytes
    # and is handed back as the text it is, so a job that has produced nothing
    # yet answers with the empty string rather than with an empty object.
    Call(
        name="get_workflow_job_logs",
        arguments=OF_REPOSITORY | {"job_id": JOB_ID},
        verb="GET",
        path=f"{ACTIONS}/jobs/{JOB_ID}/logs",
        payload=RawBody(LOGS),
        data=LOGS,
        empty="",
    ),
]

CASES = [pytest.param(call, id=f"{call.name}-{index}") for index, call in enumerate(CALLS)]


def expected_data(call: Call) -> Any:
    """Read the payload a call has to hand back.

    Args:
        call: The method that ran.

    Returns:
        What it is expected to answer with.

    """
    return call.payload if isinstance(call.data, Unchanged) else call.data


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
        result = getattr(client.actions, call.name)(**call.arguments, headers=dict(PROBE_HEADERS))
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
            result = await getattr(client.actions, call.name)(**call.arguments, headers=dict(PROBE_HEADERS))
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
    assert data == expected_data(call)
    assert metadata == {"status_code": 200}


@pytest.mark.parametrize("call", CASES)
def test_a_response_without_a_body_answers_with_the_default(call: Call) -> None:
    """A method answered without a body should hand back the empty payload of its own shape.

    A dispatch really does answer `204` unless the run details were asked for,
    and a caller reading a field off the result meets a `TypeError` rather than
    an empty result when the default is not the shape the method documents.
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
    assert data == expected_data(call)
    assert metadata == {"status_code": 200}


@pytest.mark.asyncio
@pytest.mark.parametrize("call", CASES)
async def test_an_async_response_without_a_body_answers_with_the_default(call: Call) -> None:
    """A method asked asynchronously and answered without a body should fall back the same way."""
    (data, metadata), session = await invoke_async(call, NO_CONTENT)

    assert_addressed(call, session)
    assert data == call.empty
    assert metadata == {"status_code": 204}


def test_a_log_is_decoded_as_utf8_by_both_clients() -> None:
    """A log carrying non-ASCII text should arrive intact, and identically, from either client.

    The body is decoded explicitly rather than through `requests.Response.text`,
    which guesses an encoding when the response declares none. The guess and the
    asynchronous client's fixed UTF-8 would then disagree about the same bytes,
    so the two clients are compared against the text itself and against each
    other.
    """
    call = next(entry for entry in CALLS if entry.name == "get_workflow_job_logs")

    (synchronous, _), _ = invoke(call, RawBody(LOGS))

    assert synchronous == LOGS
    assert "…" in synchronous


def test_every_actions_method_is_declared() -> None:
    """Every public method of both resources should be declared in the table above.

    One added without an entry makes whatever request it makes, and the first
    anyone hears of a dropped filter is a listing that answers with the wrong
    runs against a real instance.

    This enumerates the members of a class rather than calling it, so it reads
    the instrumentation of a mutation run rather than the code and is deselected
    there; `[tool.mutmut]` in `pyproject.toml` says so and why.
    """
    declared = {call.name for call in CALLS}

    for resource in (Actions, AsyncActions):
        public = {name for name in vars(resource) if not name.startswith("_") and callable(getattr(resource, name))}
        assert public == declared, f"{resource.__name__} has methods no entry declares: {public - declared}"
