"""Update user settings command."""

from __future__ import annotations

from typing import Annotated

import typer


def update_settings_command(  # noqa: PLR0913
    ctx: typer.Context,
    diff_view_style: Annotated[
        str | None, typer.Option("--diff-view-style", help="The preferred diff view style.")
    ] = None,
    full_name: Annotated[str | None, typer.Option("--full-name", help="The full name of the user.")] = None,
    hide_activity: Annotated[
        bool | None, typer.Option("--hide-activity/--no-hide-activity", help="Whether to hide the user's activity.")
    ] = None,
    hide_email: Annotated[
        bool | None, typer.Option("--hide-email/--no-hide-email", help="Whether to hide the user's email.")
    ] = None,
    language: Annotated[str | None, typer.Option("--language", help="The preferred language.")] = None,
    location: Annotated[str | None, typer.Option("--location", help="The location of the user.")] = None,
    theme: Annotated[str | None, typer.Option("--theme", help="The preferred theme.")] = None,
    website: Annotated[str | None, typer.Option("--website", help="The user's website.")] = None,
    account_name: Annotated[
        str | None,
        typer.Option(
            "--account-name",
            help="Name of the account to use for authentication.",
        ),
    ] = None,
    token: Annotated[
        str | None,
        typer.Option(
            "--token",
            help="Token for authentication. If not provided, the token from the specified account will be used.",
        ),
    ] = None,
    base_url: Annotated[
        str | None,
        typer.Option(
            "--base-url",
            help="Base URL of the GitHub platform. If not provided, the base URL from the specified account will be used.",
        ),
    ] = None,
) -> None:
    """Update user settings.

    Args:
        ctx: The Typer context.
        diff_view_style: The preferred diff view style.
        full_name: The full name of the user.
        hide_activity: Whether to hide the user's activity.
        hide_email: Whether to hide the user's email.
        language: The preferred language.
        location: The location of the user.
        theme: The preferred theme.
        website: The user's website.
        account_name: Name of the account to use for authentication.
        token: Token for authentication. If not provided, the token from the specified account will be used.
        base_url: Base URL of the Gitea platform. If not provided, the base URL from the specified account will be used.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj["config_path"],
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Get user information.

        Returns:
            The user information as a dictionary.

        """
        with Gitea(token=token, base_url=base_url) as client:
            return client.user.update_user_settings(
                diff_view_style=diff_view_style,
                full_name=full_name,
                hide_activity=hide_activity,
                hide_email=hide_email,
                language=language,
                location=location,
                theme=theme,
                website=website,
            )

    execute_api_command(api_call=api_call, command_name="gitea-cli user update-settings")
