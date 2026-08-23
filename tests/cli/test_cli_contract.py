"""Contract tests: what every CLI subcommand emits, field for field.

The CLI's JSON envelope is an interface, and the field names in its `data` are the
part of it that changes without anyone deciding to change it. A helper that
rebuilds a payload, a rename that reads better, a field renamed upstream and
mirrored here - each is a one-line edit, none of them fails a test that only
checks that a command ran and printed an envelope, and each of them breaks a
script that was reading the old name.

So each subcommand is declared here with the responses it is answered with and
the `data` it has to emit for them, and the test runs the command and compares.
Every entry is exact: an extra field, a missing one and a renamed one all fail,
which is what makes this a contract rather than a smoke test. `UNCHANGED` is the
usual answer - the command emits the API's payload as it arrived, which is the
convention `gitea.utils.fields` states - so an entry spelling its data out is a
command that transforms it, and the transformation is legible in the table.

`test_every_subcommand_has_a_contract` keeps the table honest: a subcommand added
without an entry fails it rather than quietly going unpinned.

The requests are answered one level below the client, at the session it builds, so
the paths the commands ask for and the client's own parsing are under test as
well. Nothing here reaches the network or reads the user's configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml
from typer.main import get_command
from typer.testing import CliRunner

from gitea.cli.main import app
from gitea.watch.state import STATE_FILE_ENV
from tests.cli.envelope import parse_envelope
from tests.cli.tree import leaf_commands
from tests.transport import NO_CONTENT, RawBody, RoutedSession

runner = CliRunner()

BASE_URL = "https://gitea.invalid"

# The account each command is expected to act as, in the throwaway configuration
# every invocation is given. It is deliberately not the default account: a command
# that drops `--account-name` on the way to resolving it then reaches `OTHER`
# below, which the assertions can see, where falling back to the same account
# would look like working.
ACCOUNT = "seed"
TOKEN = "seed-token"

# The default account, which nothing here asks for. Its address and token differ
# from `ACCOUNT`'s, so reaching it is a visible failure rather than a silent one.
OTHER = "other"
OTHER_BASE_URL = "https://other.invalid"
OTHER_TOKEN = "other-token"

# The two ways a command is told which instance to talk to and with what. Both are
# run for every command reaching the API: an account to resolve, and credentials
# given outright. What a command emits cannot depend on which was used, and a
# command mishandling either reaches the wrong instance, or none, or reaches it
# unauthenticated - none of which the envelope shows when the responses are faked.
ACCOUNT_AUTH = ("--account-name", ACCOUNT)
EXPLICIT_AUTH = ("--token", TOKEN, "--base-url", BASE_URL)

# What the client sends once it has resolved either of them.
AUTHORIZATION = f"token {TOKEN}"
API_ROOT = f"{BASE_URL}/api/v1/"


class Unchanged:
    """Declares that a command emits the payload it was answered with, unaltered.

    Which is what nearly every command does, and what the field-name convention
    asks of them: the data is the API's own object, keyed as the API keyed it.
    """

    def __repr__(self) -> str:
        """Name the sentinel in a test failure.

        Returns:
            The name this is referred to by.

        """
        return "UNCHANGED"


UNCHANGED = Unchanged()

# --- The payloads the fake instance answers with ---------------------------
#
# Each is an object of its endpoint's own shape, keyed as the Gitea API keys it.
# They are the yardstick the emitted data is measured against, so a key here is
# one the API sends and not a convenient shorthand.

REPOSITORY = {"id": 254, "name": "r", "owner": "o", "full_name": "o/r"}

USER = {"id": 36, "login": "someone", "full_name": "", "email": "someone@example.invalid", "username": "someone"}

ORGANIZATION = {"id": 23, "username": "o", "full_name": "", "description": "", "visibility": "limited"}

COLUMN = {
    "id": 117,
    "title": "Working",
    "default": False,
    "sorting": 0,
    "project_id": 31,
    "created_at": "2026-08-17T06:53:32+02:00",
    "updated_at": "2026-08-18T12:46:48+02:00",
}

PROJECT = {
    "id": 31,
    "title": "Board",
    "description": "",
    "state": "open",
    "is_closed": False,
    "card_type": "text_only",
    "type": "organization",
    "repo_id": 0,
    "created_at": "2026-08-17T06:53:32+02:00",
    "updated_at": "2026-08-18T12:46:48+02:00",
}

# The project as an issue payload lists it: the same object without a column,
# because Gitea's project schema carries none. `issue get` resolves one.
PROJECT_ON_ISSUE = {"id": 31, "title": "Board", "type": "organization", "repo_id": 0}

ISSUE = {
    "id": 1873,
    "number": 34,
    "title": "unify field names between CLI JSON output and client dicts",
    "body": "",
    "state": "open",
    "comments": 3,
    "labels": [],
    "assignees": None,
    "milestone": None,
    "repository": REPOSITORY,
    "created_at": "2026-08-17T06:54:12+02:00",
    "updated_at": "2026-08-18T14:42:07+02:00",
}

# A second issue, for the run that has to see something change.
OTHER_ISSUE = {**ISSUE, "id": 1874, "number": 35, "title": "something else"}

ISSUE_ON_BOARD = {**ISSUE, "projects": [PROJECT_ON_ISSUE]}

COMMENT = {
    "id": 8206,
    "issue_url": f"{BASE_URL}/o/r/issues/34",
    "user": USER,
    "body": "Claiming this issue.",
    "assets": [],
    "created_at": "2026-08-18T12:57:23+02:00",
    "updated_at": "2026-08-18T12:57:23+02:00",
}

LABEL = {"id": 3, "name": "bug", "color": "ff0000", "description": "", "exclusive": False}

MILESTONE = {
    "id": 7,
    "title": "v1",
    "description": "",
    "state": "open",
    "open_issues": 1,
    "closed_issues": 0,
    "due_on": None,
}

PULL_REQUEST = {
    "id": 900,
    "number": 88,
    "title": "fix the pagination",
    "state": "open",
    "mergeable": True,
    "merged": False,
    "user": USER,
}

NOTIFICATION = {
    "id": 12,
    "repository": REPOSITORY,
    "subject": {"title": "unify field names", "type": "Issue", "state": "open"},
    "unread": True,
    "pinned": False,
    "updated_at": "2026-08-18T14:42:07+02:00",
}

# The Actions objects. Their listings are the one place in this API where a
# listing is an object rather than a bare array: `total_count` alongside the
# entries, which is what the commands emit and what these pin.
WORKFLOW = {
    "id": "build.yml",
    "name": "Build",
    "path": ".gitea/workflows/build.yml",
    "state": "active",
    "html_url": f"{BASE_URL}/o/r/actions?workflow=build.yml",
}

WORKFLOWS = {"total_count": 1, "workflows": [WORKFLOW]}

WORKFLOW_RUN = {
    "id": 42,
    "run_number": 7,
    "event": "push",
    "status": "success",
    "conclusion": "success",
    "head_branch": "main",
    "head_sha": "deadbeef",
    "pull_requests": [],
}

WORKFLOW_RUNS = {"total_count": 1, "workflow_runs": [WORKFLOW_RUN]}

WORKFLOW_JOB = {
    "id": 118,
    "run_id": 42,
    "name": "build",
    "status": "success",
    "conclusion": "success",
    "runner_name": "runner-1",
    "steps": [{"number": 1, "name": "Checkout", "status": "success", "conclusion": "success"}],
}

WORKFLOW_JOBS = {"total_count": 1, "jobs": [WORKFLOW_JOB]}

# A log as the endpoint sends it: the file itself, not a document describing it.
JOB_LOGS = "::group::Run\nbuilding\n::endgroup::\n"

USER_SETTINGS = {
    "full_name": "Someone",
    "theme": "gitea",
    "language": "en-US",
    "location": "",
    "website": "",
    "hide_email": False,
    "hide_activity": False,
    "diff_view_style": "unified",
}

# The board `issue get` and `project issues` walk. Ordered because the longer URL
# contains the shorter fragment: the issues of a column are matched first.
BOARD_ROUTES = (
    (f"/columns/{COLUMN['id']}/issues", [ISSUE_ON_BOARD]),
    ("/columns", [COLUMN]),
)

# What a watch reports for an issue that appeared and one that went away. Every
# record carries the same keys whatever the kind, which is itself the contract:
# a consumer reads `added` and `removed` without first asking what happened.
WATCH_SCOPE = "repo:o/r"


def _change(issue: dict[str, Any], kind: str, detail: str) -> dict[str, Any]:
    """Build the change record a watch reports for one issue.

    Args:
        issue: The issue the change is on.
        kind: What changed.
        detail: The change, as the human digest phrases it.

    Returns:
        The change record, including the scope the command adds.

    """
    return {
        "kind": kind,
        "issue_id": issue["id"],
        "number": issue["number"],
        "title": issue["title"],
        "repository": "o/r",
        "detail": detail,
        "added": [],
        "removed": [],
        "scope": WATCH_SCOPE,
    }


@dataclass(frozen=True)
class Contract:
    """One subcommand, what it is answered with, and the data it has to emit.

    Attributes:
        path: The subcommand, as its words are typed.
        args: The options the invocation passes, beyond `--output json` and the
            configuration path. Credentials are added for a command reaching the
            API.
        payload: The body every request of the command is answered with, unless a
            route claims it. `NO_CONTENT` answers as an endpoint that succeeds
            without a body does.
        routes: Endpoint fragments answered with a payload of their own, for a
            command reaching more than one endpoint. Matched in order.
        data: The `data` the command has to emit. `UNCHANGED` declares it to be
            `payload` exactly, which is what a command passing an API object
            through emits.
        metadata: The keys of the envelope's `metadata`. The values are left out:
            a path or a status code varies with the invocation, the keys are the
            contract.
        warmup: Routes for one invocation to run first, whose output is ignored.
            For a command reporting what changed since its last run, which has
            nothing to report on a first one.
        api: Whether the command reaches the API at all. The `config` commands do
            not; they act on the configuration file.

    """

    path: tuple[str, ...]
    args: tuple[str, ...] = ()
    payload: Any = None
    routes: tuple[tuple[str, Any], ...] = ()
    data: Any = UNCHANGED
    metadata: tuple[str, ...] = ("status_code",)
    warmup: tuple[tuple[str, Any], ...] | None = None
    api: bool = True


# The options addressing a repository, an issue on it, and a project of the
# owner, which most of the table repeats.
REPO = ("--owner", "o", "--repository", "r")
ISSUE_ARGS = (*REPO, "--issue-id", "34")
BOARD = ("--owner", "o", "--project-id", "31")

# The Actions entities, named as the convention names them: a workflow by its
# file name, a run and a job by their IDs.
WORKFLOW_ARGS = ("--workflow-id", "build.yml")
RUN_ARGS = ("--run-id", "42")
JOB_ARGS = ("--job-id", "118")

CONTRACTS = (
    # --- config: the CLI's own objects, not the API's ----------------------
    Contract(
        path=("config", "add"),
        args=("--name", "added", "--token", "tok", "--base-url", BASE_URL),
        data={"name": "added", "base_url": BASE_URL, "is_default": False, "status": "added"},
        metadata=("config_path",),
        api=False,
    ),
    Contract(
        path=("config", "delete"),
        args=("--name", ACCOUNT, "--force"),
        data={"name": ACCOUNT, "status": "deleted"},
        metadata=("config_path",),
        api=False,
    ),
    Contract(
        path=("config", "list"),
        # Both accounts, in the order the configuration carries them, and no token
        # for either: `config` commands never print one.
        data={
            "default_account": OTHER,
            "accounts": [
                {"name": OTHER, "base_url": OTHER_BASE_URL},
                {"name": ACCOUNT, "base_url": BASE_URL},
            ],
        },
        metadata=("config_path", "account_count"),
        api=False,
    ),
    Contract(
        path=("config", "update"),
        args=("--name", ACCOUNT, "--base-url", "https://moved.invalid"),
        data={
            "name": ACCOUNT,
            "base_url": "https://moved.invalid",
            "is_default": False,
            "updated_fields": ["base_url"],
            "status": "updated",
        },
        metadata=("config_path",),
        api=False,
    ),
    # --- issue -------------------------------------------------------------
    Contract(path=("issue", "close"), args=ISSUE_ARGS, payload=ISSUE),
    Contract(path=("issue", "create"), args=(*REPO, "--title", "T"), payload=ISSUE),
    Contract(path=("issue", "edit"), args=(*ISSUE_ARGS, "--title", "T"), payload=ISSUE),
    Contract(
        path=("issue", "get"),
        args=ISSUE_ARGS,
        payload=ISSUE_ON_BOARD,
        routes=BOARD_ROUTES,
        # The one field no endpoint sends: the column the issue's card sits in,
        # resolved from the board because the issue payload cannot say.
        data={**ISSUE_ON_BOARD, "projects": [{**PROJECT_ON_ISSUE, "column_id": COLUMN["id"]}]},
    ),
    Contract(path=("issue", "list"), args=REPO, payload=[ISSUE]),
    Contract(
        path=("issue", "dependency", "add"),
        args=(*ISSUE_ARGS, "--dependency-owner", "o", "--dependency-repository", "r", "--dependency-issue-id", "35"),
        payload=ISSUE,
    ),
    Contract(path=("issue", "dependency", "list"), args=ISSUE_ARGS, payload=[ISSUE]),
    Contract(
        path=("issue", "dependency", "remove"),
        args=(*ISSUE_ARGS, "--dependency-owner", "o", "--dependency-repository", "r", "--dependency-issue-id", "35"),
        payload=ISSUE,
    ),
    # `issue comment` and `comment` are the same commands under two names, so
    # both spellings are pinned: one of them could be rewired alone.
    Contract(path=("issue", "comment", "add"), args=(*ISSUE_ARGS, "--body", "hi"), payload=COMMENT),
    Contract(path=("issue", "comment", "delete"), args=(*REPO, "--comment-id", "8206"), payload=NO_CONTENT, data={}),
    Contract(
        path=("issue", "comment", "edit"),
        args=(*REPO, "--comment-id", "8206", "--body", "hi"),
        payload=COMMENT,
    ),
    Contract(path=("issue", "comment", "list"), args=ISSUE_ARGS, payload=[COMMENT]),
    Contract(path=("comment", "add"), args=(*ISSUE_ARGS, "--body", "hi"), payload=COMMENT),
    Contract(path=("comment", "delete"), args=(*REPO, "--comment-id", "8206"), payload=NO_CONTENT, data={}),
    Contract(path=("comment", "edit"), args=(*REPO, "--comment-id", "8206", "--body", "hi"), payload=COMMENT),
    Contract(path=("comment", "list"), args=ISSUE_ARGS, payload=[COMMENT]),
    # --- label, milestone, pull request, notification, user ----------------
    Contract(path=("label", "create"), args=(*REPO, "--name", "bug", "--color", "ff0000"), payload=LABEL),
    Contract(path=("label", "delete"), args=(*REPO, "--label-id", "3"), payload=NO_CONTENT, data={}),
    Contract(path=("label", "list"), args=REPO, payload=[LABEL]),
    Contract(path=("label", "update"), args=(*REPO, "--label-id", "3", "--name", "bug"), payload=LABEL),
    Contract(path=("milestone", "create"), args=(*REPO, "--title", "v1"), payload=MILESTONE),
    Contract(path=("milestone", "list"), args=REPO, payload=[MILESTONE]),
    Contract(path=("pull-request", "list"), args=REPO, payload=[PULL_REQUEST]),
    Contract(path=("notification", "list"), payload=[NOTIFICATION]),
    Contract(path=("notification", "read"), payload=[NOTIFICATION]),
    Contract(path=("user", "get"), payload=USER),
    Contract(path=("user", "update-settings"), args=("--theme", "gitea"), payload=USER_SETTINGS),
    # --- actions -----------------------------------------------------------
    Contract(path=("actions", "workflow", "list"), args=REPO, payload=WORKFLOWS),
    Contract(path=("actions", "workflow", "get"), args=(*REPO, *WORKFLOW_ARGS), payload=WORKFLOW),
    Contract(
        path=("actions", "workflow", "dispatch"),
        args=(*REPO, *WORKFLOW_ARGS, "--ref", "main", "--input", "environment=staging"),
        # Gitea accepts a dispatch with `204` and no body unless the run details
        # were asked for, so this is what a dispatch that worked emits.
        payload=NO_CONTENT,
        data={},
    ),
    Contract(path=("actions", "run", "list"), args=REPO, payload=WORKFLOW_RUNS),
    Contract(path=("actions", "run", "get"), args=(*REPO, *RUN_ARGS), payload=WORKFLOW_RUN),
    Contract(path=("actions", "run", "jobs"), args=(*REPO, *RUN_ARGS), payload=WORKFLOW_JOBS),
    Contract(path=("actions", "job", "get"), args=(*REPO, *JOB_ARGS), payload=WORKFLOW_JOB),
    Contract(
        path=("actions", "job", "logs"),
        args=(*REPO, *JOB_ARGS),
        # The one endpoint answering with a file rather than a document. The
        # command names the job the log belongs to, which the response cannot.
        payload=RawBody(JOB_LOGS),
        data={"job_id": 118, "logs": JOB_LOGS},
    ),
    # --- org, repo: discovering what an instance holds ----------------------
    Contract(path=("org", "list"), payload=[ORGANIZATION]),
    Contract(path=("repo", "list"), args=("--owner", "o"), payload=[REPOSITORY]),
    # --- project -----------------------------------------------------------
    Contract(path=("project", "create"), args=("--owner", "o", "--title", "Board"), payload=PROJECT),
    Contract(path=("project", "list"), args=("--owner", "o"), payload=[PROJECT]),
    Contract(path=("project", "get"), args=BOARD, payload=PROJECT),
    Contract(path=("project", "edit"), args=(*BOARD, "--title", "Board"), payload=PROJECT),
    Contract(path=("project", "delete"), args=BOARD, payload=NO_CONTENT, data={}),
    Contract(
        path=("project", "issues"),
        args=BOARD,
        routes=BOARD_ROUTES,
        # The one command that rebuilds a column rather than passing it on. It
        # names it `title`, as the API does; `name` here would be the rename the
        # convention exists to prevent.
        data=[{"column": {"id": COLUMN["id"], "title": COLUMN["title"]}, "issues": [ISSUE_ON_BOARD]}],
        metadata=("status_code", "column_count", "issue_count"),
    ),
    Contract(
        path=("project", "show"),
        args=BOARD,
        payload=PROJECT,
        routes=BOARD_ROUTES,
        # The board in one object: the project as the API sent it, and every
        # column as the API sent it with the cards on it counted and named.
        # `issue_count` and `issue_ids` are added because the columns endpoint
        # has no way of saying either; nothing the endpoint did send is dropped.
        data={
            "project": PROJECT,
            "columns": [{**COLUMN, "issue_count": 1, "issue_ids": [ISSUE_ON_BOARD["id"]]}],
        },
        metadata=("status_code", "column_count", "issue_count"),
    ),
    Contract(path=("project", "column", "create"), args=(*BOARD, "--title", "Working"), payload=COLUMN),
    Contract(path=("project", "column", "list"), args=BOARD, payload=[COLUMN]),
    Contract(path=("project", "column", "issues"), args=(*BOARD, "--column-id", "117"), payload=[ISSUE]),
    Contract(
        path=("project", "issue", "add"),
        args=(*BOARD, "--column-id", "117", "--issue-id", "1873"),
        payload=NO_CONTENT,
        data={},
    ),
    Contract(
        path=("project", "issue", "move"),
        args=(*BOARD, "--column-id", "117", "--issue-id", "1873"),
        payload=NO_CONTENT,
        # The board is walked before the move: an issue with no card on the
        # project has nothing to move, and Gitea reports that as a success.
        routes=BOARD_ROUTES,
        data={},
    ),
    Contract(
        path=("project", "issue", "remove"),
        args=(*BOARD, "--column-id", "117", "--issue-id", "1873"),
        payload=NO_CONTENT,
        data={},
    ),
    # --- watch -------------------------------------------------------------
    Contract(
        path=("watch", "list"),
        args=REPO,
        # The first run records what is there and reports nothing, so the run
        # under test is the second one, which meets a different issue.
        warmup=(("/comments", [COMMENT]), ("", [ISSUE])),
        routes=(("/comments", [COMMENT]), ("", [OTHER_ISSUE])),
        data=[_change(OTHER_ISSUE, "new", "new issue"), _change(ISSUE, "gone", "no longer listed")],
        metadata=(
            "status_code",
            "scopes",
            "baselined_scopes",
            "issue_count",
            "change_count",
            "state_file",
            "dry_run",
        ),
    ),
    Contract(
        path=("watch", "advance"),
        args=REPO,
        # As above, the run under test is the second one: the first records what
        # is there, so this one has a baseline to have moved past.
        warmup=(("/comments", [COMMENT]), ("", [ISSUE])),
        routes=(("/comments", [COMMENT]), ("", [OTHER_ISSUE])),
        # What was recorded, not what changed: the command commits the baseline
        # rather than reporting the difference. `change_count` is how far it
        # moved - the issue that appeared and the one that went away.
        data=[{"scope": WATCH_SCOPE, "issue_count": 1, "change_count": 2, "baselined": False}],
        metadata=(
            "status_code",
            "scopes",
            "baselined_scopes",
            "issue_count",
            "change_count",
            "state_file",
        ),
    ),
)


def write_config(path: Path) -> None:
    """Write the throwaway configuration an invocation is given.

    Two accounts, and the one the commands name is not the default, so that
    resolving the wrong one is a request to a different address with a different
    token rather than the same request by another route.

    Args:
        path: Location to write the configuration to.

    """
    path.write_text(
        yaml.safe_dump(
            {
                "default_account": OTHER,
                "accounts": {
                    ACCOUNT: {"name": ACCOUNT, "base_url": BASE_URL, "token": TOKEN},
                    OTHER: {"name": OTHER, "base_url": OTHER_BASE_URL, "token": OTHER_TOKEN},
                },
            }
        )
    )


def invoke(
    contract: Contract,
    routes: tuple[tuple[str, Any], ...],
    config_path: Path,
    auth: tuple[str, ...],
) -> tuple[Any, RoutedSession]:
    """Run one subcommand in JSON mode against the responses it declared.

    Args:
        contract: The subcommand to run.
        routes: The endpoints to answer, for this invocation.
        config_path: The throwaway configuration to read.
        auth: How the command is told which instance to talk to.

    Returns:
        The result of the invocation, and the session recording what it asked for.

    """
    session = RoutedSession(routes, payload=contract.payload)
    arguments = [
        "--config-path",
        str(config_path),
        "--output",
        "json",
        *contract.path,
        *contract.args,
        *auth,
    ]

    with patch("gitea.client.gitea.requests.Session", return_value=session):
        return runner.invoke(app, arguments), session


def contract_cases() -> list[Any]:
    """Build one case per subcommand and way of authenticating it.

    Returns:
        Every contract, once for each way of authenticating the command: both for
        a command reaching the API, and once with neither for the `config`
        commands, which reach only the configuration file.

    """
    cases = []
    for contract in CONTRACTS:
        name = " ".join(contract.path)
        if not contract.api:
            cases.append(pytest.param(contract, (), id=name))
            continue
        cases.append(pytest.param(contract, ACCOUNT_AUTH, id=f"{name} [account]"))
        cases.append(pytest.param(contract, EXPLICIT_AUTH, id=f"{name} [credentials]"))
    return cases


@pytest.mark.parametrize(("contract", "auth"), contract_cases())
def test_subcommand_emits_the_declared_data(
    contract: Contract, auth: tuple[str, ...], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every subcommand should emit the envelope its contract declares, exactly."""
    monkeypatch.setenv(STATE_FILE_ENV, str(tmp_path / "watch-state.json"))
    config_path = tmp_path / "config.yaml"
    write_config(config_path)

    if contract.warmup is not None:
        warmup, _ = invoke(contract, contract.warmup, config_path, auth)
        assert warmup.exit_code == 0, f"warm-up run failed: {warmup.output!r}"

    result, session = invoke(contract, contract.routes, config_path, auth)

    assert result.exit_code == 0, result.output
    envelope = parse_envelope(result.stdout)

    expected = contract.payload if isinstance(contract.data, Unchanged) else contract.data
    assert envelope["data"] == expected
    assert set(envelope["metadata"]) == set(contract.metadata)

    assert_requests_were_addressed(contract, session)


def assert_requests_were_addressed(contract: Contract, session: RoutedSession) -> None:
    """Check that the command reached the instance it was told to, authenticated.

    The data a command emits is only the API's if the command asked the API the
    caller meant: a request sent to the default instance, or sent without the
    account's token, answers with somebody else's data or with nothing. Neither is
    visible in the envelope when the responses are faked, so it is asserted here.

    A URL is refused when it carries `None` in it, which is what a coordinate the
    command dropped rather than resolved looks like once it is interpolated into a
    path - `/orgs/None/projects/31/columns`. The fake answers such a request as
    readily as the right one, so nothing else would notice.

    Args:
        contract: The subcommand that ran.
        session: The session recording what it asked for.

    Raises:
        AssertionError: If the command reached the API when it had no reason to,
            or reached it at the wrong address, or reached it unauthenticated.

    """
    if not contract.api:
        assert session.requests == [], f"{contract.path} reached the API: {session.urls}"
        return

    assert session.requests, f"{contract.path} made no request"

    for url in session.urls:
        assert url.startswith(API_ROOT), f"{contract.path} asked {url}"
        assert "None" not in url, f"{contract.path} interpolated a missing coordinate: {url}"

    for headers in session.headers:
        assert headers.get("Authorization") == AUTHORIZATION, f"{contract.path} sent {headers}"


def test_every_subcommand_has_a_contract() -> None:
    """Every leaf subcommand should be pinned by an entry above.

    A subcommand without one emits whatever it emits, and the first anyone hears
    of a field having been renamed is a script that stopped working. Add the
    entry rather than an exception here.
    """
    declared = {contract.path for contract in CONTRACTS}
    existing = {path for path, _ in leaf_commands(get_command(app))}

    assert declared == existing


def test_contracts_are_declared_once_each() -> None:
    """No subcommand should be declared twice, which would leave one entry unread."""
    assert len({contract.path for contract in CONTRACTS}) == len(CONTRACTS)


def contract_for(path: tuple[str, ...]) -> Contract:
    """Find the contract of one subcommand.

    Args:
        path: The subcommand, as its words are typed.

    Returns:
        The entry declaring it.

    """
    return next(contract for contract in CONTRACTS if contract.path == path)


def test_a_column_is_emitted_by_its_api_field_name() -> None:
    """A column reaches the JSON output keyed by `title`, and never by `name`.

    The compatibility alias lets a Python caller read `column["name"]`; the point
    of it being an alias rather than a key is that it is not emitted, so no
    consumer of the CLI can come to depend on a name the API does not use.

    The table above would keep passing if a command started emitting `name` and
    its entry were updated to match, so the field name itself is asserted here,
    on every column any command emits.
    """
    columns = [
        contract_for(("project", "column", "create")).payload,
        *contract_for(("project", "column", "list")).payload,
        *(entry["column"] for entry in contract_for(("project", "issues")).data),
        *contract_for(("project", "show")).data["columns"],
    ]

    assert len(columns) == 4
    for column in columns:
        assert "title" in column
        assert "name" not in column
