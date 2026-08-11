"""Edit project command."""

from __future__ import annotations

from typing import Annotated, Literal

import typer


def edit_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    repository: Annotated[str, typer.Option("--repository", help="Name of the repository.")],
    project_id: Annotated[int, typer.Option("--project-id", help="ID of the project.")],
    title: Annotated[
        str | None,
        typer.Option("--title", help="Title of the project."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", help="Description of the project."),
    ] = None,
    card_type: Annotated[
        str | None,
        typer.Option("--card-type", help="Card type of the project (text_only, images_and_text)."),
    ] = None,
    state: Annotated[
        Literal["open", "closed"] | None,
        typer.Option("--state", help="State of the project."),
    ] = None,
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
            help="Base URL of the Gitea platform. If not provided, the base URL from the specified account will be used.",
        ),
    ] = None,
) -> None:
    """Edit a project in a repository.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        repository: The name of the repository.
        project_id: The ID of the project.
        title: The title of the project.
        description: The description of the project.
        card_type: The card type of the project.
        state: The state of the project.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Edit project information.

        Returns:
            A tuple containing the project data and metadata.

        """
        with Gitea(token=token, base_url=base_url) as client:
            return client.project.edit_project(
                owner=owner,
                repository=repository,
                project_id=project_id,
                title=title,
                description=description,
                card_type=card_type,
                state=state,
            )

    execute_api_command(api_call=api_call, command_name="gitea-cli project edit")
