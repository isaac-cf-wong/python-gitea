"""Get one artifact of a repository.

`size_in_bytes` is what a download is sized by and `expired` whether there is an
archive left to download at all, so this is worth reading before
`gitea-cli actions artifact download` on an old run.
"""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import ARTIFACT_ID_HELP, REPOSITORY_REQUIRED_HELP

COMMAND_NAME = "gitea-cli actions artifact get"


def get_artifact_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    artifact_id: Annotated[int, typer.Option("--artifact-id", help=ARTIFACT_ID_HELP)],
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_REQUIRED_HELP)] = None,
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
    """Get one artifact of a repository.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        artifact_id: The ID of the artifact.
        repository: The name of the repository, which this command requires.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.cli.utils.options import require_repository  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Fetch the artifact.

        Returns:
            A tuple containing the artifact and metadata.

        """
        target_repository = require_repository(repository, command=COMMAND_NAME)

        with Gitea(token=token, base_url=base_url) as client:
            return client.actions.get_artifact(
                owner=owner,
                repository=target_repository,
                artifact_id=artifact_id,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name=COMMAND_NAME)
