"""Unit tests for the `actions run list` command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gitea.cli.actions.run.list import list_runs_command

RUNS = {"total_count": 1, "workflow_runs": [{"id": 42, "status": "success"}]}


def make_ctx() -> SimpleNamespace:
    """Create a context carrying the configuration path a command reads.

    Returns:
        The stand-in context.

    """
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


def run_command(**overrides) -> MagicMock:
    """Run the command with every option given a value, and return the client it used.

    Args:
        **overrides: Options to pass instead of the defaults below.

    Returns:
        The client the command called, so the arguments it forwarded can be read
        off it.

    """
    arguments = {
        "owner": "owner",
        "repository": "repo",
        "workflow_id": "build.yml",
        "event": "push",
        "branch": "main",
        "status": "in_progress",
        "actor": "someone",
        "head_sha": "deadbeef",
        "exclude_pull_requests": True,
        "page": 2,
        "limit": 5,
        "account_name": "acct",
        "token": None,
        "base_url": None,
    }
    arguments.update(overrides)

    with (
        patch("gitea.cli.utils.api.execute_api_command") as mock_execute,
        patch("gitea.cli.utils.auth.get_auth_params") as mock_get_auth_params,
        patch("gitea.client.gitea.Gitea") as mock_gitea,
    ):
        mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
        client = MagicMock()
        client.actions.list_workflow_runs.return_value = (RUNS, {"status_code": 200})
        mock_gitea.return_value.__enter__.return_value = client

        list_runs_command(ctx=make_ctx(), **arguments)

        assert mock_execute.call_args[1]["command_name"] == "gitea-cli actions run list"
        assert mock_execute.call_args[1]["api_call"]() == (RUNS, {"status_code": 200})

    return client


def test_every_filter_reaches_the_client() -> None:
    """Each option should be forwarded, since a dropped filter answers with the wrong runs."""
    client = run_command()

    client.actions.list_workflow_runs.assert_called_once_with(
        owner="owner",
        repository="repo",
        workflow_id="build.yml",
        event="push",
        branch="main",
        status="in_progress",
        actor="someone",
        head_sha="deadbeef",
        exclude_pull_requests=True,
        page=2,
        limit=5,
    )


def test_the_pull_request_flag_is_left_unasked_when_it_is_not_set() -> None:
    """Without the flag, the listing sends no `exclude_pull_requests` parameter at all."""
    client = run_command(exclude_pull_requests=False)

    assert client.actions.list_workflow_runs.call_args[1]["exclude_pull_requests"] is None
