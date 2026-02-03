"""Unit tests for the CLI API utils."""

import json
from unittest.mock import MagicMock

import pytest
import typer

from gitea.cli.utils.api import execute_api_command


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

    # Logger.exception should have been called with the message and the command name and exception
    mock_logger.exception.assert_called_once()
    call_args = mock_logger.exception.call_args[0]
    assert call_args[1] == "MyCmd"
    assert isinstance(call_args[2], ValueError)
