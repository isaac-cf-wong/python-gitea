"""Contract tests: what every CLI subcommand emits, field for field.

The CLI's JSON envelope is an interface, and the field names in its `data` are the
part of it that changes without anyone deciding to change it. A helper that
rebuilds a payload, a rename that reads better, a field renamed upstream and
mirrored here - each is a one-line edit, none of them fails a test that only
checks that a command ran and printed an envelope, and each of them breaks a
script that was reading the old name (management/weave-workspace#34).

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
from tests.cli.transport import NO_CONTENT, RoutedSession
from tests.cli.tree import leaf_commands

runner = CliRunner()

BASE_URL = "https://gitea.invalid"

# Credentials every command reaching the API is given, so that none of them
# resolves an account from the configuration.
AUTH = ("--token", "stub-token", "--base-url", BASE_URL)

# The account the throwaway configuration carries, for the `config` commands
# acting on an existing one.
ACCOUNT = "seed"


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
        data={"default_account": ACCOUNT, "accounts": [{"name": ACCOUNT, "base_url": BASE_URL}]},
        metadata=("config_path", "account_count"),
        api=False,
    ),
    Contract(
        path=("config", "update"),
        args=("--name", ACCOUNT, "--base-url", "https://other.invalid"),
        data={
            "name": ACCOUNT,
            "base_url": "https://other.invalid",
            "is_default": True,
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
)


def write_config(path: Path) -> None:
    """Write the throwaway configuration an invocation is given.

    Args:
        path: Location to write the configuration to.

    """
    path.write_text(
        yaml.safe_dump(
            {
                "default_account": ACCOUNT,
                "accounts": {ACCOUNT: {"name": ACCOUNT, "base_url": BASE_URL, "token": "seed-token"}},
            }
        )
    )


def invoke(contract: Contract, routes: tuple[tuple[str, Any], ...], config_path: Path) -> Any:
    """Run one subcommand in JSON mode against the responses it declared.

    Args:
        contract: The subcommand to run.
        routes: The endpoints to answer, for this invocation.
        config_path: The throwaway configuration to read.

    Returns:
        The result of the invocation.

    """
    session = RoutedSession(routes, payload=contract.payload)
    arguments = [
        "--config-path",
        str(config_path),
        "--output",
        "json",
        *contract.path,
        *contract.args,
        *(AUTH if contract.api else ()),
    ]

    with patch("gitea.client.gitea.requests.Session", return_value=session):
        return runner.invoke(app, arguments)


@pytest.mark.parametrize("contract", CONTRACTS, ids=[" ".join(entry.path) for entry in CONTRACTS])
def test_subcommand_emits_the_declared_data(
    contract: Contract, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every subcommand should emit the envelope its contract declares, exactly."""
    monkeypatch.setenv(STATE_FILE_ENV, str(tmp_path / "watch-state.json"))
    config_path = tmp_path / "config.yaml"
    write_config(config_path)

    if contract.warmup is not None:
        warmup = invoke(contract, contract.warmup, config_path)
        assert warmup.exit_code == 0, f"warm-up run failed: {warmup.output!r}"

    result = invoke(contract, contract.routes, config_path)

    assert result.exit_code == 0, result.output
    envelope = parse_envelope(result.stdout)

    expected = contract.payload if isinstance(contract.data, Unchanged) else contract.data
    assert envelope["data"] == expected
    assert set(envelope["metadata"]) == set(contract.metadata)


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
    ]

    assert len(columns) == 3
    for column in columns:
        assert "title" in column
        assert "name" not in column
