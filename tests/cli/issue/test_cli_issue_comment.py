"""Unit tests for the `issue comment` alias of the comment CLI commands."""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from gitea.cli.comment import main as comment_main
from gitea.cli.issue import main as issue_main
from gitea.cli.main import app

runner = CliRunner()


def test_comment_group_registered_on_issue_app():
    """The issue_app should expose a `comment` group backed by the comment_app."""
    groups = {group.name: group for group in issue_main.issue_app.registered_groups}

    assert "comment" in groups
    assert groups["comment"].typer_instance is comment_main.comment_app


def test_issue_comment_commands_share_the_top_level_implementations():
    """The aliased commands should be the very same callbacks as `gitea-cli comment`."""
    group = next(group for group in issue_main.issue_app.registered_groups if group.name == "comment")

    aliased = {command.name: command.callback for command in group.typer_instance.registered_commands}
    top_level = {command.name: command.callback for command in comment_main.comment_app.registered_commands}

    assert set(aliased) == {"add", "delete", "edit", "list"}
    assert aliased == top_level


@pytest.mark.parametrize("command", ["add", "delete", "edit", "list"])
def test_comment_subcommands_reachable_under_issue(command):
    """Each comment command should be invocable as `gitea-cli issue comment <command>`."""
    result = runner.invoke(app, ["issue", "comment", command, "--help"])

    assert result.exit_code == 0


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
def test_issue_comment_list_runs_the_comment_list_command(mock_get_auth_params, mock_execute):
    """`gitea-cli issue comment list` should run the top-level comment list implementation."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    result = runner.invoke(
        app,
        ["issue", "comment", "list", "--owner", "owner", "--repository", "repo", "--index", "7"],
    )

    assert result.exit_code == 0
    mock_execute.assert_called_once()
    assert mock_execute.call_args[1]["command_name"] == "gitea-cli comment list"
