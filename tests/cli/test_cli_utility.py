"""Unit tests for CLI utility functions."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from gitea.cli.utility import execute_api_command


class TestExecuteApiCommand:
    """Test cases for execute_api_command function."""

    @pytest.fixture
    def mock_ctx(self):
        """Fixture to create a mock Typer context."""
        ctx = MagicMock(spec=typer.Context)
        ctx.obj = {"output": None}
        return ctx

    @pytest.fixture
    def mock_api_call(self):
        """Fixture to create a mock API call function."""
        return MagicMock(return_value={"key": "value"})

    @patch("gitea.cli.utility.Console")
    def test_successful_call_no_output(self, mock_console_class, mock_ctx, mock_api_call):
        """Test successful API call with no output file."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        execute_api_command(ctx=mock_ctx, api_call=mock_api_call, command_name="test-command")

        mock_api_call.assert_called_once()
        mock_console.print_json.assert_called_once_with('{\n    "key": "value"\n}')
        mock_console.print.assert_not_called()

    @patch("gitea.cli.utility.Console")
    @patch("gitea.cli.utility.Path")
    def test_successful_call_with_output(self, mock_path_class, mock_console_class, mock_ctx, mock_api_call):
        """Test successful API call with output file."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_output_path = MagicMock(spec=Path)
        mock_path_class.return_value = mock_output_path

        mock_ctx.obj["output"] = "/path/to/output.json"

        execute_api_command(ctx=mock_ctx, api_call=mock_api_call, command_name="test-command")

        mock_api_call.assert_called_once()
        mock_output_path.write_text.assert_called_once_with('{\n    "key": "value"\n}')
        mock_console.print.assert_called_once_with("Output saved to /path/to/output.json")
        mock_console.print_json.assert_not_called()

    @patch("gitea.cli.utility.Console")
    def test_api_call_raises_exception(self, mock_console_class, mock_ctx, mock_api_call):
        """Test API call that raises an exception."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_api_call.side_effect = Exception("API Error")

        with pytest.raises(typer.Exit):
            execute_api_command(ctx=mock_ctx, api_call=mock_api_call, command_name="test-command")

        mock_api_call.assert_called_once()
        mock_console.print.assert_called_once_with("Error executing test-command: API Error", style="red")
        mock_console.print_json.assert_not_called()
