"""Unit tests for the `actions run get` command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gitea.cli.actions.run.get import get_run_command

RUN = {"id": 42, "status": "in_progress", "conclusion": None}


def make_ctx() -> SimpleNamespace:
    """Create a context carrying the configuration path a command reads.

    Returns:
        The stand-in context.

    """
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_it_asks_for_the_run_it_was_named(mock_gitea, mock_get_auth_params, mock_execute) -> None:
    """The run ID should reach the client as it was passed."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    client = MagicMock()
    client.actions.get_workflow_run.return_value = (RUN, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    get_run_command(
        ctx=make_ctx(),
        owner="owner",
        run_id=42,
        repository="repo",
        account_name="acct",
        token=None,
        base_url=None,
    )

    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli actions run get"

    result = call_kwargs["api_call"]()
    client.actions.get_workflow_run.assert_called_once_with(owner="owner", repository="repo", run_id=42)
    assert result == (RUN, {"status_code": 200})
