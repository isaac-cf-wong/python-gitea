"""Behavioural tests for the `issue label` commands.

The commands are run against a stand-in for the instance that keeps each issue's
labels as Gitea does: a POST to an issue's labels appends, a PUT replaces them, a
DELETE of the list clears it and a DELETE of one label removes that one. A command
that sent the wrong method would therefore leave the issue with the wrong labels,
which is what these tests look at, rather than only at which method was sent.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import requests
from typer.testing import CliRunner

from gitea.cli.main import app
from tests.cli.envelope import parse_envelope
from tests.transport import NO_CONTENT, RecordedResponse, RecordingSession

runner = CliRunner()

BASE_URL = "https://gitea.invalid"
API_ROOT = f"{BASE_URL}/api/v1"

BUG = {"id": 3, "name": "bug", "color": "ff0000"}
DOCS = {"id": 5, "name": "docs", "color": "00ff00"}
URGENT = {"id": 8, "name": "priority: urgent", "color": "0000ff"}
DEFINED = [BUG, DOCS, URGENT]


class FailedResponse:
    """The answer of an endpoint refusing a request, as far as the client reads it."""

    status_code = 404
    content = b""

    def raise_for_status(self) -> None:
        """Raise as a refused request does.

        Raises:
            requests.HTTPError: Always.

        """
        raise requests.HTTPError("404 Client Error: Not Found")

    def close(self) -> None:
        """Release the response, as the client does on a failure."""


class LabelServer(RecordingSession):
    """Stand-in for the label endpoints of one repository, keeping state between requests."""

    def __init__(
        self,
        carried: dict[int, list[int]],
        defined: list[dict[str, Any]] | None = None,
        failing: frozenset[int] = frozenset(),
    ) -> None:
        """Start the instance with the labels each issue carries.

        Args:
            carried: The IDs of the labels each issue carries, by issue number.
            defined: The labels the repository defines.
            failing: Issues whose label endpoints refuse every request.

        """
        super().__init__()
        self.defined = DEFINED if defined is None else defined
        self.carried = {issue: list(ids) for issue, ids in carried.items()}
        self.failing = failing

    def _labels_of(self, issue: int) -> list[dict[str, Any]]:
        by_id = {label["id"]: label for label in self.defined}
        return [by_id[label_id] for label_id in self.carried[issue]]

    def _ids(self, values: list[int | str]) -> list[int]:
        by_name = {label["name"]: label["id"] for label in self.defined}
        return [value if isinstance(value, int) else by_name[value] for value in values]

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Record a request and answer it as the instance would.

        Args:
            method: HTTP method the client asked for.
            url: Full URL the client built.
            **kwargs: The headers, the query parameters and the JSON body.

        Returns:
            The response.

        Raises:
            AssertionError: If the request reached an endpoint this stand-in does not serve.

        """
        self._record(method, url, **kwargs)
        path = url.removeprefix(API_ROOT)

        if path == "/repos/o/r/labels" and method == "GET":
            params = kwargs.get("params") or {}
            page, limit = params.get("page", 1), params.get("limit", len(self.defined))
            return RecordedResponse(self.defined[(page - 1) * limit : page * limit])

        match = re.fullmatch(r"/repos/o/r/issues/(\d+)/labels(?:/(\d+))?", path)
        assert match, f"unexpected request: {method} {url}"
        issue = int(match.group(1))
        if issue in self.failing:
            return FailedResponse()

        body = kwargs.get("json") or {}
        if match.group(2) is not None:
            assert method == "DELETE", f"unexpected request: {method} {url}"
            label_id = int(match.group(2))
            self.carried[issue] = [i for i in self.carried[issue] if i != label_id]
            return RecordedResponse(NO_CONTENT)
        if method == "POST":
            for label_id in self._ids(body["labels"]):
                if label_id not in self.carried[issue]:
                    self.carried[issue].append(label_id)
        elif method == "PUT":
            self.carried[issue] = self._ids(body["labels"])
        elif method == "DELETE":
            self.carried[issue] = []
            return RecordedResponse(NO_CONTENT)
        return RecordedResponse(self._labels_of(issue))

    @property
    def writes(self) -> list[tuple[str, str]]:
        """The requests that could change an issue's labels.

        Returns:
            Every request made with a method other than GET.

        """
        return [(method, url) for method, url in self.requests if method != "GET"]


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    """An empty configuration, so that nothing is read from the user's own."""
    path = tmp_path / "config.yaml"
    path.write_text("accounts: {}\n")
    return path


def run(server: LabelServer, config_path: Path, *args: str) -> Any:
    """Run one `issue label` command against the stand-in.

    Args:
        server: The stand-in to answer with.
        config_path: The configuration to read.
        *args: The subcommand and its options, after `issue label`.

    Returns:
        The result of the invocation.

    """
    arguments = [
        "--config-path",
        str(config_path),
        "--output",
        "json",
        "issue",
        "label",
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
        # Wide enough that an error logged to the console is not wrapped mid-sentence.
        return runner.invoke(app, arguments, env={"COLUMNS": "500"})


def data_of(result: Any) -> Any:
    """Read the data of a successful invocation's envelope.

    Args:
        result: The result of the invocation.

    Returns:
        The envelope's data.

    """
    assert result.exit_code == 0, result.output
    return parse_envelope(result.stdout)["data"]


def test_list_emits_the_issue_labels(config_path):
    """`list` should emit the labels the issue carries."""
    server = LabelServer({34: [3, 5]})

    assert data_of(run(server, config_path, "list", "--issue-id", "34")) == [BUG, DOCS]


def test_add_keeps_the_labels_the_issue_already_has(config_path):
    """`add` should leave the issue's other labels on it, and emit all of them."""
    server = LabelServer({34: [3]})

    data = data_of(run(server, config_path, "add", "--issue-id", "34", "--label", "5"))

    assert server.carried[34] == [3, 5]
    assert data == [BUG, DOCS]
    assert server.writes == [("POST", f"{API_ROOT}/repos/o/r/issues/34/labels")]


def test_add_resolves_names_to_ids(config_path):
    """A name should reach the API as its label's ID, not as the name."""
    server = LabelServer({34: []})

    data = data_of(run(server, config_path, "add", "--issue-id", "34", "--label", "priority: urgent", "--label", "3"))

    assert server.bodies[-1] == {"labels": [8, 3]}
    assert data == [URGENT, BUG]


def test_add_resolves_a_name_on_a_later_page_of_the_listing(config_path):
    """A name should be found wherever it sits in the repository's labels, not only on the first page."""
    many = [{"id": 100 + i, "name": f"label-{i}", "color": "cccccc"} for i in range(60)]
    server = LabelServer({34: []}, defined=many)

    data_of(run(server, config_path, "add", "--issue-id", "34", "--label", "label-59"))

    assert server.bodies[-1] == {"labels": [159]}


def test_a_numeric_label_is_sent_as_an_id_without_listing_the_labels(config_path):
    """A numeric value is an ID, which needs no lookup and may name an organization label."""
    server = LabelServer({34: []}, defined=[{"id": 900, "name": "org-wide", "color": "cccccc"}])

    data_of(run(server, config_path, "add", "--issue-id", "34", "--label", "900"))

    assert server.requests[0] == ("POST", f"{API_ROOT}/repos/o/r/issues/34/labels")
    assert server.bodies[0] == {"labels": [900]}


@pytest.mark.parametrize("command", ["add", "set", "remove"])
def test_an_unknown_name_is_an_error_and_nothing_is_written(config_path, command):
    """An unknown name should fail the command before any issue is changed."""
    server = LabelServer({34: [3], 35: [3]})

    result = run(server, config_path, command, "--issue-id", "34", "--issue-id", "35", "--label", "5", "--label", "Bug")

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "no label named 'Bug' in o/r" in result.output
    assert "Traceback" not in result.output
    assert server.writes == []
    assert server.carried == {34: [3], 35: [3]}


def test_a_name_shared_by_two_labels_is_an_error(config_path):
    """A name two labels share could mean either, so the command should refuse it."""
    twins = [BUG, {**DOCS, "name": "bug"}]
    server = LabelServer({34: []}, defined=twins)

    result = run(server, config_path, "add", "--issue-id", "34", "--label", "bug")

    assert result.exit_code == 1
    assert "more than one label" in result.output
    assert server.writes == []


def test_remove_takes_off_only_the_given_label(config_path):
    """`remove` should take the named label off and leave the rest."""
    server = LabelServer({34: [3, 5, 8]})

    data = data_of(run(server, config_path, "remove", "--issue-id", "34", "--label", "docs"))

    assert server.carried[34] == [3, 8]
    assert data == [BUG, URGENT]
    assert server.writes == [("DELETE", f"{API_ROOT}/repos/o/r/issues/34/labels/5")]


def test_remove_of_a_label_the_issue_does_not_carry_changes_nothing_and_says_so(config_path):
    """A label not on the issue should be left alone, succeed, and be named in the metadata."""
    server = LabelServer({34: [3]})

    result = run(server, config_path, "remove", "--issue-id", "34", "--label", "docs")

    assert result.exit_code == 0, result.output
    envelope = parse_envelope(result.stdout)
    assert envelope["data"] == [BUG]
    assert envelope["metadata"]["not_on_issue"] == [5]
    assert server.writes == []
    assert server.carried[34] == [3]


def test_set_replaces_every_label(config_path):
    """`set` should leave the issue with exactly the given labels."""
    server = LabelServer({34: [3, 5]})

    data = data_of(run(server, config_path, "set", "--issue-id", "34", "--label", "priority: urgent"))

    assert server.carried[34] == [8]
    assert data == [URGENT]


def test_clear_removes_every_label(config_path):
    """`clear` should leave the issue without labels, and emit the empty list read back."""
    server = LabelServer({34: [3, 5]})

    data = data_of(run(server, config_path, "clear", "--issue-id", "34"))

    assert server.carried[34] == []
    assert data == []


@pytest.mark.parametrize("command", ["add", "set", "remove"])
def test_a_command_writing_labels_needs_one(config_path, command):
    """Without a --label there is nothing to write, which should be an error rather than a no-op."""
    server = LabelServer({34: [3]})

    result = run(server, config_path, command, "--issue-id", "34")

    assert result.exit_code == 1
    assert "--label" in result.output
    assert server.requests == []


@pytest.mark.parametrize("command", ["list", "add", "set", "remove", "clear"])
def test_every_command_needs_an_issue(config_path, command):
    """Without an --issue-id there is no issue to act on."""
    server = LabelServer({})

    labels = ("--label", "3") if command in {"add", "set", "remove"} else ()

    result = run(server, config_path, command, *labels)

    assert result.exit_code == 1
    assert "--issue-id" in result.output
    assert server.requests == []


def test_several_issues_are_each_labelled_and_reported_by_number(config_path):
    """With several --issue-id, each issue should be changed and reported under its own number."""
    server = LabelServer({34: [3], 35: [], 36: [5]})

    data = data_of(
        run(server, config_path, "add", "--issue-id", "34", "--issue-id", "35", "--issue-id", "36", "--label", "docs")
    )

    assert server.carried == {34: [3, 5], 35: [5], 36: [5]}
    assert data == [
        {"issue_id": 34, "labels": [BUG, DOCS]},
        {"issue_id": 35, "labels": [DOCS]},
        {"issue_id": 36, "labels": [DOCS]},
    ]


def test_several_issues_report_absent_labels_per_issue(config_path):
    """With several issues, a label one of them lacks should be named on that issue's entry."""
    server = LabelServer({34: [5], 35: []})

    data = data_of(run(server, config_path, "remove", "--issue-id", "34", "--issue-id", "35", "--label", "docs"))

    assert data == [
        {"issue_id": 34, "labels": [], "not_on_issue": []},
        {"issue_id": 35, "labels": [], "not_on_issue": [5]},
    ]


def test_a_failure_part_way_names_the_issues_already_done(config_path):
    """A failure on a later issue should say which issues were already changed."""
    server = LabelServer({34: [], 35: [], 36: []}, failing=frozenset({35}))

    result = run(
        server, config_path, "add", "--issue-id", "34", "--issue-id", "35", "--issue-id", "36", "--label", "docs"
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "failed on issue 35" in result.output
    assert "Issues 34 were already done" in result.output
    assert server.carried == {34: [5], 35: [], 36: []}


def test_output_is_one_envelope(config_path):
    """The command should print the envelope and nothing else on stdout."""
    server = LabelServer({34: [3]})

    result = run(server, config_path, "list", "--issue-id", "34")

    assert json.loads(result.stdout) == {"data": [BUG], "metadata": {"status_code": 200}}
