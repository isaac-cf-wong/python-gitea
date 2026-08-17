"""Unit tests for the CLI API utils."""

import json
from unittest.mock import MagicMock

import pytest
import typer
from requests import ConnectionError as RequestsConnectionError
from requests import HTTPError, Timeout

from gitea.cli.utils.api import execute_api_command
from gitea.cli.utils.errors import CommandError


def test_execute_api_command_success(capsys):
    """Should print JSON with data and metadata on success."""

    def api_call():
        return {"key": "value"}, {"meta": 1}

    execute_api_command(api_call, command_name="MyCmd")

    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["data"] == {"key": "value"}
    assert out["metadata"] == {"meta": 1}


def test_execute_api_command_exception(monkeypatch):
    """Should log the exception and raise typer.Exit with code 1."""

    def api_call():
        raise ValueError("boom")

    mock_logger = MagicMock()
    monkeypatch.setattr("gitea.cli.utils.api.logger", mock_logger)

    with pytest.raises(typer.Exit) as exc_info:
        execute_api_command(api_call, command_name="MyCmd")

    # Typer Exit should carry the exit code passed
    exit_code = getattr(exc_info.value, "exit_code", getattr(exc_info.value, "code", None))
    assert exit_code == 1

    # Logger.exception should have been called with the message and the command name.
    # The exception itself is captured via exc_info, not passed as an argument.
    mock_logger.exception.assert_called_once()
    call_args = mock_logger.exception.call_args[0]
    assert call_args[1] == "MyCmd"


def test_execute_api_command_command_error(monkeypatch):
    """Should log a CommandError as its message alone and raise typer.Exit with code 1."""

    def api_call():
        raise CommandError("No issue #15 in owner/repo")

    mock_logger = MagicMock()
    monkeypatch.setattr("gitea.cli.utils.api.logger", mock_logger)

    with pytest.raises(typer.Exit) as exc_info:
        execute_api_command(api_call, command_name="MyCmd")

    exit_code = getattr(exc_info.value, "exit_code", getattr(exc_info.value, "code", None))
    assert exit_code == 1

    # The message carries the whole error, so no traceback is logged.
    mock_logger.exception.assert_not_called()
    mock_logger.error.assert_called_once()
    assert str(mock_logger.error.call_args[0][1]) == "No issue #15 in owner/repo"


@pytest.mark.parametrize(
    "error",
    [
        RequestsConnectionError("Failed to establish a new connection: [Errno 111] Connection refused"),
        Timeout("Read timed out. (read timeout=10)"),
    ],
    ids=["connection", "timeout"],
)
def test_execute_api_command_unreachable_instance(monkeypatch, error):
    """Should report a connection or timeout failure without a traceback."""

    def api_call():
        raise error

    mock_logger = MagicMock()
    monkeypatch.setattr("gitea.cli.utils.api.logger", mock_logger)

    with pytest.raises(typer.Exit) as exc_info:
        execute_api_command(api_call, command_name="MyCmd")

    exit_code = getattr(exc_info.value, "exit_code", getattr(exc_info.value, "code", None))
    assert exit_code == 1

    # There is no response to report a status from, so the message points at
    # the instance instead, and a traceback would add nothing.
    mock_logger.exception.assert_not_called()
    mock_logger.error.assert_called_once()
    message = str(mock_logger.error.call_args[0][1])
    assert "Could not reach the Gitea API" in message
    assert str(error) in message


def test_execute_api_command_http_error_keeps_its_traceback(monkeypatch):
    """Should not mistake a rejected request for an unreachable instance.

    `HTTPError` is a `RequestException` too, so catching connection failures
    too broadly would report every rejected call as unreachable.
    """

    def api_call():
        raise HTTPError("404 Client Error")

    mock_logger = MagicMock()
    monkeypatch.setattr("gitea.cli.utils.api.logger", mock_logger)

    with pytest.raises(typer.Exit):
        execute_api_command(api_call, command_name="MyCmd")

    mock_logger.error.assert_not_called()
    mock_logger.exception.assert_called_once()


@pytest.mark.parametrize(
    "error",
    [
        CommandError("Could not reach the Gitea API at http://[fe80::1]:3000: refused"),
        RequestsConnectionError("HTTPConnectionPool(host='[fe80::1]', port=3000)"),
    ],
    ids=["command-error", "connection"],
)
def test_execute_api_command_logs_errors_as_literal_text(monkeypatch, error):
    """Should log error messages as text, since they can look like Rich markup.

    An IPv6 base URL such as `http://[fe80::1]:3000` parses as a style tag, and
    the handler configured by `setup_logging` raises on one it cannot resolve.
    """

    def api_call():
        raise error

    mock_logger = MagicMock()
    monkeypatch.setattr("gitea.cli.utils.api.logger", mock_logger)

    with pytest.raises(typer.Exit):
        execute_api_command(api_call, command_name="MyCmd")

    assert mock_logger.error.call_args.kwargs["extra"] == {"markup": False}
