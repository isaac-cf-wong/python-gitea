"""Unit tests for the `gitea-cli watch advance` command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from gitea.cli.main import app
from gitea.cli.watch.advance import format_record
from gitea.watch.changes import comment_hash
from gitea.watch.state import STATE_FILE_ENV
from tests.cli.envelope import parse_envelope
from tests.cli.rendering import unrendered
from tests.cli.watch.support import AUTH, COMMENT, ISSUE, OTHER_ISSUE, logged_error, make_client, run

runner = CliRunner()

# A third issue, for the change that lands between a dry run and the advance
# committing what it reported.
LATE_ISSUE = {
    "id": 1955,
    "number": 17,
    "title": "Bump the pins",
    "updated_at": "2026-08-02T12:00:00Z",
    "assignees": [],
    "labels": [],
    "repository": {"owner": "my-org", "name": "my-repo"},
}


def advance(state_path: Path, *extra: str, output: str | None = None) -> list[str]:
    """Build the arguments of an advance against one repository.

    Args:
        state_path: Path of the cache the run reads and writes.
        *extra: Further arguments to append.
        output: The output format to pass globally, or None for the default.

    Returns:
        The arguments to invoke with.

    """
    globals_ = ["--output", output] if output else []
    return [
        *globals_,
        "watch",
        "advance",
        "--owner",
        "my-org",
        "--repository",
        "my-repo",
        "--state-file",
        str(state_path),
        *AUTH,
        *extra,
    ]


class TestRecording:
    """Tests for what an advance writes to the cache."""

    def test_the_current_state_is_recorded(self, tmp_path: Path) -> None:
        """The point of the command: what is there now becomes what is compared against."""
        state_path = tmp_path / "watch-state.json"

        result = run(*advance(state_path), client=make_client([ISSUE], comments={15: [COMMENT]}))

        assert result.exit_code == 0
        recorded = json.loads(state_path.read_text(encoding="utf-8"))["scopes"]["repo:my-org/my-repo"]["issues"]
        assert recorded["1854"] == {
            "issue_id": 1854,
            "number": 15,
            "title": "Fix the docs",
            "repository": "my-org/my-repo",
            "updated_at": "2026-08-02T10:00:00Z",
            "assignees": ["alice"],
            "labels": ["bug"],
            "comment_hashes": [comment_hash(COMMENT)],
        }

    def test_the_baseline_moves_past_what_had_not_been_reported(self, tmp_path: Path) -> None:
        """A change the cache still holds is consumed, so the next run is quiet."""
        state_path = tmp_path / "watch-state.json"
        run(*advance(state_path), client=make_client([ISSUE]))

        run(*advance(state_path), client=make_client([ISSUE, OTHER_ISSUE]))
        result = run(
            "watch",
            "list",
            "--owner",
            "my-org",
            "--repository",
            "my-repo",
            "--state-file",
            str(state_path),
            *AUTH,
            client=make_client([ISSUE, OTHER_ISSUE]),
        )

        assert result.stdout == ""

    def test_only_the_scopes_advanced_are_touched(self, tmp_path: Path) -> None:
        """Advancing one repository must not drop what another one recorded."""
        state_path = tmp_path / "watch-state.json"
        run(
            "watch",
            "advance",
            "--owner",
            "my-org",
            "--repository",
            "other-repo",
            "--state-file",
            str(state_path),
            *AUTH,
            client=make_client([OTHER_ISSUE]),
        )

        run(*advance(state_path), client=make_client([ISSUE]))

        scopes = json.loads(state_path.read_text(encoding="utf-8"))["scopes"]
        assert sorted(scopes) == ["repo:my-org/my-repo", "repo:my-org/other-repo"]

    def test_a_project_board_can_be_advanced(self, tmp_path: Path) -> None:
        """A board is a scope like any other, and is keyed apart from the repository."""
        state_path = tmp_path / "watch-state.json"

        result = run(
            "watch",
            "advance",
            "--owner",
            "my-org",
            "--project-id",
            "29",
            "--state-file",
            str(state_path),
            *AUTH,
            client=make_client(columns=[{"id": 5, "title": "Working"}], column_issues={5: [ISSUE]}),
        )

        assert result.exit_code == 0
        scopes = json.loads(state_path.read_text(encoding="utf-8"))["scopes"]
        assert list(scopes) == ["project:my-org/29"]
        assert list(scopes["project:my-org/29"]["issues"]) == ["1854"]


class TestReport:
    """Tests for what an advance says about what it recorded."""

    def test_a_first_advance_says_the_scope_was_baselined(self, tmp_path: Path) -> None:
        """There is nothing before a first record for the baseline to have moved past."""
        result = run(*advance(tmp_path / "watch-state.json"), client=make_client([ISSUE]))

        assert result.stdout == "repo:my-org/my-repo: recorded 1 issue, baselined for the first time\n"

    def test_an_advance_over_nothing_new_says_so(self, tmp_path: Path) -> None:
        """A caller committing a cache that had not moved should be told it had not."""
        state_path = tmp_path / "watch-state.json"
        run(*advance(state_path), client=make_client([ISSUE]))

        result = run(*advance(state_path), client=make_client([ISSUE]))

        assert result.stdout == "repo:my-org/my-repo: recorded 1 issue, unchanged since the cache\n"

    def test_an_advance_counts_what_the_baseline_moved_past(self, tmp_path: Path) -> None:
        """The count is what a caller checks against what its dry run reported."""
        state_path = tmp_path / "watch-state.json"
        run(*advance(state_path), client=make_client([ISSUE]))

        result = run(*advance(state_path), client=make_client([ISSUE, OTHER_ISSUE]))

        assert result.stdout == "repo:my-org/my-repo: recorded 2 issues, 1 change baselined\n"

    def test_json_mode_answers_with_the_envelope(self, tmp_path: Path) -> None:
        """A scripted consumer reads the counts rather than parsing the lines."""
        state_path = tmp_path / "watch-state.json"
        run(*advance(state_path), client=make_client([ISSUE]))

        result = run(*advance(state_path, output="json"), client=make_client([ISSUE, OTHER_ISSUE]))

        payload = parse_envelope(result.stdout)
        assert payload["data"] == [
            {
                "scope": "repo:my-org/my-repo",
                "issue_count": 2,
                "change_count": 1,
                "baselined": False,
            }
        ]
        assert payload["metadata"] == {
            "status_code": 200,
            "scopes": ["repo:my-org/my-repo"],
            "baselined_scopes": [],
            "issue_count": 2,
            "change_count": 1,
            "state_file": str(state_path),
        }

    def test_a_first_advance_names_the_baselined_scope_in_the_metadata(self, tmp_path: Path) -> None:
        """`baselined_scopes` is what tells a first record from a moved one."""
        state_path = tmp_path / "watch-state.json"

        result = run(*advance(state_path, output="json"), client=make_client([ISSUE]))

        metadata = parse_envelope(result.stdout)["metadata"]
        assert metadata["baselined_scopes"] == ["repo:my-org/my-repo"]
        assert metadata["change_count"] == 0

    def test_every_scope_advanced_is_reported(self, tmp_path: Path) -> None:
        """One line per scope, so an invocation advancing several says what each did."""
        state_path = tmp_path / "watch-state.json"

        result = run(
            "watch",
            "advance",
            "--owner",
            "my-org",
            "--repository",
            "my-repo",
            "--project-id",
            "29",
            "--state-file",
            str(state_path),
            *AUTH,
            client=make_client([ISSUE], columns=[{"id": 5, "title": "Working"}], column_issues={5: [ISSUE]}),
        )

        assert result.stdout == (
            "repo:my-org/my-repo: recorded 1 issue, baselined for the first time\n"
            "project:my-org/my-repo/29: recorded 1 issue, baselined for the first time\n"
        )


class TestFormatRecord:
    """Tests for the line one scope's record is rendered as."""

    def test_a_single_change_is_phrased_in_the_singular(self) -> None:
        """A digest reading `1 changes` is a digest nobody wrote on purpose."""
        record = {"scope": "repo:o/r", "issue_count": 1, "change_count": 1, "baselined": False}

        assert format_record(record) == "repo:o/r: recorded 1 issue, 1 change baselined"

    def test_several_of_each_are_phrased_in_the_plural(self) -> None:
        """And neither is `2 issue`."""
        record = {"scope": "repo:o/r", "issue_count": 2, "change_count": 3, "baselined": False}

        assert format_record(record) == "repo:o/r: recorded 2 issues, 3 changes baselined"

    def test_an_empty_scope_is_phrased_in_the_plural(self) -> None:
        """Zero is not one, in English or in the rendering."""
        record = {"scope": "repo:o/r", "issue_count": 0, "change_count": 0, "baselined": True}

        assert format_record(record) == "repo:o/r: recorded 0 issues, baselined for the first time"

    def test_a_baselined_scope_never_claims_a_count_of_changes(self) -> None:
        """Nothing was recorded before it, so there is nothing it moved past."""
        record = {"scope": "repo:o/r", "issue_count": 4, "change_count": 0, "baselined": True}

        assert format_record(record) == "repo:o/r: recorded 4 issues, baselined for the first time"


class TestDecouplingDetectionFromConsumption:
    """Tests for the pair this command is one half of."""

    def test_a_dry_run_and_an_advance_report_a_change_once_between_them(self, tmp_path: Path) -> None:
        """Detection and consumption pulled apart: reported by one, consumed by the other."""
        state_path = tmp_path / "watch-state.json"
        run(*_list_args(state_path), client=make_client([ISSUE]))

        reported = run(*_list_args(state_path, "--no-advance"), client=make_client([ISSUE, OTHER_ISSUE]))
        run(*advance(state_path), client=make_client([ISSUE, OTHER_ISSUE]))
        after = run(*_list_args(state_path), client=make_client([ISSUE, OTHER_ISSUE]))

        assert reported.stdout == "my-org/my-repo#16 new: new issue · Ship the release\n"
        assert after.stdout == ""

    def test_a_change_landing_before_the_advance_is_counted_though_never_reported(self, tmp_path: Path) -> None:
        """The window the pair does not close, pinned rather than left to be discovered.

        The advance commits the state of the instance now, not the state the dry
        run saw - there is nothing else left to commit - so an issue that appears
        between the two is baselined without ever being reported. What the caller
        gets is the count: an advance moving past more changes than its dry run
        reported is how the window shows.
        """
        state_path = tmp_path / "watch-state.json"
        run(*_list_args(state_path), client=make_client([ISSUE]))
        reported = run(*_list_args(state_path, "--no-advance", output="json"), client=make_client([ISSUE, OTHER_ISSUE]))

        committed = run(*advance(state_path, output="json"), client=make_client([ISSUE, OTHER_ISSUE, LATE_ISSUE]))
        after = run(*_list_args(state_path), client=make_client([ISSUE, OTHER_ISSUE, LATE_ISSUE]))

        assert parse_envelope(reported.stdout)["metadata"]["change_count"] == 1
        assert parse_envelope(committed.stdout)["metadata"]["change_count"] == 2
        assert after.stdout == ""


class TestFailures:
    """Tests for an advance that could not do what it was asked."""

    def test_a_cache_that_cannot_be_written_fails_the_run(self, tmp_path: Path) -> None:
        """A caller told the baseline moved when it did not would act twice on one change.

        The cache path is a directory here, which no platform lets a file be
        renamed over.
        """
        state_path = tmp_path / "watch-state.json"
        state_path.mkdir()
        (state_path / "occupied").touch()

        with patch("gitea.cli.utils.api.logger") as logger:
            result = run(*advance(state_path), client=make_client([ISSUE]))

        assert result.exit_code == 1
        assert result.stdout == ""
        assert logger.exception.call_count == 0
        assert "Could not write the watch cache at" in logged_error(logger)
        assert [entry.name for entry in state_path.iterdir()] == ["occupied"]

    def test_naming_nothing_to_watch_names_this_command(self, tmp_path: Path) -> None:
        """The refusal should quote the invocation the user typed, not the other one."""
        with patch("gitea.cli.utils.api.logger") as logger:
            result = run(
                "watch",
                "advance",
                "--owner",
                "my-org",
                "--state-file",
                str(tmp_path / "watch-state.json"),
                *AUTH,
            )

        assert result.exit_code == 1
        assert result.stdout == ""
        message = logged_error(logger)
        assert "'gitea-cli watch advance' needs something to watch" in message

    def test_nothing_is_written_when_the_scopes_are_refused(self, tmp_path: Path) -> None:
        """A refused invocation must not leave a cache claiming a scope was recorded."""
        state_path = tmp_path / "watch-state.json"

        run("watch", "advance", "--owner", "my-org", "--state-file", str(state_path), *AUTH)

        assert not state_path.exists()

    def test_an_unreachable_instance_leaves_the_cache_alone(self, tmp_path: Path) -> None:
        """A failed fetch must not record an empty scope as the current state."""
        import requests

        state_path = tmp_path / "watch-state.json"
        run(*advance(state_path), client=make_client([ISSUE]))
        recorded = state_path.read_bytes()

        client = make_client()
        client.issue.list_issues.side_effect = requests.ConnectionError("Connection refused")

        with patch("gitea.cli.utils.api.logger") as logger:
            result = run(*advance(state_path), client=client)

        assert result.exit_code == 1
        assert result.stdout == ""
        assert "Could not reach the Gitea API at https://gitea.invalid" in logged_error(logger)
        assert state_path.read_bytes() == recorded


class TestStateFileOption:
    """Tests for naming the cache."""

    def test_the_environment_names_the_cache_when_the_option_is_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The advance reads the same variable every other watch run does."""
        state_path = tmp_path / "from-the-environment.json"
        monkeypatch.setenv(STATE_FILE_ENV, str(state_path))

        result = run(
            "watch", "advance", "--owner", "my-org", "--repository", "my-repo", *AUTH, client=make_client([ISSUE])
        )

        assert result.exit_code == 0
        assert state_path.exists()


class TestHelp:
    """Tests for how the command presents itself."""

    def test_the_command_is_registered(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`watch advance` should be reachable from the root command."""
        monkeypatch.setenv("COLUMNS", "200")
        result = runner.invoke(app, ["watch", "--help"])

        assert result.exit_code == 0
        assert "advance" in unrendered(result.stdout)


def _list_args(state_path: Path, *extra: str, output: str | None = None) -> list[str]:
    """Build the arguments of a `watch list` run against the same repository.

    Args:
        state_path: Path of the cache the run reads and writes.
        *extra: Further arguments to append.
        output: The output format to pass globally, or None for the default.

    Returns:
        The arguments to invoke with.

    """
    globals_ = ["--output", output] if output else []
    return [
        *globals_,
        "watch",
        "list",
        "--owner",
        "my-org",
        "--repository",
        "my-repo",
        "--state-file",
        str(state_path),
        *AUTH,
        *extra,
    ]
