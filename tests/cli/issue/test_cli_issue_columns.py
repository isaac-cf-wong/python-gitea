"""Behavioural tests for reading issues with and without their board columns.

`issue get` reports the column each issue's card sits in by walking the projects'
boards unless `--no-columns` is passed. The command runs against a stand-in that
records every request it is asked to make, so these tests read what a caller
sees - the project entries of the emitted issue - against what the run cost: the
board requests ARE the walk, and a read that does not resolve columns must make
none of them. Counting the issue requests is the other half of the same claim:
whatever boards the issues are on, such a read is one request per issue.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from gitea.cli.main import app
from tests.cli.envelope import parse_envelope
from tests.transport import RoutedSession

runner = CliRunner()

BASE_URL = "https://gitea.invalid"
API_ROOT = f"{BASE_URL}/api/v1"

ISSUE_GLOBAL_ID = 1854
PROJECT = {"id": 29, "title": "Board", "repo_id": 0, "type": "organization"}
COLUMN_ID = 107
COLUMNS = [{"id": COLUMN_ID, "title": "In Progress"}]
# The column's listing identifies its cards by the issues' global IDs, which is
# how the walk matches a card to the issue whose column is being looked for.
CARD = [{"id": ISSUE_GLOBAL_ID}]


def make_issue(number: int, projects: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Describe one issue as the API does, on the given projects.

    Args:
        number: The issue number.
        projects: The projects the issue is on. Defaults to the one board.

    Returns:
        The issue payload.

    """
    entries = [PROJECT] if projects is None else projects
    return {
        "id": ISSUE_GLOBAL_ID,
        "number": number,
        "state": "open",
        "title": f"Issue {number}",
        "projects": [dict(project) for project in entries],
    }


def make_server(*numbers: int) -> RoutedSession:
    """Build a stand-in answering the given issues and the board their cards sit on.

    The board routes are declared before the issue ones and longest first: a
    route answers the first URL that contains its fragment, and every column
    listing's URL contains the one for the columns.

    Args:
        *numbers: The issue numbers the repository holds.

    Returns:
        The recording session to answer with.

    """
    routes: list[tuple[str, Any]] = [
        (f"/orgs/o/projects/{PROJECT['id']}/columns/{COLUMN_ID}/issues", CARD),
        (f"/orgs/o/projects/{PROJECT['id']}/columns", COLUMNS),
    ]
    routes += [(f"/repos/o/r/issues/{number}", make_issue(number)) for number in numbers]
    return RoutedSession(routes)


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    """An empty configuration, so that nothing is read from the user's own.

    Args:
        tmp_path: The test's temporary directory.

    Returns:
        The path of the configuration to run against.

    """
    path = tmp_path / "config.yaml"
    path.write_text("accounts: {}\n")
    return path


def run(server: RoutedSession, config_path: Path, *args: str) -> Any:
    """Run `issue get` against the stand-in.

    Args:
        server: The stand-in to answer with.
        config_path: The configuration to read.
        *args: The options of `issue get`.

    Returns:
        The result of the invocation.

    """
    arguments = [
        "--config-path",
        str(config_path),
        "--output",
        "json",
        "issue",
        "get",
        *args,
        "--owner",
        "o",
        "--repository",
        "r",
        "--token",
        "t",
        "--base-url",
        BASE_URL,
    ]
    with patch("gitea.client.gitea.requests.Session", return_value=server):
        return runner.invoke(app, arguments)


def board_requests(server: RoutedSession) -> list[str]:
    """The URLs of the requests that walked a board, in order.

    Args:
        server: The stand-in that recorded the requests.

    Returns:
        The board URLs the run asked for.

    """
    return [url for _method, url in server.requests if "/columns" in url]


def test_get_resolves_the_column_of_the_card_by_default(config_path: Path):
    """Without the option, the project entry carries the column the card sits in."""
    server = make_server(3)

    result = run(server, config_path, "--issue-id", "3")

    assert result.exit_code == 0, result.output
    envelope = parse_envelope(result.stdout)
    assert [project["column_id"] for project in envelope["data"]["projects"]] == [COLUMN_ID]
    assert envelope["metadata"] == {"status_code": 200}
    assert board_requests(server) == [
        f"{API_ROOT}/orgs/o/projects/{PROJECT['id']}/columns",
        f"{API_ROOT}/orgs/o/projects/{PROJECT['id']}/columns/{COLUMN_ID}/issues",
    ]


def test_get_with_columns_asks_for_them_explicitly(config_path: Path):
    """--columns is the default spelled out, and resolves them the same way."""
    server = make_server(3)

    result = run(server, config_path, "--columns", "--issue-id", "3")

    assert result.exit_code == 0, result.output
    envelope = parse_envelope(result.stdout)
    assert [project["column_id"] for project in envelope["data"]["projects"]] == [COLUMN_ID]
    assert board_requests(server) == [
        f"{API_ROOT}/orgs/o/projects/{PROJECT['id']}/columns",
        f"{API_ROOT}/orgs/o/projects/{PROJECT['id']}/columns/{COLUMN_ID}/issues",
    ]


def test_get_without_columns_leaves_the_projects_to_the_api(config_path: Path):
    """--no-columns should emit the project entries as the API sent them and read no board."""
    server = make_server(3)

    result = run(server, config_path, "--no-columns", "--issue-id", "3")

    assert result.exit_code == 0, result.output
    envelope = parse_envelope(result.stdout)
    assert envelope["data"]["projects"] == [PROJECT]
    assert "column_id" not in envelope["data"]["projects"][0]
    assert board_requests(server) == []
    assert len(server.requests) == 1


def test_get_without_columns_reads_one_request_per_issue(config_path: Path):
    """--no-columns costs one request per issue, however many boards they are on."""
    server = make_server(3, 5, 7)

    result = run(server, config_path, "--no-columns", "--issue-id", "3", "--issue-id", "5", "--issue-id", "7")

    assert result.exit_code == 0, result.output
    envelope = parse_envelope(result.stdout)
    assert [issue["number"] for issue in envelope["data"]] == [3, 5, 7]
    assert [project for issue in envelope["data"] for project in issue["projects"]] == [PROJECT, PROJECT, PROJECT]
    assert board_requests(server) == []
    assert server.requests == [
        ("GET", f"{API_ROOT}/repos/o/r/issues/3"),
        ("GET", f"{API_ROOT}/repos/o/r/issues/5"),
        ("GET", f"{API_ROOT}/repos/o/r/issues/7"),
    ]


def test_get_without_columns_still_emits_an_issue_without_projects(config_path: Path):
    """An issue on no project is emitted as before, with or without the columns."""
    server = RoutedSession([("/repos/o/r/issues/3", make_issue(3, projects=[]))])

    result = run(server, config_path, "--no-columns", "--issue-id", "3")

    assert result.exit_code == 0, result.output
    assert parse_envelope(result.stdout)["data"]["projects"] == []
