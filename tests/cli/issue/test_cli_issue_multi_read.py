"""Behavioural tests for reading several issues in one run.

`issue get` takes `--issue-id` repeatedly and `--issue-id-file`, and `issue list`
takes `--issue-ids`. The commands are run against a stand-in for the issue
endpoints of one repository, so what is checked is what a caller sees: which
issues come back, in what order, in what shape, and how many requests it took.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import requests
from typer.testing import CliRunner

from gitea.cli.main import app
from tests.cli.envelope import parse_envelope
from tests.transport import RecordedResponse, RecordingSession

runner = CliRunner()

BASE_URL = "https://gitea.invalid"
API_ROOT = f"{BASE_URL}/api/v1"


def make_issue(number: int, state: str = "open") -> dict[str, Any]:
    """Describe one issue as the API does, as far as these tests read it.

    Args:
        number: The issue number.
        state: The issue's state.

    Returns:
        The issue payload.

    """
    return {"id": 1000 + number, "number": number, "state": state, "title": f"Issue {number}", "projects": []}


class FailedResponse:
    """The answer of an endpoint refusing a request, as far as the client reads it."""

    content = b""

    def __init__(self, status_code: int) -> None:
        """Answer with the given status.

        Args:
            status_code: The status of the refusal.

        """
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Raise as a refused request does, carrying the response as requests does.

        Raises:
            requests.HTTPError: Always.

        """
        raise requests.HTTPError(f"{self.status_code} Client Error", response=self)

    def close(self) -> None:
        """Release the response, as the client does on a failure."""


class IssueServer(RecordingSession):
    """Stand-in for the issue endpoints of one repository."""

    def __init__(self, issues: list[dict[str, Any]], refusing: frozenset[int] = frozenset()) -> None:
        """Start the instance with the given issues, newest first as Gitea lists them.

        Args:
            issues: The issues of the repository.
            refusing: Issues whose endpoint answers 500 rather than the issue.

        """
        super().__init__()
        self.issues = {issue["number"]: issue for issue in issues}
        self.refusing = refusing

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Record a request and answer it as the instance would.

        Args:
            method: HTTP method the client asked for.
            url: Full URL the client built.
            **kwargs: The headers, the query parameters and the body.

        Returns:
            The response.

        """
        self._record(method, url, **kwargs)
        path = url.removeprefix(API_ROOT)
        assert method == "GET", f"unexpected request: {method} {url}"

        if path == "/repos/o/r/issues":
            params = kwargs.get("params") or {}
            state = params.get("state", "open")
            listed = [issue for issue in self.issues.values() if state in ("all", issue["state"])]
            listed.sort(key=lambda issue: -issue["number"])
            page, limit = params.get("page", 1), params.get("limit", 50)
            return RecordedResponse(listed[(page - 1) * limit : page * limit])

        match = re.fullmatch(r"/repos/o/r/issues/(\d+)", path)
        assert match, f"unexpected request: {method} {url}"
        number = int(match.group(1))
        if number in self.refusing:
            return FailedResponse(500)
        if number not in self.issues:
            return FailedResponse(404)
        return RecordedResponse(self.issues[number])

    @property
    def listing_pages(self) -> list[int]:
        """The pages of the issue listing that were asked for.

        Returns:
            The page number of each listing request, in order.

        """
        return [
            params["page"]
            for (_, url), params in zip(self.requests, self.params, strict=True)
            if url == f"{API_ROOT}/repos/o/r/issues"
        ]


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    """An empty configuration, so that nothing is read from the user's own."""
    path = tmp_path / "config.yaml"
    path.write_text("accounts: {}\n")
    return path


def run(server: IssueServer, config_path: Path, *args: str, stdin: str | None = None) -> Any:
    """Run one `issue` command against the stand-in.

    Args:
        server: The stand-in to answer with.
        config_path: The configuration to read.
        *args: The subcommand and its options, after `issue`.
        stdin: Text to feed the command on stdin.

    Returns:
        The result of the invocation.

    """
    arguments = [
        "--config-path",
        str(config_path),
        "--output",
        "json",
        "issue",
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
        return runner.invoke(app, arguments, input=stdin)


def run_failing(server: IssueServer, config_path: Path, *args: str) -> str:
    """Run one `issue` command that has to fail, and read the error it reported.

    Args:
        server: The stand-in to answer with.
        config_path: The configuration to read.
        *args: The subcommand and its options, after `issue`.

    Returns:
        The one error the command reported.

    """
    with patch("gitea.cli.utils.api.logger") as logger:
        result = run(server, config_path, *args)

    assert result.exit_code == 1, result.output
    assert result.stdout == ""
    assert logger.exception.call_args_list == []
    assert len(logger.error.call_args_list) == 1, logger.error.call_args_list
    template, *values = logger.error.call_args.args
    return template % tuple(values)


def numbers(data: list[dict[str, Any]]) -> list[int]:
    """Read the issue numbers of a list of issues, in order.

    Args:
        data: The issues.

    Returns:
        Their numbers.

    """
    return [issue["number"] for issue in data]


REPOSITORY = [make_issue(number, "closed" if number % 2 == 0 else "open") for number in range(1, 8)]


def test_get_with_one_issue_id_emits_the_issue_itself(config_path):
    """One --issue-id keeps the shape the command always had: the issue, not a list of one."""
    server = IssueServer(REPOSITORY)

    result = run(server, config_path, "get", "--issue-id", "3")

    assert result.exit_code == 0, result.output
    assert parse_envelope(result.stdout)["data"] == make_issue(3)


def test_get_with_repeated_issue_ids_emits_them_in_the_order_asked(config_path):
    """Repeated --issue-id should give a list in the requested order, each issue once."""
    server = IssueServer(REPOSITORY)

    result = run(server, config_path, "get", "--issue-id", "5", "--issue-id", "2", "--issue-id", "7", "--issue-id", "5")

    assert result.exit_code == 0, result.output
    envelope = parse_envelope(result.stdout)
    assert numbers(envelope["data"]) == [5, 2, 7]
    assert [issue["state"] for issue in envelope["data"]] == ["open", "closed", "open"]
    assert envelope["metadata"] == {"status_code": 200}
    assert len(server.requests) == 3


def test_get_reads_the_issue_numbers_from_a_file(config_path, tmp_path):
    """--issue-id-file should read numbers separated by commas, spaces and newlines alike."""
    listed = tmp_path / "issues.txt"
    listed.write_text("6\n1, 4\n\n  3\n")
    server = IssueServer(REPOSITORY)

    result = run(server, config_path, "get", "--issue-id-file", str(listed))

    assert result.exit_code == 0, result.output
    assert numbers(parse_envelope(result.stdout)["data"]) == [6, 1, 4, 3]


def test_get_reads_the_issue_numbers_from_stdin(config_path):
    """--issue-id-file - should read the numbers from stdin."""
    server = IssueServer(REPOSITORY)

    result = run(server, config_path, "get", "--issue-id-file", "-", stdin="2\n7\n")

    assert result.exit_code == 0, result.output
    assert numbers(parse_envelope(result.stdout)["data"]) == [2, 7]


def test_get_with_a_file_of_one_issue_still_emits_a_list(config_path, tmp_path):
    """The shape follows the invocation: a file gives a list, however many issues it lists."""
    listed = tmp_path / "issues.txt"
    listed.write_text("4\n")
    server = IssueServer(REPOSITORY)

    result = run(server, config_path, "get", "--issue-id-file", str(listed))

    assert result.exit_code == 0, result.output
    assert parse_envelope(result.stdout)["data"] == [make_issue(4, "closed")]


def test_get_puts_the_issue_ids_before_those_of_the_file(config_path, tmp_path):
    """--issue-id and --issue-id-file combine, the options first and each issue once."""
    listed = tmp_path / "issues.txt"
    listed.write_text("1 6")
    server = IssueServer(REPOSITORY)

    result = run(server, config_path, "get", "--issue-id", "6", "--issue-id-file", str(listed))

    assert result.exit_code == 0, result.output
    assert numbers(parse_envelope(result.stdout)["data"]) == [6, 1]


def test_get_names_every_unknown_issue_and_prints_nothing(config_path):
    """An unknown issue fails the run, naming each missing one after trying them all."""
    server = IssueServer(REPOSITORY)

    error = run_failing(
        server, config_path, "get", "--issue-id", "2", "--issue-id", "40", "--issue-id", "3", "--issue-id", "41"
    )

    assert "no issue 40, 41 in o/r" in error
    assert "the other 2 of the 4 requested exist" in error
    assert len(server.requests) == 4


def test_get_raises_a_failure_other_than_a_missing_issue_as_it_was(config_path):
    """A refusal other than 404 is not reported as a missing issue."""
    server = IssueServer(REPOSITORY, refusing=frozenset({3}))

    with patch("gitea.cli.utils.api.logger") as logger:
        result = run(server, config_path, "get", "--issue-id", "2", "--issue-id", "3")

    assert result.exit_code == 1
    assert result.stdout == ""
    assert logger.error.call_args_list == []
    assert len(logger.exception.call_args_list) == 1


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("", "lists no issue number"),
        ("3, x", "holds 'x', which is not an issue number"),
        ("0", "holds '0', which is not an issue number"),
    ],
)
def test_get_rejects_a_file_without_usable_numbers(config_path, tmp_path, content, expected):
    """An empty file or a value that is not an issue number is an error before any request."""
    listed = tmp_path / "issues.txt"
    listed.write_text(content)
    server = IssueServer(REPOSITORY)

    error = run_failing(server, config_path, "get", "--issue-id-file", str(listed))

    assert expected in error
    assert server.requests == []


def test_get_reports_a_file_it_cannot_read(config_path, tmp_path):
    """A missing file is an error naming it, before any request."""
    server = IssueServer(REPOSITORY)
    missing = tmp_path / "absent.txt"

    error = run_failing(server, config_path, "get", "--issue-id-file", str(missing))

    assert f"could not read --issue-id-file {missing}" in error
    assert server.requests == []


def test_get_without_an_issue_says_how_to_name_one(config_path):
    """Neither --issue-id nor --issue-id-file is an error naming both."""
    error = run_failing(IssueServer(REPOSITORY), config_path, "get")

    assert "--issue-id NUMBER" in error
    assert "--issue-id-file PATH" in error


def test_get_refuses_the_deprecated_index_with_several_issues(config_path):
    """--index names one issue, so combining it with several is an error."""
    error = run_failing(
        IssueServer(REPOSITORY), config_path, "get", "--index", "1", "--issue-id", "2", "--issue-id", "3"
    )

    assert "--index names one issue" in error


def test_get_still_accepts_the_deprecated_index_alone(config_path):
    """--index on its own keeps working, with the single-issue shape."""
    server = IssueServer(REPOSITORY)

    result = run(server, config_path, "get", "--index", "1")

    assert result.exit_code == 0, result.output
    assert parse_envelope(result.stdout)["data"] == make_issue(1)


def test_list_narrowed_to_issue_ids_keeps_the_requested_order_and_the_filters(config_path):
    """--issue-ids keeps only the listed issues, in the order given, and still honours --state."""
    server = IssueServer(REPOSITORY)

    result = run(server, config_path, "list", "--issue-ids", "5,2,1,7")

    assert result.exit_code == 0, result.output
    envelope = parse_envelope(result.stdout)
    # 2 is closed, so the default `--state open` leaves it out, and says so.
    assert numbers(envelope["data"]) == [5, 1, 7]
    assert envelope["metadata"]["not_listed"] == [2]


def test_list_narrowed_to_issue_ids_walks_pages_until_every_issue_is_seen(config_path):
    """The listing is paged only as far as the last requested issue."""
    server = IssueServer([make_issue(number) for number in range(1, 11)])

    result = run(server, config_path, "list", "--state", "all", "--limit", "3", "--issue-ids", "8, 6")

    assert result.exit_code == 0, result.output
    envelope = parse_envelope(result.stdout)
    assert numbers(envelope["data"]) == [8, 6]
    assert envelope["metadata"]["not_listed"] == []
    # Newest first, three a page: [10, 9, 8], [7, 6, 5] - and no further.
    assert server.listing_pages == [1, 2]


def test_list_narrowed_to_issue_ids_reports_an_unknown_issue_as_not_listed(config_path):
    """An issue the listing does not hold is named in not_listed after the whole listing was walked."""
    server = IssueServer(REPOSITORY)

    result = run(server, config_path, "list", "--state", "all", "--limit", "5", "--issue-ids", "3,99")

    assert result.exit_code == 0, result.output
    envelope = parse_envelope(result.stdout)
    assert numbers(envelope["data"]) == [3]
    assert envelope["metadata"]["not_listed"] == [99]
    assert server.listing_pages == [1, 2]


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (("--issue-ids", "1,two"), "holds 'two', which is not an issue number"),
        (("--issue-ids", " , "), "--issue-ids names no issue"),
        (("--issue-ids", "1", "--page", "2"), "--page cannot be combined with it"),
    ],
)
def test_list_rejects_an_unusable_issue_ids_filter(config_path, args, expected):
    """A malformed set, an empty one, or one combined with --page is an error before any request."""
    server = IssueServer(REPOSITORY)

    error = run_failing(server, config_path, "list", *args)

    assert expected in error
    assert server.requests == []


def test_list_without_issue_ids_is_a_single_page_as_before(config_path):
    """Without --issue-ids the listing is the one page asked for, unfiltered."""
    server = IssueServer(REPOSITORY)

    result = run(server, config_path, "list", "--state", "all", "--limit", "3", "--page", "2")

    assert result.exit_code == 0, result.output
    envelope = parse_envelope(result.stdout)
    assert numbers(envelope["data"]) == [4, 3, 2]
    assert "not_listed" not in envelope["metadata"]
