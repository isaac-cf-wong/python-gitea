"""Unit tests for the `gitea-cli watch list` command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from gitea.cli.main import app
from gitea.cli.watch.list import build_scopes
from gitea.utils.pagination import PAGE_SIZE
from gitea.watch.changes import comment_hash
from gitea.watch.state import STATE_FILE_ENV
from tests.cli.envelope import parse_envelope
from tests.cli.rendering import unrendered
from tests.cli.transport import RecordingSession

runner = CliRunner()

AUTH = ["--token", "tok", "--base-url", "https://gitea.invalid"]

ISSUE = {
    "id": 1854,
    "number": 15,
    "title": "Fix the docs",
    "updated_at": "2026-08-02T10:00:00Z",
    "assignees": [{"login": "alice"}],
    "labels": [{"name": "bug"}],
    "repository": {"owner": "my-org", "name": "my-repo"},
}

OTHER_ISSUE = {
    "id": 1900,
    "number": 16,
    "title": "Ship the release",
    "updated_at": "2026-08-02T11:00:00Z",
    "assignees": [],
    "labels": [],
    "repository": {"owner": "my-org", "name": "my-repo"},
}

COMMENT = {
    "id": 7,
    "body": "Looks right to me",
    "user": {"login": "alice"},
    "created_at": "2026-08-01T09:00:00Z",
    "updated_at": "2026-08-01T09:00:00Z",
}


def paged(*pages: list[dict[str, Any]]):
    """Build a side effect serving one page of a listing per requested page number.

    Args:
        *pages: The items of each page, in order.

    Returns:
        A side effect returning the requested page, or an empty page beyond the last one.

    """

    def _side_effect(**kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        page = kwargs.get("page", 1)
        return (list(pages[page - 1]) if page <= len(pages) else [], {"status_code": 200})

    return _side_effect


def paged_by(key: str, pages_by_value: dict[Any, list[list[dict[str, Any]]]]):
    """Build a side effect serving the pages recorded for one value of an argument.

    Args:
        key: The keyword argument selecting which listing is being paged.
        pages_by_value: Mapping of that argument's value to that listing's pages.

    Returns:
        A side effect returning the requested page, or an empty page beyond the last one.

    """

    def _side_effect(**kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        pages = pages_by_value.get(kwargs[key], [])
        page = kwargs.get("page", 1)
        return (list(pages[page - 1]) if page <= len(pages) else [], {"status_code": 200})

    return _side_effect


def make_client(
    issues: list[dict[str, Any]] | None = None,
    comments: dict[int, list[dict[str, Any]]] | None = None,
    columns: list[dict[str, Any]] | None = None,
    column_issues: dict[int, list[dict[str, Any]]] | None = None,
) -> MagicMock:
    """Build a client answering the listings a watch run walks.

    Args:
        issues: The open issues of every repository.
        comments: The comments of each issue, keyed by issue number.
        columns: The columns of every project.
        column_issues: The issues of each column, keyed by column ID.

    Returns:
        The client.

    """
    client = MagicMock()
    client.issue.list_issues.side_effect = paged(issues or [])
    client.comment.list_comments.side_effect = paged_by(
        "index", {number: [page] for number, page in (comments or {}).items()}
    )
    client.project.list_project_columns.side_effect = paged(columns or [])
    client.project.list_project_column_issues.side_effect = paged_by(
        "column_id", {column_id: [page] for column_id, page in (column_issues or {}).items()}
    )
    return client


def run(*arguments: str, client: MagicMock | None = None):
    """Invoke the CLI against a stubbed client.

    Args:
        *arguments: The arguments to invoke with.
        client: The client every command in this invocation talks to.

    Returns:
        The result of the invocation.

    """
    with patch("gitea.client.gitea.Gitea") as gitea:
        gitea.return_value.__enter__.return_value = client if client is not None else make_client()
        return runner.invoke(app, list(arguments))


def watch(state_path: Path, *extra: str, output: str | None = None) -> list[str]:
    """Build the arguments of a watch run against one repository.

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


def logged_error(logger: MagicMock) -> str:
    """Read the message of the single error a failed run logged.

    Asserting on the rendered stderr would make the assertion depend on the
    terminal, since `RichHandler` lays a record out as a table and appends the
    emitting frame to it; the record itself is what the CLI wrote.

    Args:
        logger: The patched logger of the module reporting the failure.

    Returns:
        The logged message with its arguments interpolated.

    """
    template, *arguments = logger.error.call_args.args
    return str(template) % tuple(arguments)


class TestBuildScopes:
    """Tests for working out what a run watches from the options naming it."""

    def test_every_repository_named_is_a_scope(self) -> None:
        """Repeating `--repository` should watch each of them."""
        scopes = build_scopes("my-org", ["one", "two"], [])

        assert [scope.key for scope in scopes] == ["repo:my-org/one", "repo:my-org/two"]
        assert [scope.repository for scope in scopes] == ["one", "two"]
        assert [scope.project_id for scope in scopes] == [None, None]

    def test_a_project_without_a_repository_belongs_to_the_owner(self) -> None:
        """Omitting `--repository` should watch the organization's own project."""
        scopes = build_scopes("my-org", [], [29])

        assert [scope.key for scope in scopes] == ["project:my-org/29"]
        assert scopes[0].repository is None
        assert scopes[0].project_id == 29

    def test_a_project_is_resolved_against_the_single_repository_named(self) -> None:
        """A repository project should be keyed apart from the organization's."""
        scopes = build_scopes("my-org", ["my-repo"], [29])

        assert [scope.key for scope in scopes] == ["repo:my-org/my-repo", "project:my-org/my-repo/29"]
        assert scopes[1].repository == "my-repo"

    def test_watching_nothing_names_the_options_to_pass(self) -> None:
        """A run with no scope should say what to name, not watch nothing quietly."""
        from gitea.cli.utils.errors import CommandError

        with pytest.raises(CommandError, match="needs something to watch"):
            build_scopes("my-org", [], [])

    def test_a_project_cannot_be_resolved_against_several_repositories(self) -> None:
        """Two repositories leave no single scope for a project ID to belong to."""
        from gitea.cli.utils.errors import CommandError

        with pytest.raises(CommandError, match="cannot resolve --project-id against 2 repositories"):
            build_scopes("my-org", ["one", "two"], [29])


class TestBaseline:
    """Tests for the first run against a scope."""

    def test_the_first_run_prints_nothing(self, tmp_path: Path) -> None:
        """A repository already full of issues should not all be reported at once."""
        state_path = tmp_path / "watch-state.json"

        result = run(*watch(state_path), client=make_client([ISSUE, OTHER_ISSUE], comments={15: [COMMENT], 16: []}))

        assert result.exit_code == 0
        assert result.stdout == ""

    def test_the_first_run_records_the_scope(self, tmp_path: Path) -> None:
        """What was baselined has to be written down, or nothing is ever a delta."""
        state_path = tmp_path / "watch-state.json"

        run(*watch(state_path), client=make_client([ISSUE], comments={15: [COMMENT]}))

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

    def test_the_baselined_scope_is_named_in_the_metadata(self, tmp_path: Path) -> None:
        """A silent run should still say why it was silent."""
        result = run(*watch(tmp_path / "watch-state.json", output="json"), client=make_client([ISSUE]))

        metadata = parse_envelope(result.stdout)["metadata"]
        assert metadata["baselined_scopes"] == ["repo:my-org/my-repo"]
        assert metadata["issue_count"] == 1
        assert metadata["change_count"] == 0


class TestNoChange:
    """Tests for the tick this command exists to make cheap."""

    def test_a_run_with_nothing_changed_prints_nothing_at_all(self, tmp_path: Path) -> None:
        """Empty stdout on a quiet tick is what lets cron run this for free."""
        state_path = tmp_path / "watch-state.json"
        arguments = watch(state_path)

        run(*arguments, client=make_client([ISSUE], comments={15: [COMMENT]}))
        result = run(*arguments, client=make_client([ISSUE], comments={15: [COMMENT]}))

        assert result.exit_code == 0
        assert result.stdout == ""

    def test_json_mode_still_answers_with_the_envelope(self, tmp_path: Path) -> None:
        """A scripted consumer should get the same shape whether or not anything moved."""
        state_path = tmp_path / "watch-state.json"
        run(*watch(state_path), client=make_client([ISSUE]))

        result = run(*watch(state_path, output="json"), client=make_client([ISSUE]))

        payload = parse_envelope(result.stdout)
        assert payload["data"] == []
        assert payload["metadata"]["change_count"] == 0


class TestReportedChanges:
    """Tests for what a run reports once the scope has been recorded."""

    def test_a_new_issue_is_reported(self, tmp_path: Path) -> None:
        """An issue opened since the last run is the plainest change there is."""
        state_path = tmp_path / "watch-state.json"
        run(*watch(state_path), client=make_client([ISSUE]))

        result = run(*watch(state_path), client=make_client([ISSUE, OTHER_ISSUE]))

        assert result.stdout == "my-org/my-repo#16 new: new issue · Ship the release\n"

    def test_an_assignee_change_is_reported(self, tmp_path: Path) -> None:
        """Handing an issue over should reach the digest."""
        state_path = tmp_path / "watch-state.json"
        run(*watch(state_path), client=make_client([ISSUE]))

        reassigned = {**ISSUE, "assignees": [{"login": "bob"}]}
        result = run(*watch(state_path), client=make_client([reassigned]))

        assert result.stdout == "my-org/my-repo#15 assignees: +bob -alice · Fix the docs\n"

    def test_a_label_change_is_reported(self, tmp_path: Path) -> None:
        """Labelling an issue should reach the digest."""
        state_path = tmp_path / "watch-state.json"
        run(*watch(state_path), client=make_client([ISSUE]))

        relabelled = {**ISSUE, "labels": [{"name": "bug"}, {"name": "urgent"}]}
        result = run(*watch(state_path), client=make_client([relabelled]))

        assert result.stdout == "my-org/my-repo#15 labels: +urgent · Fix the docs\n"

    def test_a_new_comment_is_reported(self, tmp_path: Path) -> None:
        """The change most worth watching for is someone answering."""
        state_path = tmp_path / "watch-state.json"
        run(*watch(state_path), client=make_client([ISSUE], comments={15: [COMMENT]}))

        answered = {**COMMENT, "id": 8, "body": "On it", "user": {"login": "bob"}}
        result = run(*watch(state_path), client=make_client([ISSUE], comments={15: [COMMENT, answered]}))

        assert result.stdout == "my-org/my-repo#15 comments: 1 new · Fix the docs\n"

    def test_an_edited_comment_is_reported_as_a_change(self, tmp_path: Path) -> None:
        """A comment rewritten in place is not the comment that was recorded."""
        state_path = tmp_path / "watch-state.json"
        run(*watch(state_path), client=make_client([ISSUE], comments={15: [COMMENT]}))

        edited = {**COMMENT, "body": "Actually, no", "updated_at": "2026-08-03T09:00:00Z"}
        result = run(*watch(state_path), client=make_client([ISSUE], comments={15: [edited]}))

        assert result.stdout == "my-org/my-repo#15 comments: 1 new, 1 removed · Fix the docs\n"

    def test_an_issue_of_the_watched_repository_needs_no_repository_in_its_payload(self, tmp_path: Path) -> None:
        """A repository scope already knows which repository its issues live in.

        The payload of an issue listed under a repository need not repeat it, so
        the scope is the fallback: without it the comments would not be listed at
        all and the change would go unreported.
        """
        state_path = tmp_path / "watch-state.json"
        bare = {key: value for key, value in ISSUE.items() if key != "repository"}
        run(*watch(state_path), client=make_client([bare], comments={15: [COMMENT]}))

        answered = {**COMMENT, "id": 8, "body": "On it", "user": {"login": "bob"}}
        client = make_client([bare], comments={15: [COMMENT, answered]})
        result = run(*watch(state_path), client=client)

        assert result.stdout == "my-org/my-repo#15 comments: 1 new · Fix the docs\n"
        assert client.comment.list_comments.call_args_list[0].kwargs["owner"] == "my-org"
        assert client.comment.list_comments.call_args_list[0].kwargs["repository"] == "my-repo"

    def test_an_issue_that_left_the_scope_is_reported(self, tmp_path: Path) -> None:
        """An issue closed since the last run drops out of the listing."""
        state_path = tmp_path / "watch-state.json"
        run(*watch(state_path), client=make_client([ISSUE, OTHER_ISSUE]))

        result = run(*watch(state_path), client=make_client([ISSUE]))

        assert result.stdout == "my-org/my-repo#16 gone: no longer listed · Ship the release\n"

    def test_an_issue_that_changed_twice_is_reported_twice(self, tmp_path: Path) -> None:
        """Each change gets its own line, in a fixed order."""
        state_path = tmp_path / "watch-state.json"
        run(*watch(state_path), client=make_client([ISSUE]))

        moved = {**ISSUE, "assignees": [], "labels": []}
        result = run(*watch(state_path), client=make_client([moved]))

        assert result.stdout.splitlines() == [
            "my-org/my-repo#15 assignees: -alice · Fix the docs",
            "my-org/my-repo#15 labels: -bug · Fix the docs",
        ]

    def test_the_json_envelope_carries_the_changes_and_the_run(self, tmp_path: Path) -> None:
        """The scripted digest should say what changed, where, and against what."""
        state_path = tmp_path / "watch-state.json"
        run(*watch(state_path), client=make_client([ISSUE]))

        result = run(*watch(state_path, output="json"), client=make_client([ISSUE, OTHER_ISSUE]))

        payload = parse_envelope(result.stdout)
        assert payload["data"] == [
            {
                "scope": "repo:my-org/my-repo",
                "kind": "new",
                "issue_id": 1900,
                "number": 16,
                "title": "Ship the release",
                "repository": "my-org/my-repo",
                "detail": "new issue",
                "added": [],
                "removed": [],
            }
        ]
        assert payload["metadata"] == {
            "status_code": 200,
            "scopes": ["repo:my-org/my-repo"],
            "baselined_scopes": [],
            "issue_count": 2,
            "change_count": 1,
            "state_file": str(state_path),
            "dry_run": False,
        }


class TestIdempotence:
    """Tests for a change being reported once, and for the flag that suspends that."""

    def test_a_reported_change_is_not_reported_again(self, tmp_path: Path) -> None:
        """The cache is updated by the run that reports, so the next one is quiet."""
        state_path = tmp_path / "watch-state.json"
        run(*watch(state_path), client=make_client([ISSUE]))
        first = run(*watch(state_path), client=make_client([ISSUE, OTHER_ISSUE]))

        second = run(*watch(state_path), client=make_client([ISSUE, OTHER_ISSUE]))

        assert first.stdout != ""
        assert second.stdout == ""

    def test_a_dry_run_leaves_the_cache_byte_for_byte(self, tmp_path: Path) -> None:
        """`--dry-run` has to touch nothing, not merely record the same thing again."""
        state_path = tmp_path / "watch-state.json"
        run(*watch(state_path), client=make_client([ISSUE]))
        recorded = state_path.read_bytes()

        run(*watch(state_path, "--dry-run"), client=make_client([ISSUE, OTHER_ISSUE]))

        assert state_path.read_bytes() == recorded

    def test_a_dry_run_still_reports(self, tmp_path: Path) -> None:
        """Leaving the cache alone is not the same as reporting nothing."""
        state_path = tmp_path / "watch-state.json"
        run(*watch(state_path), client=make_client([ISSUE]))

        result = run(*watch(state_path, "--dry-run"), client=make_client([ISSUE, OTHER_ISSUE]))

        assert result.stdout == "my-org/my-repo#16 new: new issue · Ship the release\n"

    def test_a_change_seen_by_a_dry_run_comes_back_on_the_next_run(self, tmp_path: Path) -> None:
        """Nothing is consumed by a dry run, which is the point of it."""
        state_path = tmp_path / "watch-state.json"
        run(*watch(state_path), client=make_client([ISSUE]))
        run(*watch(state_path, "--dry-run"), client=make_client([ISSUE, OTHER_ISSUE]))

        result = run(*watch(state_path), client=make_client([ISSUE, OTHER_ISSUE]))

        assert result.stdout == "my-org/my-repo#16 new: new issue · Ship the release\n"

    def test_a_dry_run_says_so_in_the_metadata(self, tmp_path: Path) -> None:
        """A scripted consumer should be able to tell the two modes apart."""
        state_path = tmp_path / "watch-state.json"

        result = run(*watch(state_path, "--dry-run", output="json"), client=make_client([ISSUE]))

        assert parse_envelope(result.stdout)["metadata"]["dry_run"] is True
        assert not state_path.exists()


class TestSeveralScopes:
    """Tests for watching more than one thing in one invocation."""

    def test_each_repository_is_cached_apart_from_the_others(self, tmp_path: Path) -> None:
        """A digest across repositories must not report one repository's issues as another's."""
        state_path = tmp_path / "watch-state.json"
        arguments = [
            "--output",
            "json",
            "watch",
            "list",
            "--owner",
            "my-org",
            "--repository",
            "one",
            "--repository",
            "two",
            "--state-file",
            str(state_path),
            *AUTH,
        ]

        run(*arguments, client=make_client([ISSUE]))
        result = run(*arguments, client=make_client([ISSUE]))

        payload = parse_envelope(result.stdout)
        assert payload["metadata"]["scopes"] == ["repo:my-org/one", "repo:my-org/two"]
        # The same issue is in both scopes; neither may report it as new, and
        # the second scope's baseline may not be answered by the first's cache.
        assert payload["data"] == []
        assert payload["metadata"]["issue_count"] == 2
        assert set(json.loads(state_path.read_text(encoding="utf-8"))["scopes"]) == {
            "repo:my-org/one",
            "repo:my-org/two",
        }

    def test_a_scope_added_later_is_baselined_on_its_own(self, tmp_path: Path) -> None:
        """Widening the watch should not announce everything in the new scope."""
        state_path = tmp_path / "watch-state.json"
        run(*watch(state_path), client=make_client([ISSUE]))

        widened = [
            "--output",
            "json",
            "watch",
            "list",
            "--owner",
            "my-org",
            "--repository",
            "my-repo",
            "--repository",
            "other",
            "--state-file",
            str(state_path),
            *AUTH,
        ]
        result = run(*widened, client=make_client([ISSUE]))

        payload = parse_envelope(result.stdout)
        assert payload["metadata"]["baselined_scopes"] == ["repo:my-org/other"]
        assert payload["data"] == []

    def test_a_change_names_the_scope_it_was_seen_in(self, tmp_path: Path) -> None:
        """A multi-scope digest has to say which scope each change came from."""
        state_path = tmp_path / "watch-state.json"
        arguments = [
            "--output",
            "json",
            "watch",
            "list",
            "--owner",
            "my-org",
            "--repository",
            "one",
            "--project-id",
            "29",
            "--state-file",
            str(state_path),
            *AUTH,
        ]
        columns = [{"id": 5, "title": "Todo"}]

        run(*arguments, client=make_client([ISSUE], columns=columns, column_issues={5: [ISSUE]}))
        result = run(
            *arguments,
            client=make_client([ISSUE, OTHER_ISSUE], columns=columns, column_issues={5: [ISSUE]}),
        )

        payload = parse_envelope(result.stdout)
        assert [(change["scope"], change["number"]) for change in payload["data"]] == [("repo:my-org/one", 16)]
        assert payload["metadata"]["scopes"] == ["repo:my-org/one", "project:my-org/one/29"]


class TestProjectScope:
    """Tests for watching a board rather than a repository."""

    def test_every_column_of_the_board_is_walked(self, tmp_path: Path) -> None:
        """A card in any column is on the board, whichever column it sits in."""
        state_path = tmp_path / "watch-state.json"
        arguments = [
            "--output",
            "json",
            "watch",
            "list",
            "--owner",
            "my-org",
            "--project-id",
            "29",
            "--state-file",
            str(state_path),
            *AUTH,
        ]
        client = make_client(
            columns=[{"id": 5, "title": "Todo"}, {"id": 6, "title": "Done"}],
            column_issues={5: [ISSUE], 6: [OTHER_ISSUE]},
        )

        result = run(*arguments, client=client)

        assert parse_envelope(result.stdout)["metadata"]["issue_count"] == 2
        assert [call.kwargs["column_id"] for call in client.project.list_project_column_issues.call_args_list] == [
            5,
            5,
            6,
            6,
        ]
        assert client.issue.list_issues.call_count == 0

    def test_a_column_without_a_usable_id_is_skipped(self, tmp_path: Path) -> None:
        """A malformed column should not fail the board it is on."""
        client = make_client(
            columns=[{"title": "Nameless"}, {"id": 6, "title": "Done"}],
            column_issues={6: [OTHER_ISSUE]},
        )

        result = run(
            "--output",
            "json",
            "watch",
            "list",
            "--owner",
            "my-org",
            "--project-id",
            "29",
            "--state-file",
            str(tmp_path / "watch-state.json"),
            *AUTH,
            client=client,
        )

        assert result.exit_code == 0
        assert parse_envelope(result.stdout)["metadata"]["issue_count"] == 1

    def test_a_card_names_the_repository_holding_it(self, tmp_path: Path) -> None:
        """A board holds cards from any repository, so the card's own payload decides."""
        state_path = tmp_path / "watch-state.json"
        arguments = [
            "watch",
            "list",
            "--owner",
            "my-org",
            "--project-id",
            "29",
            "--state-file",
            str(state_path),
            *AUTH,
        ]
        elsewhere = {**OTHER_ISSUE, "repository": {"owner": "other-org", "name": "other-repo"}}
        columns = [{"id": 5, "title": "Todo"}]

        run(*arguments, client=make_client(columns=columns, column_issues={5: [ISSUE]}))
        client = make_client(columns=columns, column_issues={5: [ISSUE, elsewhere]})
        result = run(*arguments, client=client)

        assert result.stdout == "other-org/other-repo#16 new: new issue · Ship the release\n"
        # The comments of a card are listed under the repository holding it,
        # not under the owner of the board.
        assert {
            (call.kwargs["owner"], call.kwargs["repository"], call.kwargs["index"])
            for call in client.comment.list_comments.call_args_list
        } == {("my-org", "my-repo", 15), ("other-org", "other-repo", 16)}

    def test_a_card_naming_half_a_repository_names_none(self, tmp_path: Path) -> None:
        """Half a repository is not one, and must not be listed against.

        Taking the half that is there would build a request against an owner of
        `None`, which is worse than not reading the comments at all.
        """
        client = make_client(
            columns=[{"id": 5, "title": "Todo"}],
            column_issues={5: [{**ISSUE, "repository": {"name": "other-repo"}}]},
        )

        result = run(
            "--output",
            "json",
            "watch",
            "list",
            "--owner",
            "my-org",
            "--project-id",
            "29",
            "--state-file",
            str(tmp_path / "watch-state.json"),
            *AUTH,
            client=client,
        )

        assert result.exit_code == 0
        assert parse_envelope(result.stdout)["metadata"]["issue_count"] == 1
        assert client.comment.list_comments.call_count == 0

    def test_a_card_of_an_unnamed_repository_is_still_watched(self, tmp_path: Path) -> None:
        """A payload that names no repository costs the comments, not the issue."""
        client = make_client(
            columns=[{"id": 5, "title": "Todo"}],
            column_issues={5: [{key: value for key, value in ISSUE.items() if key != "repository"}]},
        )

        result = run(
            "--output",
            "json",
            "watch",
            "list",
            "--owner",
            "my-org",
            "--project-id",
            "29",
            "--state-file",
            str(tmp_path / "watch-state.json"),
            *AUTH,
            client=client,
        )

        assert result.exit_code == 0
        assert parse_envelope(result.stdout)["metadata"]["issue_count"] == 1
        assert client.comment.list_comments.call_count == 0


class TestRequests:
    """Tests for the endpoints a run actually reaches."""

    def test_each_scope_reaches_the_endpoint_it_names(self, tmp_path: Path) -> None:
        """A scope that resolved to the wrong URL would watch the wrong thing.

        Standing in at the session the client builds its URLs for keeps the path
        building under test, which a client stub answering every endpoint alike
        would not.
        """
        session = RecordingSession()

        with patch("gitea.client.gitea.requests.Session", return_value=session):
            result = runner.invoke(
                app,
                [
                    "watch",
                    "list",
                    "--owner",
                    "my-org",
                    "--repository",
                    "my-repo",
                    "--project-id",
                    "29",
                    "--state-file",
                    str(tmp_path / "watch-state.json"),
                    *AUTH,
                ],
            )

        assert result.exit_code == 0, result.output
        assert session.requests == [
            ("GET", "https://gitea.invalid/api/v1/repos/my-org/my-repo/issues"),
            ("GET", "https://gitea.invalid/api/v1/repos/my-org/my-repo/projects/29/columns"),
        ]

    def test_a_project_of_the_owner_reaches_the_organization_endpoint(self, tmp_path: Path) -> None:
        """Omitting `--repository` should watch the organization's own board."""
        session = RecordingSession()

        with patch("gitea.client.gitea.requests.Session", return_value=session):
            result = runner.invoke(
                app,
                [
                    "watch",
                    "list",
                    "--owner",
                    "my-org",
                    "--project-id",
                    "29",
                    "--state-file",
                    str(tmp_path / "watch-state.json"),
                    *AUTH,
                ],
            )

        assert result.exit_code == 0, result.output
        assert session.requests == [("GET", "https://gitea.invalid/api/v1/orgs/my-org/projects/29/columns")]

    def test_a_repository_scope_lists_its_open_issues_and_their_comments(self, tmp_path: Path) -> None:
        """Watching every issue ever closed would make the listing grow forever."""
        client = make_client([ISSUE], comments={15: [COMMENT]})

        run(*watch(tmp_path / "watch-state.json"), client=client)

        assert client.issue.list_issues.call_args_list[0].kwargs == {
            "owner": "my-org",
            "repository": "my-repo",
            "state": "open",
            "page": 1,
            "limit": PAGE_SIZE,
        }
        assert client.comment.list_comments.call_args_list[0].kwargs == {
            "owner": "my-org",
            "repository": "my-repo",
            "index": 15,
            "page": 1,
            "limit": PAGE_SIZE,
        }

    def test_a_project_scope_lists_its_columns_and_their_issues(self, tmp_path: Path) -> None:
        """Every listing a board is walked through asks for a full page of it."""
        client = make_client(columns=[{"id": 5, "title": "Todo"}], column_issues={5: [ISSUE]})

        run(
            "watch",
            "list",
            "--owner",
            "my-org",
            "--project-id",
            "29",
            "--state-file",
            str(tmp_path / "watch-state.json"),
            *AUTH,
            client=client,
        )

        assert client.project.list_project_columns.call_args_list[0].kwargs == {
            "owner": "my-org",
            "repository": None,
            "project_id": 29,
            "page": 1,
            "limit": PAGE_SIZE,
        }
        assert client.project.list_project_column_issues.call_args_list[0].kwargs == {
            "owner": "my-org",
            "repository": None,
            "project_id": 29,
            "column_id": 5,
            "page": 1,
            "limit": PAGE_SIZE,
        }

    def test_a_malformed_entry_does_not_end_the_walk(self, tmp_path: Path) -> None:
        """One unusable issue must not take the issues listed after it with it.

        Dropping the rest of the scope would report every one of them as gone on
        this run and as new on the next.
        """
        client = make_client(["not an issue", {"number": 15}, ISSUE, OTHER_ISSUE])

        result = run(*watch(tmp_path / "watch-state.json", output="json"), client=client)

        assert result.exit_code == 0
        assert parse_envelope(result.stdout)["metadata"]["issue_count"] == 2

    def test_every_page_of_a_listing_is_walked(self, tmp_path: Path) -> None:
        """A scope larger than one page must not look like a scope that shrank."""
        state_path = tmp_path / "watch-state.json"
        client = make_client()
        client.issue.list_issues.side_effect = paged([ISSUE], [OTHER_ISSUE])

        result = run(*watch(state_path, output="json"), client=client)

        assert parse_envelope(result.stdout)["metadata"]["issue_count"] == 2
        assert [call.kwargs["page"] for call in client.issue.list_issues.call_args_list] == [1, 2, 3]


class TestRecovery:
    """Tests for the caches a run has to survive."""

    @pytest.mark.parametrize("content", ["", "not json at all", '{"scopes": {"repo:my-org/my-repo": "nonsense"}}'])
    def test_an_unreadable_cache_baselines_rather_than_failing(self, tmp_path: Path, content: str) -> None:
        """A watchdog has to recover from a lost cache by itself.

        Args:
            tmp_path: Directory to write the cache into.
            content: The unreadable cache to write.

        """
        state_path = tmp_path / "watch-state.json"
        state_path.write_text(content, encoding="utf-8")

        result = run(*watch(state_path), client=make_client([ISSUE, OTHER_ISSUE]))

        assert result.exit_code == 0
        assert result.stdout == ""
        assert json.loads(state_path.read_text(encoding="utf-8"))["scopes"]["repo:my-org/my-repo"]["issues"]

    def test_a_cache_written_by_a_newer_version_is_read_not_rejected(self, tmp_path: Path) -> None:
        """A field this version does not know must not cost the whole cache."""
        state_path = tmp_path / "watch-state.json"
        state_path.write_text(
            json.dumps(
                {
                    "version": 99,
                    "scopes": {
                        "repo:my-org/my-repo": {
                            "issues": {
                                "1854": {
                                    "number": 15,
                                    "assignees": ["alice"],
                                    "labels": ["bug"],
                                    "comment_hashes": [],
                                    "invented_later": "ignored",
                                }
                            }
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        result = run(*watch(state_path), client=make_client([ISSUE, OTHER_ISSUE]))

        # The recorded issue compares equal and only the new one is reported,
        # which a rejected cache would have baselined into silence.
        assert result.stdout == "my-org/my-repo#16 new: new issue · Ship the release\n"

    def test_a_cache_that_cannot_be_written_fails_the_run(self, tmp_path: Path) -> None:
        """A run whose changes were never recorded would report them forever."""
        state_path = tmp_path / "unwritable" / "watch-state.json"
        state_path.parent.mkdir()
        state_path.parent.chmod(0o500)

        try:
            with patch("gitea.cli.utils.api.logger") as logger:
                result = run(*watch(state_path), client=make_client([ISSUE]))
        finally:
            state_path.parent.chmod(0o700)

        assert result.exit_code == 1
        # A failed command leaves stdout parsable, as every other error does.
        assert result.stdout == ""
        assert logger.exception.call_count == 0
        assert "Could not write the watch cache at" in logged_error(logger)


class TestScopeErrors:
    """Tests for how an invocation naming nothing to watch is refused."""

    def test_naming_nothing_to_watch_says_what_to_pass(self, tmp_path: Path) -> None:
        """The message should name the options rather than report an empty digest."""
        with patch("gitea.cli.utils.api.logger") as logger:
            result = run(
                "watch",
                "list",
                "--owner",
                "my-org",
                "--state-file",
                str(tmp_path / "watch-state.json"),
                *AUTH,
            )

        assert result.exit_code == 1
        assert result.stdout == ""
        assert logger.exception.call_count == 0
        message = logged_error(logger)
        assert "'gitea-cli watch list' needs something to watch" in message
        assert "--repository REPOSITORY" in message
        assert "--project-id ID" in message

    def test_a_project_alongside_several_repositories_is_refused(self, tmp_path: Path) -> None:
        """The ambiguity is named rather than resolved by a guess."""
        with patch("gitea.cli.utils.api.logger") as logger:
            result = run(
                "watch",
                "list",
                "--owner",
                "my-org",
                "--repository",
                "one",
                "--repository",
                "two",
                "--project-id",
                "29",
                "--state-file",
                str(tmp_path / "watch-state.json"),
                *AUTH,
            )

        assert result.exit_code == 1
        assert result.stdout == ""
        assert "cannot resolve --project-id against 2 repositories" in logged_error(logger)

    def test_nothing_is_written_when_the_scopes_are_refused(self, tmp_path: Path) -> None:
        """A refused invocation must not leave a cache claiming a scope was watched."""
        state_path = tmp_path / "watch-state.json"

        run("watch", "list", "--owner", "my-org", "--state-file", str(state_path), *AUTH)

        assert not state_path.exists()


class TestStateFileOption:
    """Tests for naming the cache."""

    def test_the_environment_names_the_cache_when_the_option_is_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A cron entry should be able to set the cache once for every run."""
        state_path = tmp_path / "from-the-environment.json"
        monkeypatch.setenv(STATE_FILE_ENV, str(state_path))

        result = run(
            "watch", "list", "--owner", "my-org", "--repository", "my-repo", *AUTH, client=make_client([ISSUE])
        )

        assert result.exit_code == 0
        assert state_path.exists()

    def test_the_option_wins_over_the_environment(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """An explicit path should decide, as `--output` does over its variable."""
        monkeypatch.setenv(STATE_FILE_ENV, str(tmp_path / "from-the-environment.json"))
        state_path = tmp_path / "from-the-option.json"

        run(*watch(state_path), client=make_client([ISSUE]))

        assert state_path.exists()
        assert not (tmp_path / "from-the-environment.json").exists()

    def test_the_cache_in_use_is_reported(self, tmp_path: Path) -> None:
        """A run should say which cache it compared against."""
        state_path = tmp_path / "watch-state.json"

        result = run(*watch(state_path, output="json"), client=make_client([ISSUE]))

        assert parse_envelope(result.stdout)["metadata"]["state_file"] == str(state_path)


class TestUnreachableInstance:
    """Tests for an instance the run could not reach."""

    def test_the_base_url_is_named_and_the_cache_is_left_alone(self, tmp_path: Path) -> None:
        """A failed fetch must not record an empty scope as the current state."""
        import requests

        state_path = tmp_path / "watch-state.json"
        run(*watch(state_path), client=make_client([ISSUE]))
        recorded = state_path.read_bytes()

        client = make_client()
        client.issue.list_issues.side_effect = requests.ConnectionError("Connection refused")

        with patch("gitea.cli.utils.api.logger") as logger:
            result = run(*watch(state_path), client=client)

        assert result.exit_code == 1
        assert result.stdout == ""
        assert "Could not reach the Gitea API at https://gitea.invalid" in logged_error(logger)
        assert state_path.read_bytes() == recorded


class TestHelp:
    """Tests for how the command family presents itself."""

    def test_the_family_is_registered(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`watch list` should be reachable from the root command."""
        monkeypatch.setenv("COLUMNS", "200")
        result = runner.invoke(app, ["watch", "--help"])

        assert result.exit_code == 0
        assert "list" in unrendered(result.stdout)
