"""Unit tests for the `actions run jobs` command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gitea.cli.actions.run.jobs import list_run_jobs_command

JOBS = {"total_count": 1, "jobs": [{"id": 118, "name": "build"}]}


def make_ctx() -> SimpleNamespace:
    """Create a context carrying the configuration path a command reads.

    Returns:
        The stand-in context.

    """
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_it_lists_the_jobs_of_the_run_with_every_filter(mock_gitea, mock_get_auth_params, mock_execute) -> None:
    """The run, the status filter and the paging should all reach the client."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    client = MagicMock()
    client.actions.list_workflow_run_jobs.return_value = (JOBS, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_run_jobs_command(
        ctx=make_ctx(),
        owner="owner",
        run_id=42,
        repository="repo",
        status="failure",
        page=3,
        limit=7,
        account_name="acct",
        token=None,
        base_url=None,
    )

    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli actions run jobs"

    result = call_kwargs["api_call"]()
    client.actions.list_workflow_run_jobs.assert_called_once_with(
        owner="owner", repository="repo", run_id=42, status="failure", page=3, limit=7
    )
    assert result == (JOBS, {"status_code": 200})
