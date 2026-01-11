"""Unit tests for user CLI main module."""

from unittest.mock import MagicMock, patch

import typer

from gitea.cli.user.main import register_commands, user_app


class TestUserApp:
    """Test cases for user_app Typer instance."""

    def test_user_app_creation(self):
        """Test that user_app is properly configured."""
        assert isinstance(user_app, typer.Typer)
        assert user_app.info.name == "user"
        assert user_app.info.help == "Commands for managing Gitea users."


class TestRegisterCommands:
    """Test cases for register_commands function."""

    @patch("gitea.cli.user.get_user.get_user_command", new_callable=MagicMock)
    @patch("gitea.cli.user.get_workflow_jobs.get_workflow_jobs_command", new_callable=MagicMock)
    @patch("gitea.cli.user.get_user_level_runners.get_user_level_runners_command", new_callable=MagicMock)
    @patch("gitea.cli.user.get_registration_token.get_registration_token_command", new_callable=MagicMock)
    @patch("gitea.cli.user.delete_user_level_runner.delete_user_level_runner_command", new_callable=MagicMock)
    @patch("gitea.cli.user.get_workflow_runs.get_workflow_runs_command", new_callable=MagicMock)
    def test_register_commands(  # noqa: PLR0913
        self,
        mock_get_workflow_runs,
        mock_delete_user_level_runner,
        mock_get_registration_token,
        mock_get_user_level_runners,
        mock_get_workflow_jobs,
        mock_get_user,
    ):
        """Test that register_commands imports and registers all commands."""
        # Create a fresh app for testing
        test_app = typer.Typer(name="user", help="Commands for managing Gitea users.")

        with patch("gitea.cli.user.main.user_app", test_app):
            register_commands()

        # Check that all commands were registered
        command_names = [cmd.name for cmd in test_app.registered_commands]
        assert "get-user" in command_names
        assert "get-workflow-jobs" in command_names
        assert "get-user-level-runners" in command_names
        assert "get-registration-token" in command_names
        assert "delete-user-level-runner" in command_names
        assert "get-workflow-runs" in command_names
