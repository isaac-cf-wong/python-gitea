"""Print the logs of one job of an Actions workflow run.

The endpoint answers with the log file rather than with a JSON document, and
this is the one command in the family whose two output formats differ in more
than shape. In text mode - the default - it writes the log itself to stdout, so
it can be piped, grepped or redirected like the file it is. Under `--output
json` it emits the usual envelope, with the log as a string under `logs` and the
job it belongs to alongside it, since a consumer parsing stdout as JSON cannot
be handed a raw log.

`job_id` in the envelope is added by this command rather than sent by the
endpoint: the response is a blob and has no field to say whose logs it carries.
"""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import JOB_ID_HELP, REPOSITORY_REQUIRED_HELP

COMMAND_NAME = "gitea-cli actions job logs"


def job_logs_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    job_id: Annotated[int, typer.Option("--job-id", help=JOB_ID_HELP)],
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
    """Print the logs of one job of an Actions workflow run.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        job_id: The ID of the job.
        repository: The name of the repository, which this command requires.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.output import emit  # noqa: PLC0415
    from gitea.cli.utils.api import execute_api_call  # noqa: PLC0415
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
        """Download the job's logs.

        Returns:
            A tuple containing the logs, under the job they belong to, and
            metadata.

        """
        target_repository = require_repository(repository, command=COMMAND_NAME)

        with Gitea(token=token, base_url=base_url) as client:
            logs, metadata = client.actions.get_workflow_job_logs(
                owner=owner,
                repository=target_repository,
                job_id=job_id,
            )

        return {"job_id": job_id, "logs": logs}, metadata

    def report(data: Any, metadata: dict[str, Any]) -> None:
        """Write the logs out in the format this invocation asked for.

        Args:
            data: The logs, under the job they belong to.
            metadata: Information about the call.

        """

        def render_text() -> None:
            """Write the log to stdout as it arrived.

            No trailing newline is added: the log carries its own, and a job
            that has produced no output yet prints nothing rather than a blank
            line.
            """
            if data["logs"]:
                typer.echo(data["logs"], nl=False)

        emit(ctx, data=data, metadata=metadata, render_text=render_text)

    execute_api_call(api_call=api_call, report=report, base_url=base_url, command_name=COMMAND_NAME)
