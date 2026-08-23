"""Unit tests for what a watch run works out that it is watching.

`build_scopes` is shared by `watch list` and `watch advance`: the two commands
have to agree about which issues a scope holds and which key it is cached under,
or an advance would commit a baseline the next list run compares against under
another name. The tests live here rather than with either command for the same
reason.
"""

from __future__ import annotations

import pytest

from gitea.cli.watch.scopes import build_scopes

COMMAND = "gitea-cli watch list"


class TestBuildScopes:
    """Tests for working out what a run watches from the options naming it."""

    def test_every_repository_named_is_a_scope(self) -> None:
        """Repeating `--repository` should watch each of them."""
        scopes = build_scopes("my-org", ["one", "two"], [], COMMAND)

        assert [scope.key for scope in scopes] == ["repo:my-org/one", "repo:my-org/two"]
        assert [scope.repository for scope in scopes] == ["one", "two"]
        assert [scope.project_id for scope in scopes] == [None, None]

    def test_a_project_without_a_repository_belongs_to_the_owner(self) -> None:
        """Omitting `--repository` should watch the organization's own project."""
        scopes = build_scopes("my-org", [], [29], COMMAND)

        assert [scope.key for scope in scopes] == ["project:my-org/29"]
        assert scopes[0].repository is None
        assert scopes[0].project_id == 29

    def test_a_project_is_resolved_against_the_single_repository_named(self) -> None:
        """A repository project should be keyed apart from the organization's."""
        scopes = build_scopes("my-org", ["my-repo"], [29], COMMAND)

        assert [scope.key for scope in scopes] == ["repo:my-org/my-repo", "project:my-org/my-repo/29"]
        assert scopes[1].repository == "my-repo"

    def test_watching_nothing_names_the_options_to_pass(self) -> None:
        """A run with no scope should say what to name, not watch nothing quietly."""
        from gitea.cli.utils.errors import CommandError

        with pytest.raises(CommandError, match="needs something to watch"):
            build_scopes("my-org", [], [], COMMAND)

    def test_the_same_repository_named_twice_is_watched_once(self) -> None:
        """One scope per key, so a repeated name is not fetched and compared twice.

        Both occurrences would otherwise be compared against the same recorded
        snapshots, reporting every change on it twice.
        """
        assert [scope.key for scope in build_scopes("my-org", ["one", "two", "one"], [], COMMAND)] == [
            "repo:my-org/one",
            "repo:my-org/two",
        ]
        assert [scope.key for scope in build_scopes("my-org", [], [29, 29], COMMAND)] == ["project:my-org/29"]

    def test_a_project_cannot_be_resolved_against_several_repositories(self) -> None:
        """Two repositories leave no single scope for a project ID to belong to."""
        from gitea.cli.utils.errors import CommandError

        with pytest.raises(CommandError, match="cannot resolve --project-id against 2 repositories"):
            build_scopes("my-org", ["one", "two"], [29], COMMAND)


class TestTheRefusalNamesTheInvocation:
    """Tests for the command name a refusal is phrased with.

    Both commands build their scopes here, and a user who typed `watch advance`
    is not helped by being told what `watch list` needs.
    """

    @pytest.mark.parametrize("command", ["gitea-cli watch list", "gitea-cli watch advance"])
    def test_naming_nothing_to_watch_names_the_command_that_was_run(self, command: str) -> None:
        """The refusal should quote the invocation the user typed."""
        from gitea.cli.utils.errors import CommandError

        with pytest.raises(CommandError, match=f"'{command}' needs something to watch"):
            build_scopes("my-org", [], [], command)

    @pytest.mark.parametrize("command", ["gitea-cli watch list", "gitea-cli watch advance"])
    def test_an_unresolvable_project_names_the_command_that_was_run(self, command: str) -> None:
        """So should the refusal of a project with nothing to resolve it against."""
        from gitea.cli.utils.errors import CommandError

        with pytest.raises(CommandError, match=f"'{command}' cannot resolve --project-id"):
            build_scopes("my-org", ["one", "two"], [29], command)
