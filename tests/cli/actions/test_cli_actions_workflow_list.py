"""Unit tests for the `actions workflow list` command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from gitea.cli.actions.workflow.list import list_workflows_command
from gitea.cli.utils.errors import CommandError

WORKFLOWS = {"total_count": 1, "workflows": [{"id": "build.yml", "name": "Build"}]}


def make_ctx() -> SimpleNamespace:
    """Create a context carrying the configuration path a command reads.

    Returns:
        The stand-in context.

    """
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_it_resolves_the_account_and_lists_the_workflows(mock_gitea, mock_get_auth_params, mock_execute) -> None:
    """The command should resolve the credentials and list the repository's workflows."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    client = MagicMock()
    client.actions.list_workflows.return_value = (WORKFLOWS, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_workflows_command(
        ctx=make_ctx(),
        owner="owner",
        repository="repo",
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_get_auth_params.assert_called_once_with(
        config_path="/tmp/config", account_name="acct", token=None, base_url=None
    )
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli actions workflow list"

    result = call_kwargs["api_call"]()
    client.actions.list_workflows.assert_called_once_with(owner="owner", repository="repo")
    assert result == (WORKFLOWS, {"status_code": 200})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_a_missing_repository_is_reported_rather_than_requested(mock_gitea, mock_get_auth_params, mock_execute) -> None:
    """Omitting `--repository` should be refused before any request is made.

    The endpoint has no owner-wide form, and the option is optional at the
    parser level everywhere in this CLI, so the command is what has to say so.
    """
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    list_workflows_command(
        ctx=make_ctx(),
        owner="owner",
        repository=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError, match="needs a repository"):
        mock_execute.call_args[1]["api_call"]()

    mock_gitea.assert_not_called()
