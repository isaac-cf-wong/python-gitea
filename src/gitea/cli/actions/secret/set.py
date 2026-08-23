"""Set an Actions secret of a repository, an organization or the account.

One command for creating and for replacing, because Gitea has one endpoint for
both: it answers `201` when the secret was new and `204` when it replaced one.
Both are success, so a script that only needs the secret to hold a value does not
have to look first, and one that cares reads the status code out of the envelope's
metadata.

`--data -` reads the value from stdin, which is the spelling to use anywhere the
value matters: a value passed on the command line is visible in the shell history
and in the process list of the machine it runs on, and neither is a place for a
secret. Exactly one trailing newline is stripped, so `printf %s` and `echo` both
send what they look like they send.

Which scope is asked for follows the usual convention: `--owner` with
`--repository` for a repository's secret, `--owner` alone for an organization's,
and neither for one of the authenticated account's.
"""

from __future__ import annotations

from typing import Annotated

import typer

from gitea.cli.utils.options import (
    OWNER_SCOPE_HELP,
    REPOSITORY_SCOPE_HELP,
    SECRET_NAME_HELP,
)

COMMAND_NAME = "gitea-cli actions secret set"

# The value of `--data` that asks for the secret to be read from stdin instead.
FROM_STDIN = "-"

DATA_HELP = (
    "Value to store in the secret. Pass '-' to read it from stdin, which keeps it out of the shell history and "
    "the process list."
)


def read_secret_data(data: str) -> str:
    """Read the value to store, from the option or from stdin.

    Args:
        data: The value passed as --data, or `-` to read stdin.

    Returns:
        The value to store. When it came from stdin, one trailing newline is
        stripped - the one the shell adds - so that `echo hunter2 | ... --data -`
        stores what it looks like it stores. A value that really ends in a
        newline is sent with a second one.

    Raises:
        CommandError: If stdin was asked for and carried nothing, which is what a
            command substitution that produced nothing looks like.

    """
    from gitea.cli.utils.errors import CommandError  # noqa: PLC0415

    if data != FROM_STDIN:
        return data

    import sys  # noqa: PLC0415

    from_stdin = sys.stdin.read()
    if not from_stdin:
        raise CommandError(
            f"'{COMMAND_NAME}' was asked to read the secret from stdin and stdin was empty. "
            f"Pipe the value in, or pass it as --data VALUE."
        )
    return from_stdin.removesuffix("\n")


def set_secret_command(
    ctx: typer.Context,
    secret_name: Annotated[str, typer.Option("--secret-name", help=SECRET_NAME_HELP)],
    data: Annotated[str, typer.Option("--data", help=DATA_HELP)],
    owner: Annotated[str | None, typer.Option("--owner", help=OWNER_SCOPE_HELP)] = None,
    repository: Annotated[str | None, typer.Option("--repository", help=REPOSITORY_SCOPE_HELP)] = None,
    description: Annotated[
        str | None,
        typer.Option(
            "--description",
            help="What the secret is for, shown alongside it in the web UI. Omitting it leaves the existing one.",
        ),
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
    """Set an Actions secret, creating it or replacing its value.

    Args:
        ctx: The Typer context.
        secret_name: The name of the secret.
        data: The value to store, or `-` to read it from stdin.
        owner: The owner of the repository, or the organization itself.
        repository: The name of the repository, to narrow the owner to one of its repositories.
        description: What the secret is for.
        account_name: Name of the account to use for authentication.
        token: Token for authentication.
        base_url: Base URL of the Gitea platform.

    """
    from typing import Any  # noqa: PLC0415

    from gitea.cli.utils.api import execute_api_command  # noqa: PLC0415
    from gitea.cli.utils.auth import get_auth_params  # noqa: PLC0415
    from gitea.cli.utils.options import reporting_scope_errors  # noqa: PLC0415
    from gitea.client.gitea import Gitea  # noqa: PLC0415

    token, base_url = get_auth_params(
        config_path=ctx.obj.get("config_path"),
        account_name=account_name,
        token=token,
        base_url=base_url,
    )

    def api_call() -> tuple[dict[str, Any] | list[dict[str, Any]], dict[str, Any]]:
        """Set the secret.

        Returns:
            A tuple containing an empty object - neither answer carries a body -
            and metadata, whose status code says whether the secret was created
            or replaced.

        """
        value = read_secret_data(data)

        with reporting_scope_errors(COMMAND_NAME), Gitea(token=token, base_url=base_url) as client:
            return client.actions.create_or_update_secret(
                secret_name=secret_name,
                data=value,
                owner=owner,
                repository=repository,
                description=description,
            )

    execute_api_command(api_call=api_call, base_url=base_url, command_name=COMMAND_NAME)
