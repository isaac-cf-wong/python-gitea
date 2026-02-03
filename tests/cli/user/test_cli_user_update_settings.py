"""Unit tests for the CLI user update-settings command."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gitea.cli.user.update_settings import update_settings_command


def make_ctx():
    """Create a mock Typer context with config_path."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_update_settings_calls_execute_and_passes_params(mock_gitea, mock_get_auth_params, mock_execute):
    """update_settings_command should lookup auth and pass api_call that calls update_user_settings."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.user.update_user_settings.return_value = ({"id": 1}, {"meta": True})
    mock_gitea.return_value.__enter__.return_value = client

    update_settings_command(
        ctx=ctx,
        diff_view_style="unified",
        full_name="Dev",
        hide_activity=True,
        hide_email=False,
        language="en",
        location="Earth",
        theme="dark",
        website="https://example.com",
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_get_auth_params.assert_called_once_with(
        config_path="/tmp/config", account_name="acct", token=None, base_url=None
    )
    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli user update-settings"

    # Run the api_call and ensure client.update_user_settings got called with provided values
    result = call_kwargs["api_call"]()
    assert result == ({"id": 1}, {"meta": True})
    client.user.update_user_settings.assert_called_once_with(
        diff_view_style="unified",
        full_name="Dev",
        hide_activity=True,
        hide_email=False,
        language="en",
        location="Earth",
        theme="dark",
        website="https://example.com",
    )


def test_update_settings_defaults_to_none_for_optional_params():
    """If optional params are not provided, api_call should call update_user_settings with None values."""
    ctx = make_ctx()

    with (
        patch("gitea.cli.utils.api.execute_api_command") as mock_execute,
        patch("gitea.cli.utils.auth.get_auth_params", return_value=("t", "u")),
    ):
        client = MagicMock()
        client.user.update_user_settings.return_value = ({"ok": True}, {})
        with patch("gitea.client.gitea.Gitea") as mock_gitea:
            mock_gitea.return_value.__enter__.return_value = client

            # Call with only ctx
            update_settings_command(ctx=ctx)

            call_kwargs = mock_execute.call_args[1]
            result = call_kwargs["api_call"]()
            assert result == ({"ok": True}, {})
            client.user.update_user_settings.assert_called_once_with(
                diff_view_style=None,
                full_name=None,
                hide_activity=None,
                hide_email=None,
                language=None,
                location=None,
                theme=None,
                website=None,
            )
