"""The options every resource command shares, and how they are read.

The CLI names a target the same way in every command family:

- `--owner` names the user or organization that owns the target.
- `--repository` narrows the target to one repository of that owner. It is
  optional everywhere. Omitting it asks for the owner-wide target, which is
  what the `project` commands act on; a command whose endpoint has no
  owner-wide form reports that it needs a repository, rather than leaving the
  parser to reject the invocation with a message that never mentions the
  organization case.
- An entity is named by `--<entity>-id`: `--issue-id`, `--project-id`,
  `--column-id`, `--label-id`, `--comment-id`, `--workflow-id`, `--run-id`,
  `--job-id`, `--artifact-id`, `--runner-id`. The two entities Gitea addresses
  by name rather than by number - a secret and a variable - are named by
  `--secret-name` and `--variable-name`, since `--secret-id` would promise a
  number the API does not have.
- `--admin` asks for the instance-wide form of an endpoint, where one exists. It
  belongs to no owner, so it is refused together with `--owner`.

A second target in the same command carries its own coordinates, and those are
required together because there is no scope for them to fall back to:
`issue dependency` takes `--dependency-owner`, `--dependency-repository` and
`--dependency-issue-id` for the issue being depended on.

The helpers here are that reading, kept in one place so the wording of the
errors does not drift between command families. They raise `CommandError`, so
call them from inside the `api_call` that `execute_api_command` wraps and the
user sees the message alone rather than a traceback.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from gitea.cli.utils.errors import CommandError

logger = logging.getLogger("gitea")

REPOSITORY_REQUIRED_HELP = (
    "Name of the repository. This command has no organization-wide form, so it cannot be omitted."
)
ISSUE_ID_HELP = "Issue number shown in the web UI."
DEPRECATED_INDEX_HELP = "Deprecated alias of --issue-id."

# The Actions entities. A workflow is named by its file name rather than by a
# number - that is what Gitea's `workflow_id` path parameter takes - so the help
# says so wherever the option is offered, since `--workflow-id build.yml` reads
# like a mistake to anyone expecting the other identifiers here.
WORKFLOW_ID_HELP = "File name of the workflow, as it is named under .gitea/workflows, e.g. build.yml."
RUN_ID_HELP = "ID of the workflow run."
JOB_ID_HELP = "ID of the job of a workflow run."
ARTIFACT_ID_HELP = "ID of the artifact, as 'gitea-cli actions artifact list' reports it."
RUNNER_ID_HELP = "ID of the runner, as 'gitea-cli actions runner list' reports it."
# The help text of an option, not a credential: the name carries the word the
# security check looks for.
SECRET_NAME_HELP = "Name of the secret, which is how Gitea addresses it: there is no numeric ID."  # noqa: S105
VARIABLE_NAME_HELP = "Name of the variable, which is how Gitea addresses it: there is no numeric ID."

# The Actions scopes. Secrets, variables, runners and the run and job listings
# exist for a repository, for an organization, for the authenticated account and -
# for the runners and the listings - for the instance, at paths that differ while
# the request does not. So the coordinates say which is meant, and the help says
# what omitting one asks for, since an option that is optional everywhere gives no
# hint of its own.
OWNER_SCOPE_HELP = (
    "Owner of the repository, or the organization itself. Omit it together with --repository to address the "
    "authenticated account."
)
REPOSITORY_SCOPE_HELP = "Name of the repository. Omit it to address the owner named by --owner instead."
ADMIN_HELP = (
    "Address the whole instance rather than an owner or a repository. Answers only to an administrator's token, "
    "and cannot be combined with --owner."
)


@contextmanager
def reporting_scope_errors(command: str) -> Iterator[None]:
    """Report coordinates that name no endpoint as a CLI error rather than a traceback.

    The rule about which scopes an Actions endpoint has lives in
    `gitea.actions.scope`, once, and is enforced there for every caller - so the
    CLI does not restate it, which is how the two would come to disagree. What it
    does instead is turn the library's `ValueError` into a `CommandError`, so the
    user sees the sentence and not a stack trace.

    Args:
        command: The command being run, named as the user invoked it.

    Yields:
        Nothing; the block runs inside the conversion.

    Raises:
        CommandError: If the block rejected the coordinates it was given.

    """
    try:
        yield
    except ValueError as e:
        raise CommandError(f"'{command}' was given coordinates it cannot address: {e}") from e


def require_repository(repository: str | None, *, command: str) -> str:
    """Read `--repository` for a command whose endpoint always needs one.

    `--repository` is optional on every command, so omitting it is a request
    for the owner-wide target. The commands here have no owner-wide endpoint to
    serve that with, and the error says so instead of letting the request reach
    a URL with an empty path segment in it.

    Args:
        repository: The value passed as --repository, or None when omitted.
        command: The command being run, named as the user invoked it.

    Returns:
        The name of the repository.

    Raises:
        CommandError: If --repository was omitted.

    """
    if repository is None:
        raise CommandError(
            f"'{command}' needs a repository: pass --repository REPOSITORY. "
            f"Omitting --repository asks for the target of the owner itself, which only the "
            f"'gitea-cli project' commands have."
        )
    return repository


def resolve_issue_id(
    *,
    issue_id: int | None,
    index: int | None,
    command: str,
    option: str = "--issue-id",
    deprecated_option: str = "--index",
) -> int:
    """Read the option naming which issue a command acts on.

    The issue is named by `--issue-id` in every command family. The older name
    `--index` is still accepted so that existing scripts keep working, and
    using it logs a deprecation warning naming its replacement.

    Args:
        issue_id: The value passed as the current option, or None when omitted.
        index: The value passed as the deprecated option, or None when omitted.
        command: The command being run, named as the user invoked it.
        option: The current name of the option.
        deprecated_option: The deprecated name of the option.

    Returns:
        The issue the command acts on.

    Raises:
        CommandError: If neither option was passed, or both were passed with
            different values.

    """
    if index is None:
        if issue_id is None:
            raise CommandError(f"'{command}' needs an issue: pass {option} NUMBER.")
        return issue_id

    if issue_id is not None and issue_id != index:
        raise CommandError(
            f"{option} and {deprecated_option} name the same issue but were given different values "
            f"({issue_id} and {index}). {deprecated_option} is the deprecated name of {option}: pass only {option}."
        )

    logger.warning("%s is deprecated and will be removed; pass %s instead.", deprecated_option, option)
    return index if issue_id is None else issue_id
