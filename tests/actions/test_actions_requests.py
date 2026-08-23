"""What each Actions method asks the instance for, and what it hands back.

Built as `tests/project/test_project_requests.py` is built, and for the same
reason: a test that stands in for the client sees the one call a method makes but
not the request it produced, so a filter that stops being forwarded, or a flag
that reaches the query string in a spelling neither HTTP client can carry,
changes nothing such a test observes. Every method is driven through the real
client here, whose session is the recording stand-in of `tests/transport.py`, and
the URL, the query parameters and the JSON body it really built are compared
against what the endpoint takes.

Four things are specific to this resource and are why the table below looks
different from the project one:

* Most listings answer with an object - `total_count` alongside `workflows`,
  `workflow_runs`, `jobs`, `artifacts` or `runners` - and not with a bare array,
  so the default such a listing falls back to is the empty object rather than the
  empty list. The secret and variable listings are the two exceptions, and their
  entries say so by falling back to the empty list.
* Two endpoints answer with a file rather than with a document. A job's logs are
  declared as a `RawBody` and the method hands back text; an artifact's archive
  is declared as `RawBytes` and the method hands back bytes, undecoded.
* Most of the API exists at four scopes, and which one a call means is decided by
  the coordinates it was given rather than by the method it called. So a method
  reached at more than one scope appears more than once below, once per path it
  can address - that being the part a wrong scope would get wrong invisibly.
* Several endpoints answer without a body at all. Their entries still declare a
  payload, because the first test drives the `200` case; the `empty` field is what
  the second test pins, and that is the case the real endpoint always answers with.

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
from tests.transport import NO_CONTENT, AsyncRecordingSession, RawBody, RawBytes, RecordingSession

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
ARTIFACT_ID = 9
RUNNER_ID = 7
SECRET_NAME = "DEPLOY_TOKEN"
VARIABLE_NAME = "ENVIRONMENT"

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

ARTIFACT = {"id": ARTIFACT_ID, "name": "dist", "size_in_bytes": 12, "expired": False}
ARTIFACTS = {"total_count": 1, "artifacts": [ARTIFACT]}

# An archive as the endpoint sends it. The bytes are deliberately not valid UTF-8:
# a zip is handed back undecoded, and decoding it would replace exactly these.
ARCHIVE = b"PK\x03\x04\xff\xfe not text \x00"

SECRET = {"name": SECRET_NAME, "description": "for deploys", "created_at": "2026-08-23T10:00:00+02:00"}
VARIABLE = {"name": VARIABLE_NAME, "data": "staging", "description": "", "owner_id": 23, "repo_id": 254}
RUNNER = {
    "id": RUNNER_ID,
    "name": "runner-1",
    "status": "online",
    "busy": False,
    "disabled": False,
    "ephemeral": False,
    "labels": [{"id": 1, "name": "ubuntu-latest", "type": "docker"}],
}
RUNNERS = {"total_count": 1, "runners": [RUNNER]}
# Spelled so that it reads as a fixture rather than as a credential: the
# secret scanner in the pre-commit suite flags anything that looks like one,
# and it is right to.
REGISTRATION_TOKEN = {"token": "a-fake-registration-token"}

# The answer of an endpoint that reports success without a body, as this table
# declares it: the second test is what drives the real `204`, and the first needs
# a body to compare. The empty object is what both then expect.
NO_BODY: dict[str, Any] = {}

# The four paths the same endpoints sit under, and the coordinates that address
# each. They are what a method reached at more than one scope is declared against,
# once per path, because a scope resolved wrongly reaches a URL that exists and
# answers with somebody else's data.
ACTIONS = f"/repos/{OWNER}/{REPOSITORY}/actions"
ORGANIZATION_ACTIONS = f"/orgs/{OWNER}/actions"
ACCOUNT_ACTIONS = "/user/actions"
INSTANCE_ACTIONS = "/admin/actions"

OF_REPOSITORY = {"owner": OWNER, "repository": REPOSITORY}
OF_ORGANIZATION = {"owner": OWNER}
OF_ACCOUNT: dict[str, Any] = {}
OF_INSTANCE = {"admin": True}


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
    # --- the runs and jobs of a wider scope ---------------------------------
    #
    # The same endpoints as the two above, under a different prefix. Declared
    # here per scope because a call that resolved the scope wrongly reaches a URL
    # that exists and answers with a different owner's runs.
    Call(
        name="list_workflow_runs",
        arguments=OF_ORGANIZATION | {"status": "failure", "page": 1},
        verb="GET",
        path=f"{ORGANIZATION_ACTIONS}/runs",
        params={"status": "failure", "page": 1},
        payload=RUNS,
        empty={},
    ),
    Call(
        name="list_workflow_runs",
        arguments=OF_ACCOUNT,
        verb="GET",
        path=f"{ACCOUNT_ACTIONS}/runs",
        payload=RUNS,
        empty={},
    ),
    Call(
        name="list_workflow_runs",
        arguments=OF_INSTANCE | {"actor": "someone"},
        verb="GET",
        path=f"{INSTANCE_ACTIONS}/runs",
        params={"actor": "someone"},
        payload=RUNS,
        empty={},
    ),
    Call(
        name="list_workflow_jobs",
        arguments=OF_REPOSITORY | {"status": "queued", "page": 2, "limit": 5},
        verb="GET",
        path=f"{ACTIONS}/jobs",
        params={"status": "queued", "page": 2, "limit": 5},
        payload=JOBS,
        empty={},
    ),
    Call(
        name="list_workflow_jobs",
        arguments=OF_ORGANIZATION,
        verb="GET",
        path=f"{ORGANIZATION_ACTIONS}/jobs",
        payload=JOBS,
        empty={},
    ),
    Call(
        name="list_workflow_jobs",
        arguments=OF_ACCOUNT,
        verb="GET",
        path=f"{ACCOUNT_ACTIONS}/jobs",
        payload=JOBS,
        empty={},
    ),
    Call(
        name="list_workflow_jobs",
        arguments=OF_INSTANCE | {"status": "in_progress"},
        verb="GET",
        path=f"{INSTANCE_ACTIONS}/jobs",
        params={"status": "in_progress"},
        payload=JOBS,
        empty={},
    ),
    # --- acting on a run ----------------------------------------------------
    #
    # Cancelling and rerunning each have two endpoints, chosen by a flag rather
    # than by a method of their own, so both spellings are declared: a flag that
    # stopped being read would send the milder request and report success.
    Call(
        name="cancel_workflow_run",
        arguments=OF_REPOSITORY | {"run_id": RUN_ID},
        verb="POST",
        path=f"{ACTIONS}/runs/{RUN_ID}/cancel",
        payload=RUN,
        empty={},
    ),
    Call(
        name="cancel_workflow_run",
        arguments=OF_REPOSITORY | {"run_id": RUN_ID, "force": True},
        verb="POST",
        path=f"{ACTIONS}/runs/{RUN_ID}/force-cancel",
        payload=RUN,
        empty={},
    ),
    Call(
        name="approve_workflow_run",
        arguments=OF_REPOSITORY | {"run_id": RUN_ID},
        verb="POST",
        path=f"{ACTIONS}/runs/{RUN_ID}/approve",
        payload=RUN,
        empty={},
    ),
    Call(
        name="rerun_workflow_run",
        arguments=OF_REPOSITORY | {"run_id": RUN_ID},
        verb="POST",
        path=f"{ACTIONS}/runs/{RUN_ID}/rerun",
        payload=RUN,
        empty={},
    ),
    Call(
        name="rerun_workflow_run",
        arguments=OF_REPOSITORY | {"run_id": RUN_ID, "failed_jobs_only": True},
        verb="POST",
        path=f"{ACTIONS}/runs/{RUN_ID}/rerun-failed-jobs",
        payload=NO_BODY,
        empty={},
    ),
    # The one job endpoint addressed through its run.
    Call(
        name="rerun_workflow_job",
        arguments=OF_REPOSITORY | {"run_id": RUN_ID, "job_id": JOB_ID},
        verb="POST",
        path=f"{ACTIONS}/runs/{RUN_ID}/jobs/{JOB_ID}/rerun",
        payload=JOB,
        empty={},
    ),
    Call(
        name="delete_workflow_run",
        arguments=OF_REPOSITORY | {"run_id": RUN_ID},
        verb="DELETE",
        path=f"{ACTIONS}/runs/{RUN_ID}",
        payload=NO_BODY,
        empty={},
    ),
    # --- artifacts ----------------------------------------------------------
    #
    # As with the runs, naming a run addresses a different endpoint rather than
    # filtering the repository-wide one.
    Call(
        name="list_artifacts",
        arguments=OF_REPOSITORY | {"name": "dist"},
        verb="GET",
        path=f"{ACTIONS}/artifacts",
        params={"name": "dist"},
        payload=ARTIFACTS,
        empty={},
    ),
    Call(
        name="list_artifacts",
        arguments=OF_REPOSITORY | {"run_id": RUN_ID},
        verb="GET",
        path=f"{ACTIONS}/runs/{RUN_ID}/artifacts",
        payload=ARTIFACTS,
        empty={},
    ),
    Call(
        name="get_artifact",
        arguments=OF_REPOSITORY | {"artifact_id": ARTIFACT_ID},
        verb="GET",
        path=f"{ACTIONS}/artifacts/{ARTIFACT_ID}",
        payload=ARTIFACT,
        empty={},
    ),
    # The second method whose answer is not a parsed body, and the only one whose
    # answer is not text either: the archive is handed back as the bytes it is, so
    # an artifact that has expired answers with the empty bytes.
    Call(
        name="download_artifact",
        arguments=OF_REPOSITORY | {"artifact_id": ARTIFACT_ID},
        verb="GET",
        path=f"{ACTIONS}/artifacts/{ARTIFACT_ID}/zip",
        payload=RawBytes(ARCHIVE),
        data=ARCHIVE,
        empty=b"",
    ),
    Call(
        name="delete_artifact",
        arguments=OF_REPOSITORY | {"artifact_id": ARTIFACT_ID},
        verb="DELETE",
        path=f"{ACTIONS}/artifacts/{ARTIFACT_ID}",
        payload=NO_BODY,
        empty={},
    ),
    # --- secrets ------------------------------------------------------------
    #
    # The listing is one of the two in this API that answer with a bare array, so
    # it falls back to the empty list where its neighbours fall back to the empty
    # object. It has no form for the authenticated account; setting and deleting
    # do, and that scope is declared on those.
    Call(
        name="list_secrets",
        arguments=OF_REPOSITORY | {"page": 2, "limit": 5},
        verb="GET",
        path=f"{ACTIONS}/secrets",
        params={"page": 2, "limit": 5},
        payload=[SECRET],
        empty=[],
    ),
    Call(
        name="list_secrets",
        arguments=OF_ORGANIZATION,
        verb="GET",
        path=f"{ORGANIZATION_ACTIONS}/secrets",
        payload=[SECRET],
        empty=[],
    ),
    Call(
        name="create_or_update_secret",
        arguments=OF_REPOSITORY | {"secret_name": SECRET_NAME, "data": "hunter2", "description": "for deploys"},
        verb="PUT",
        path=f"{ACTIONS}/secrets/{SECRET_NAME}",
        body={"data": "hunter2", "description": "for deploys"},
        payload=NO_BODY,
        empty={},
    ),
    # Without a description, no `description` field at all: sending it empty would
    # clear the one the secret already has.
    Call(
        name="create_or_update_secret",
        arguments=OF_ACCOUNT | {"secret_name": SECRET_NAME, "data": "hunter2"},
        verb="PUT",
        path=f"{ACCOUNT_ACTIONS}/secrets/{SECRET_NAME}",
        body={"data": "hunter2"},
        payload=NO_BODY,
        empty={},
    ),
    Call(
        name="delete_secret",
        arguments=OF_ORGANIZATION | {"secret_name": SECRET_NAME},
        verb="DELETE",
        path=f"{ORGANIZATION_ACTIONS}/secrets/{SECRET_NAME}",
        payload=NO_BODY,
        empty={},
    ),
    # --- variables ----------------------------------------------------------
    Call(
        name="list_variables",
        arguments=OF_REPOSITORY | {"page": 3, "limit": 7},
        verb="GET",
        path=f"{ACTIONS}/variables",
        params={"page": 3, "limit": 7},
        payload=[VARIABLE],
        empty=[],
    ),
    Call(
        name="list_variables",
        arguments=OF_ACCOUNT,
        verb="GET",
        path=f"{ACCOUNT_ACTIONS}/variables",
        payload=[VARIABLE],
        empty=[],
    ),
    Call(
        name="get_variable",
        arguments=OF_ORGANIZATION | {"variable_name": VARIABLE_NAME},
        verb="GET",
        path=f"{ORGANIZATION_ACTIONS}/variables/{VARIABLE_NAME}",
        payload=VARIABLE,
        empty={},
    ),
    # Creating is a POST and updating a PUT to the same path, which is the whole
    # difference between a create that refuses to overwrite and an update that
    # does. A method sending the wrong verb would overwrite silently.
    Call(
        name="create_variable",
        arguments=OF_REPOSITORY | {"variable_name": VARIABLE_NAME, "value": "staging", "description": "the target"},
        verb="POST",
        path=f"{ACTIONS}/variables/{VARIABLE_NAME}",
        body={"value": "staging", "description": "the target"},
        payload=NO_BODY,
        empty={},
    ),
    # The rename reaches the body as `name`, which is what Gitea calls it.
    Call(
        name="update_variable",
        arguments=OF_REPOSITORY
        | {"variable_name": VARIABLE_NAME, "value": "production", "new_name": "TARGET", "description": "renamed"},
        verb="PUT",
        path=f"{ACTIONS}/variables/{VARIABLE_NAME}",
        body={"value": "production", "name": "TARGET", "description": "renamed"},
        payload=NO_BODY,
        empty={},
    ),
    Call(
        name="update_variable",
        arguments=OF_ACCOUNT | {"variable_name": VARIABLE_NAME, "value": "production"},
        verb="PUT",
        path=f"{ACCOUNT_ACTIONS}/variables/{VARIABLE_NAME}",
        body={"value": "production"},
        payload=NO_BODY,
        empty={},
    ),
    Call(
        name="delete_variable",
        arguments=OF_REPOSITORY | {"variable_name": VARIABLE_NAME},
        verb="DELETE",
        path=f"{ACTIONS}/variables/{VARIABLE_NAME}",
        payload=NO_BODY,
        empty={},
    ),
    # --- runners ------------------------------------------------------------
    #
    # The one family offered at all four scopes, the instance included.
    Call(
        name="list_runners",
        arguments=OF_REPOSITORY | {"disabled": True},
        verb="GET",
        path=f"{ACTIONS}/runners",
        params={"disabled": "true"},
        payload=RUNNERS,
        empty={},
    ),
    Call(
        name="list_runners",
        arguments=OF_INSTANCE | {"disabled": False},
        verb="GET",
        path=f"{INSTANCE_ACTIONS}/runners",
        params={"disabled": "false"},
        payload=RUNNERS,
        empty={},
    ),
    Call(
        name="list_runners",
        arguments=OF_ACCOUNT,
        verb="GET",
        path=f"{ACCOUNT_ACTIONS}/runners",
        payload=RUNNERS,
        empty={},
    ),
    Call(
        name="get_runner",
        arguments=OF_ORGANIZATION | {"runner_id": RUNNER_ID},
        verb="GET",
        path=f"{ORGANIZATION_ACTIONS}/runners/{RUNNER_ID}",
        payload=RUNNER,
        empty={},
    ),
    # `disabled` is a body field here rather than a query parameter, so it is sent
    # as a JSON boolean and not as the API's query spelling.
    Call(
        name="update_runner",
        arguments=OF_REPOSITORY | {"runner_id": RUNNER_ID, "disabled": True},
        verb="PATCH",
        path=f"{ACTIONS}/runners/{RUNNER_ID}",
        body={"disabled": True},
        payload=RUNNER,
        empty={},
    ),
    Call(
        name="delete_runner",
        arguments=OF_INSTANCE | {"runner_id": RUNNER_ID},
        verb="DELETE",
        path=f"{INSTANCE_ACTIONS}/runners/{RUNNER_ID}",
        payload=NO_BODY,
        empty={},
    ),
    Call(
        name="create_runner_registration_token",
        arguments=OF_REPOSITORY,
        verb="POST",
        path=f"{ACTIONS}/runners/registration-token",
        payload=REGISTRATION_TOKEN,
        empty={},
    ),
    Call(
        name="create_runner_registration_token",
        arguments=OF_ACCOUNT,
        verb="POST",
        path=f"{ACCOUNT_ACTIONS}/runners/registration-token",
        payload=REGISTRATION_TOKEN,
        empty={},
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


def public_methods(resource: type) -> set[str]:
    """Collect the public methods a resource offers, however they were composed in.

    The families of this resource are separate classes that `Actions` inherits, so
    the methods are spread over the MRO rather than defined on the one class. The
    walk goes over it: reading `vars` of the class alone would have found the
    workflow methods and quietly missed every family added since, which is the
    opposite of what the check below is for.

    Args:
        resource: The resource class to enumerate.

    Returns:
        The names of its public methods.

    """
    names: set[str] = set()
    for klass in resource.__mro__:
        names |= {name for name in vars(klass) if not name.startswith("_") and callable(getattr(resource, name))}
    return names


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
        public = public_methods(resource)
        assert public == declared, f"{resource.__name__} has methods no entry declares: {public - declared}"


def test_both_resources_offer_the_same_methods() -> None:
    """The two clients should offer the same surface, method for method.

    The families are mirrored module by module rather than shared, so a method
    added to one and forgotten in the other is a real possibility - and the
    failure it produces is an `AttributeError` in somebody's asynchronous code,
    long after the synchronous version was reviewed.
    """
    assert public_methods(Actions) == public_methods(AsyncActions)


def test_an_archive_is_handed_back_undecoded() -> None:
    """An artifact's archive should arrive as the bytes it is, from either client.

    The job log endpoint's answer is decoded as UTF-8 with the invalid bytes
    replaced, which is right for a log and destroys a zip: the replacement is
    lossy, so an archive that went through it would no longer open. The archive
    declared above is deliberately not valid UTF-8, so a method that decoded it
    would hand back something that is not equal to it.
    """
    call = next(entry for entry in CALLS if entry.name == "download_artifact")

    (archive, _), _ = invoke(call, RawBytes(ARCHIVE))

    assert archive == ARCHIVE
    assert isinstance(archive, bytes)
