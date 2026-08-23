"""Download the archive of one Actions artifact.

The endpoint answers with the zip archive rather than with a document, which is
why this command is shaped differently from its neighbours: the payload goes to
the file named by `--file`, and what is reported is where it went and how large it
was. Writing the archive to stdout is deliberately not offered - a zip interleaved
with the JSON envelope would be neither - so the path is required.

Two refusals are worth knowing before scripting it. An artifact whose archive has
expired answers with no body, and writing that out would leave a zero-byte file
that looks like an empty artifact rather than a missing one, so it is reported
instead. And an existing file is not overwritten without `--force`, since the
usual mistake is a path that already holds something else.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from gitea.cli.utils.options import ARTIFACT_ID_HELP, REPOSITORY_REQUIRED_HELP

COMMAND_NAME = "gitea-cli actions artifact download"


def download_artifact_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    artifact_id: Annotated[int, typer.Option("--artifact-id", help=ARTIFACT_ID_HELP)],
    file: Annotated[
        Path,
        typer.Option("--file", help="Path to write the zip archive to. It is not written to stdout."),
    ],
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_REQUIRED_HELP)] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite the file at --file if it already exists."),
    ] = False,
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
    """Download the archive of one Actions artifact.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        artifact_id: The ID of the artifact.
        file: Where to write the zip archive.
        repository: The name of the repository, which this command requires.
        force: Whether to overwrite an existing file.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.output import emit  # noqa: PLC0415
    from gitea.cli.utils.api import execute_api_call  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.cli.utils.errors import CommandError  # noqa: PLC0415
    from gitea.cli.utils.options import require_repository  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Download the archive and write it to the file.

        Returns:
            A tuple containing the artifact the archive belongs to, where it was
            written and how large it was, and metadata.

        Raises:
            CommandError: If the file already exists and `--force` was not
                passed, or if the artifact has no archive left to download.

        """
        target_repository = require_repository(repository, command=COMMAND_NAME)

        if file.exists() and not force:
            raise CommandError(
                f"'{COMMAND_NAME}' will not overwrite {file}: pass --force, or name a path that is free."
            )

        with Gitea(token=token, base_url=base_url) as client:
            archive, metadata = client.actions.download_artifact(
                owner=owner,
                repository=target_repository,
                artifact_id=artifact_id,
            )

        if not archive:
            raise CommandError(
                f"'{COMMAND_NAME}' was answered with no archive for artifact {artifact_id}, which is what an "
                f"expired artifact answers with. Read 'expired' with "
                f"'gitea-cli actions artifact get --artifact-id {artifact_id}'; nothing was written to {file}."
            )

        file.write_bytes(archive)

        return {"artifact_id": artifact_id, "path": str(file), "size_in_bytes": len(archive)}, metadata

    def report(data: Any, metadata: dict[str, Any]) -> None:
        """Say where the archive went, in the format this invocation asked for.

        Args:
            data: The artifact, the path and the size.
            metadata: Information about the call.

        """

        def render_text() -> None:
            """Name the file that was written and its size."""
            typer.echo(f"{data['path']} ({data['size_in_bytes']} bytes)")

        emit(ctx, data=data, metadata=metadata, render_text=render_text)

    execute_api_call(api_call=api_call, report=report, base_url=base_url, command_name=COMMAND_NAME)
