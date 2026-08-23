"""Unit tests for the `actions job logs` command.

This is the one command in the CLI whose two output formats carry the same thing
in different shapes: the endpoint answers with the log file, so text mode writes
the log and JSON mode wraps it in the envelope. Both are run here through the
real client against the recording session, since what the text mode writes to
stdout is the whole point of the command and a mock of the client cannot show it.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from gitea.cli.actions.job.logs import job_logs_command
from gitea.cli.main import app
from tests.cli.envelope import parse_envelope
from tests.transport import RawBody, RecordingSession

runner = CliRunner()

BASE_URL = "https://gitea.invalid"
TOKEN = "seed-token"
JOB_ID = 118

LOGS = "::group::Run\nbuilding\n::endgroup::\n"

CREDENTIALS = ("--token", TOKEN, "--base-url", BASE_URL)
TARGET = ("--owner", "o", "--repository", "r", "--job-id", str(JOB_ID))


def make_ctx() -> SimpleNamespace:
    """Create a context carrying the configuration path a command reads.

    Returns:
        The stand-in context.

    """
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


def invoke(arguments: tuple[str, ...], payload: object) -> tuple[object, RecordingSession]:
    """Run the command against a session answering with a payload.

    Args:
        arguments: The arguments to invoke the CLI with.
        payload: What the endpoint answers with.

    Returns:
        The result of the invocation, and the session recording the request.

    """
    session = RecordingSession(payload)
    with patch("gitea.client.gitea.requests.Session", return_value=session):
        return runner.invoke(app, list(arguments)), session


def test_text_output_is_the_log_itself() -> None:
    """Text mode should write the log to stdout and nothing else.

    Not the envelope, and not a log with a newline added: the output has to be
    the file, so that it can be piped, grepped or redirected as one.
    """
    result, session = invoke(("actions", "job", "logs", *TARGET, *CREDENTIALS), RawBody(LOGS))

    assert result.exit_code == 0, result.output
    assert result.stdout == LOGS
    assert session.requests == [("GET", f"{BASE_URL}/api/v1/repos/o/r/actions/jobs/{JOB_ID}/logs")]


def test_a_job_with_no_output_yet_prints_nothing() -> None:
    """An empty log should print nothing at all, rather than a blank line."""
    result, _ = invoke(("actions", "job", "logs", *TARGET, *CREDENTIALS), RawBody(""))

    assert result.exit_code == 0, result.output
    assert result.stdout == ""


def test_json_output_wraps_the_log_in_the_envelope() -> None:
    """JSON mode should emit the envelope, with the log as a string and the job named.

    A consumer parsing stdout as JSON cannot be handed a raw log, and the
    response has no field of its own saying whose logs it carries, so the
    command adds one.
    """
    result, _ = invoke(("--output", "json", "actions", "job", "logs", *TARGET, *CREDENTIALS), RawBody(LOGS))

    assert result.exit_code == 0, result.output
    envelope = parse_envelope(result.stdout)
    assert envelope["data"] == {"job_id": JOB_ID, "logs": LOGS}
    assert envelope["metadata"] == {"status_code": 200}


@patch("gitea.cli.utils.api.execute_api_call")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_it_asks_for_the_job_it_was_named(mock_gitea, mock_get_auth_params, mock_execute) -> None:
    """The job ID should reach the client, and the log come back under it."""
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")
    client = MagicMock()
    client.actions.get_workflow_job_logs.return_value = (LOGS, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    job_logs_command(
        ctx=make_ctx(),
        owner="owner",
        job_id=JOB_ID,
        repository="repo",
        account_name="acct",
        token=None,
        base_url=None,
    )

    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli actions job logs"

    data, metadata = call_kwargs["api_call"]()
    client.actions.get_workflow_job_logs.assert_called_once_with(owner="owner", repository="repo", job_id=JOB_ID)
    assert data == {"job_id": JOB_ID, "logs": LOGS}
    assert metadata == {"status_code": 200}
