"""Unit tests for the `actions workflow dispatch` command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from gitea.cli.actions.workflow.dispatch import dispatch_command, parse_inputs
from gitea.cli.utils.errors import CommandError


def make_ctx() -> SimpleNamespace:
    """Create a context carrying the configuration path a command reads.

    Returns:
        The stand-in context.

    """
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


class TestParseInputs:
    """How `--input KEY=VALUE` is read."""

    def test_no_inputs_send_no_inputs_field(self) -> None:
        """None is not an empty mapping: a dispatch without inputs sends no field.

        Sending `"inputs": {}` instead would be a different request, and one a
        workflow declaring required inputs answers differently.
        """
        assert parse_inputs(None) is None
        assert parse_inputs([]) is None

    def test_each_input_is_read_as_a_name_and_a_value(self) -> None:
        """Several inputs are read into one mapping."""
        assert parse_inputs(["environment=staging", "verbose=1"]) == {"environment": "staging", "verbose": "1"}

    def test_only_the_first_separator_divides_the_pair(self) -> None:
        """A value containing `=` is kept whole.

        Splitting on every `=` would truncate a value that is itself a query, a
        base64 blob or a key-value string - silently, since the truncated value
        is still a valid input.
        """
        assert parse_inputs(["query=a=b=c"]) == {"query": "a=b=c"}

    def test_an_empty_value_is_accepted(self) -> None:
        """`KEY=` sets the input to the empty string, which is a value a workflow may want."""
        assert parse_inputs(["environment="]) == {"environment": ""}

    def test_a_value_without_a_separator_is_refused(self) -> None:
        """An input with no `=` names no value, so it is reported rather than guessed at."""
        with pytest.raises(CommandError, match="could not read the input"):
            parse_inputs(["environment"])

    def test_an_input_with_no_name_is_refused(self) -> None:
        """`=value` names no input."""
        with pytest.raises(CommandError, match="could not read the input"):
            parse_inputs(["=staging"])

    def test_the_same_input_twice_with_the_same_value_is_accepted(self) -> None:
        """A repetition that says the same thing is not a conflict."""
        assert parse_inputs(["environment=staging", "environment=staging"]) == {"environment": "staging"}

    def test_the_same_input_twice_with_different_values_is_refused(self) -> None:
        """Two values for one input would silently keep one of them, so it is refused."""
        with pytest.raises(CommandError, match="twice"):
            parse_inputs(["environment=staging", "environment=production"])


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_it_dispatches_with_the_ref_and_the_inputs(mock_gitea, mock_get_auth_params, mock_execute) -> None:
    """The ref and the parsed inputs should reach the client, and the flag stay unasked."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    client = MagicMock()
    client.actions.dispatch_workflow.return_value = ({}, {"status_code": 204})
    mock_gitea.return_value.__enter__.return_value = client

    dispatch_command(
        ctx=make_ctx(),
        owner="owner",
        workflow_id="build.yml",
        ref="refs/heads/main",
        repository="repo",
        inputs=["environment=staging"],
        return_run_details=False,
        account_name="acct",
        token=None,
        base_url=None,
    )

    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli actions workflow dispatch"

    result = call_kwargs["api_call"]()
    client.actions.dispatch_workflow.assert_called_once_with(
        owner="owner",
        repository="repo",
        workflow_id="build.yml",
        ref="refs/heads/main",
        inputs={"environment": "staging"},
        # Not `False`: a dispatch that did not ask for the run details makes the
        # request it always made, including against an instance that has never
        # heard of the parameter.
        return_run_details=None,
    )
    assert result == ({}, {"status_code": 204})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_the_run_details_are_asked_for_when_the_flag_is_set(mock_gitea, mock_get_auth_params, mock_execute) -> None:
    """`--return-run-details` should ask the response to name the run started."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    client = MagicMock()
    client.actions.dispatch_workflow.return_value = ({"workflow_run_id": 42}, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    dispatch_command(
        ctx=make_ctx(),
        owner="owner",
        workflow_id="build.yml",
        ref="main",
        repository="repo",
        inputs=None,
        return_run_details=True,
        account_name="acct",
        token=None,
        base_url=None,
    )

    result = mock_execute.call_args[1]["api_call"]()

    client.actions.dispatch_workflow.assert_called_once_with(
        owner="owner",
        repository="repo",
        workflow_id="build.yml",
        ref="main",
        inputs=None,
        return_run_details=True,
    )
    assert result == ({"workflow_run_id": 42}, {"status_code": 200})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_an_unreadable_input_is_refused_before_the_workflow_is_started(
    mock_gitea, mock_get_auth_params, mock_execute
) -> None:
    """A malformed `--input` should stop the dispatch rather than run it without that input.

    A dispatch cannot be taken back, so the inputs are read before the request
    is made and not while building it.
    """
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    dispatch_command(
        ctx=make_ctx(),
        owner="owner",
        workflow_id="build.yml",
        ref="main",
        repository="repo",
        inputs=["environment"],
        return_run_details=False,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError, match="could not read the input"):
        mock_execute.call_args[1]["api_call"]()

    mock_gitea.assert_not_called()
