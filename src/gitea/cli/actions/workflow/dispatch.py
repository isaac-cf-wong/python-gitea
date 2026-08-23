"""Start an Actions workflow run.

The workflow has to declare a `workflow_dispatch` trigger: that is the trigger a
dispatch fires, so a workflow without one has nothing for this to start.

Gitea answers a dispatch with `204` and no body, which says the request was
accepted but not which run it started. `--return-run-details` asks the response
to name the run, so a caller can follow the run it dispatched rather than
guessing which of the runs that appeared is its own. An instance too old to know
the parameter ignores it and answers as before, which is why it is asked for
rather than assumed.
"""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.errors import CommandError
from gitea.cli.utils.options import REPOSITORY_REQUIRED_HELP, WORKFLOW_ID_HELP

COMMAND_NAME = "gitea-cli actions workflow dispatch"


def parse_inputs(values: list[str] | None) -> dict[str, str] | None:
    """Read the `--input KEY=VALUE` options into the inputs of a dispatch.

    A value containing `=` is kept whole - `--input query=a=b` is the input
    `query` set to `a=b` - since only the first separator can be the one
    dividing the name from the value.

    Args:
        values: The values passed as --input, or None when none were.

    Returns:
        The inputs to send, or None when no --input was passed, so that a
        dispatch without inputs sends no `inputs` field at all rather than an
        empty object.

    Raises:
        CommandError: If a value carries no `=`, or names an empty key, or names
            the same key twice with different values.

    """
    if not values:
        return None

    inputs: dict[str, str] = {}
    for value in values:
        name, separator, setting = value.partition("=")
        if not separator or not name:
            raise CommandError(
                f"'{COMMAND_NAME}' could not read the input {value!r}: pass --input KEY=VALUE. "
                f"An input whose value contains '=' needs no quoting; only the first '=' divides them."
            )
        if name in inputs and inputs[name] != setting:
            raise CommandError(
                f"'{COMMAND_NAME}' was given the input {name!r} twice, with different values "
                f"({inputs[name]!r} and {setting!r}). Pass it once."
            )
        inputs[name] = setting

    return inputs


def dispatch_command(
    ctx: typer.Context,
    owner: Annotated[str, typer.Option("--owner", help="Owner of the repository.")],
    workflow_id: Annotated[str, typer.Option("--workflow-id", help=WORKFLOW_ID_HELP)],
    ref: Annotated[
        str,
        typer.Option("--ref", help="Branch or tag to run the workflow on, e.g. main or refs/heads/main."),
    ],
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_REQUIRED_HELP)] = None,
    inputs: Annotated[
        list[str] | None,
        typer.Option(
            "--input",
            help="An input of the workflow, as KEY=VALUE. Repeat to pass several.",
        ),
    ] = None,
    return_run_details: Annotated[
        bool,
        typer.Option(
            "--return-run-details",
            help=(
                "Ask the response to identify the run that was started, so it can be followed with "
                "'gitea-cli actions run get'. Instances that do not offer this answer without a body, as they do "
                "without it."
            ),
        ),
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
    """Start a run of one workflow.

    Args:
        ctx: The Typer context.
        owner: The owner of the repository.
        workflow_id: The file name of the workflow.
        ref: The branch or tag to run the workflow on.
        repository: The name of the repository, which this command requires.
        inputs: The workflow's inputs, each as `KEY=VALUE`.
        return_run_details: Whether to ask the response to name the run started.
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
        """Dispatch the workflow.

        Returns:
            A tuple containing the run details when they were asked for, an
            empty object otherwise, and metadata.

        """
        target_repository = require_repository(repository, command=COMMAND_NAME)
        dispatch_inputs = parse_inputs(inputs)

        with Gitea(token=token, base_url=base_url) as client:
            return client.actions.dispatch_workflow(
                owner=owner,
                repository=target_repository,
                workflow_id=workflow_id,
                ref=ref,
                inputs=dispatch_inputs,
                # Omitted rather than sent as false, so a dispatch that did not
                # ask for the details is the request it always was - including
                # against an instance that has never heard of the parameter.
                return_run_details=True if return_run_details else None,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name=COMMAND_NAME)
