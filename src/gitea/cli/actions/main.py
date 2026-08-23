"""CLI commands for Gitea Actions.

The commands are grouped by what they address, which is also the order an
automation reaches for them: a `workflow` is the file in the repository and what
is dispatched, a `run` is one execution of it and what carries the status, a `job`
is a step of a run and what carries the logs, and an `artifact` is a file a job
produced.

    gitea-cli actions workflow dispatch --workflow-id build.yml --ref main
    gitea-cli actions run list --status in_progress
    gitea-cli actions run jobs --run-id 42
    gitea-cli actions job logs --job-id 118
    gitea-cli actions artifact download --artifact-id 9 --file dist.zip

Three further groups configure Actions rather than watch it. A `secret` and a
`variable` are what a workflow reads at run time - the first write-only, the
second not - and a `runner` is a machine that executes jobs.

    gitea-cli actions secret set --secret-name DEPLOY_TOKEN --data -
    gitea-cli actions variable list --owner my-org
    gitea-cli actions runner list --admin

Those three, and the `run list` and `job list` commands, exist at several scopes:
`--owner` with `--repository` addresses a repository, `--owner` alone addresses
an organization, omitting both addresses the authenticated account, and `--admin`
addresses the whole instance where Gitea offers that. Not every group offers every
scope - a secret cannot be *listed* for an account, and neither secrets nor
variables have an instance-wide form - and asking for one that does not exist is
reported by name rather than answered with an empty listing.

Everything under `workflow`, `artifact` and the run-management commands addresses
a repository, since Gitea offers no wider form of those.
"""

from __future__ import annotations

import typer

actions_app = typer.Typer(
    name="actions",
    help="Commands for Gitea Actions.",
    rich_markup_mode="rich",
)

workflow_app = typer.Typer(
    name="workflow",
    help="Commands for managing Actions workflows.",
    rich_markup_mode="rich",
)

run_app = typer.Typer(
    name="run",
    help="Commands for inspecting and acting on Actions workflow runs.",
    rich_markup_mode="rich",
)

job_app = typer.Typer(
    name="job",
    help="Commands for the jobs of Actions workflow runs.",
    rich_markup_mode="rich",
)

artifact_app = typer.Typer(
    name="artifact",
    help="Commands for the artifacts an Actions run produced.",
    rich_markup_mode="rich",
)

secret_app = typer.Typer(
    name="secret",
    help="Commands for managing Actions secrets.",
    rich_markup_mode="rich",
)

variable_app = typer.Typer(
    name="variable",
    help="Commands for managing Actions variables.",
    rich_markup_mode="rich",
)

runner_app = typer.Typer(
    name="runner",
    help="Commands for managing Actions runners.",
    rich_markup_mode="rich",
)


def register_workflow_commands() -> None:
    """Register the commands over the workflows of a repository."""
    from gitea.cli.actions.workflow.dispatch import dispatch_command  # noqa: PLC0415
    from gitea.cli.actions.workflow.get import get_workflow_command  # noqa: PLC0415
    from gitea.cli.actions.workflow.list import list_workflows_command  # noqa: PLC0415

    workflow_app.command("list", help="List a repository's workflows.")(list_workflows_command)
    workflow_app.command("get", help="Get one workflow of a repository.")(get_workflow_command)
    workflow_app.command(
        "dispatch",
        help=(
            "Start a workflow run. The workflow has to declare the 'workflow_dispatch' trigger a dispatch fires, "
            "and --ref names the branch or tag to run it on."
        ),
    )(dispatch_command)


def register_run_commands() -> None:
    """Register the commands over workflow runs, and over the jobs of one."""
    from gitea.cli.actions.job.get import get_job_command  # noqa: PLC0415
    from gitea.cli.actions.job.list import list_jobs_command  # noqa: PLC0415
    from gitea.cli.actions.job.logs import job_logs_command  # noqa: PLC0415
    from gitea.cli.actions.job.rerun import rerun_job_command  # noqa: PLC0415
    from gitea.cli.actions.run.approve import approve_run_command  # noqa: PLC0415
    from gitea.cli.actions.run.cancel import cancel_run_command  # noqa: PLC0415
    from gitea.cli.actions.run.delete import delete_run_command  # noqa: PLC0415
    from gitea.cli.actions.run.force_cancel import force_cancel_run_command  # noqa: PLC0415
    from gitea.cli.actions.run.get import get_run_command  # noqa: PLC0415
    from gitea.cli.actions.run.jobs import list_run_jobs_command  # noqa: PLC0415
    from gitea.cli.actions.run.list import list_runs_command  # noqa: PLC0415
    from gitea.cli.actions.run.rerun import rerun_run_command  # noqa: PLC0415

    run_app.command(
        "list",
        help=(
            "List workflow runs, most recent first. Names a repository with --owner and --repository, an "
            "organization with --owner alone, the authenticated account with neither, or the instance with --admin."
        ),
    )(list_runs_command)
    run_app.command("get", help="Get one workflow run, including its status and conclusion.")(get_run_command)
    run_app.command("jobs", help="List the jobs of one workflow run.")(list_run_jobs_command)
    run_app.command(
        "cancel",
        help=(
            "Cancel a workflow run, waiting for its jobs to stop. Use 'force-cancel' for a run whose jobs never answer."
        ),
    )(cancel_run_command)
    run_app.command(
        "force-cancel",
        help="Mark a workflow run cancelled without waiting for its jobs, which is what clears a stuck run.",
    )(force_cancel_run_command)
    run_app.command("approve", help="Approve a workflow run that is waiting for approval.")(approve_run_command)
    run_app.command(
        "rerun",
        help="Rerun a workflow run, or with --failed-jobs only the jobs of it that failed.",
    )(rerun_run_command)
    run_app.command(
        "delete",
        help="Delete a workflow run, with the jobs, logs and artifacts it produced. It has to have finished.",
    )(delete_run_command)

    job_app.command(
        "list",
        help=(
            "List every job of a scope, rather than the jobs of one run: '--status queued' finds what is waiting "
            "for a runner."
        ),
    )(list_jobs_command)
    job_app.command("get", help="Get one job of a workflow run, including its steps.")(get_job_command)
    job_app.command(
        "logs",
        help=(
            "Print the logs of one job. Text output is the log itself, so it can be piped or redirected; "
            "'--output json' wraps it in the envelope instead."
        ),
    )(job_logs_command)
    job_app.command("rerun", help="Rerun one job of a workflow run, named by its run and its own ID.")(
        rerun_job_command
    )


def register_artifact_commands() -> None:
    """Register the commands over the artifacts of a repository."""
    from gitea.cli.actions.artifact.delete import delete_artifact_command  # noqa: PLC0415
    from gitea.cli.actions.artifact.download import download_artifact_command  # noqa: PLC0415
    from gitea.cli.actions.artifact.get import get_artifact_command  # noqa: PLC0415
    from gitea.cli.actions.artifact.list import list_artifacts_command  # noqa: PLC0415

    artifact_app.command(
        "list",
        help="List the artifacts of a repository, or with --run-id the artifacts of one run.",
    )(list_artifacts_command)
    artifact_app.command("get", help="Get one artifact, including its size and whether it has expired.")(
        get_artifact_command
    )
    artifact_app.command(
        "download",
        help="Download an artifact's zip archive to the path given by --file. It is not written to stdout.",
    )(download_artifact_command)
    artifact_app.command("delete", help="Delete one artifact's archive, leaving the run it belongs to.")(
        delete_artifact_command
    )


def register_configuration_commands() -> None:
    """Register the commands over the secrets, variables and runners of a scope."""
    from gitea.cli.actions.runner.delete import delete_runner_command  # noqa: PLC0415
    from gitea.cli.actions.runner.get import get_runner_command  # noqa: PLC0415
    from gitea.cli.actions.runner.list import list_runners_command  # noqa: PLC0415
    from gitea.cli.actions.runner.registration_token import runner_registration_token_command  # noqa: PLC0415
    from gitea.cli.actions.runner.update import update_runner_command  # noqa: PLC0415
    from gitea.cli.actions.secret.delete import delete_secret_command  # noqa: PLC0415
    from gitea.cli.actions.secret.list import list_secrets_command  # noqa: PLC0415
    from gitea.cli.actions.secret.set import set_secret_command  # noqa: PLC0415
    from gitea.cli.actions.variable.create import create_variable_command  # noqa: PLC0415
    from gitea.cli.actions.variable.delete import delete_variable_command  # noqa: PLC0415
    from gitea.cli.actions.variable.get import get_variable_command  # noqa: PLC0415
    from gitea.cli.actions.variable.list import list_variables_command  # noqa: PLC0415
    from gitea.cli.actions.variable.update import update_variable_command  # noqa: PLC0415

    secret_app.command(
        "list",
        help=(
            "List the secrets of a repository or an organization. Values are never listed: Gitea stores them "
            "write-only."
        ),
    )(list_secrets_command)
    secret_app.command(
        "set",
        help="Set a secret, creating it or replacing its value. '--data -' reads the value from stdin.",
    )(set_secret_command)
    secret_app.command("delete", help="Delete a secret of a repository, an organization or the account.")(
        delete_secret_command
    )

    variable_app.command("list", help="List the variables of a scope, values included.")(list_variables_command)
    variable_app.command("get", help="Get one variable of a scope, its value under 'data'.")(get_variable_command)
    variable_app.command(
        "create",
        help="Create a variable. A name that already exists is a conflict rather than an overwrite.",
    )(create_variable_command)
    variable_app.command(
        "update",
        help="Update a variable's value, and with --new-name its name. --value is required either way.",
    )(update_variable_command)
    variable_app.command("delete", help="Delete a variable of a scope.")(delete_variable_command)

    runner_app.command(
        "list",
        help="List the runners registered to a scope, which is not every runner that could run its jobs.",
    )(list_runners_command)
    runner_app.command("get", help="Get one runner of a scope, including the labels its jobs are matched by.")(
        get_runner_command
    )
    runner_app.command(
        "update",
        help="Disable or re-enable one runner. --state is required: there is no partial update of a runner.",
    )(update_runner_command)
    runner_app.command("delete", help="Remove one runner's registration from a scope.")(delete_runner_command)
    runner_app.command(
        "registration-token",
        help="Print the token a new runner registers to this scope with. It is a credential; redirect it.",
    )(runner_registration_token_command)


def register_commands() -> None:
    """Register the Actions commands to their groups, and the groups to the app."""
    register_workflow_commands()
    register_run_commands()
    register_artifact_commands()
    register_configuration_commands()

    actions_app.add_typer(workflow_app, name="workflow", help="Commands for managing Actions workflows.")
    actions_app.add_typer(run_app, name="run", help="Commands for inspecting and acting on Actions workflow runs.")
    actions_app.add_typer(job_app, name="job", help="Commands for the jobs of Actions workflow runs.")
    actions_app.add_typer(artifact_app, name="artifact", help="Commands for the artifacts an Actions run produced.")
    actions_app.add_typer(secret_app, name="secret", help="Commands for managing Actions secrets.")
    actions_app.add_typer(variable_app, name="variable", help="Commands for managing Actions variables.")
    actions_app.add_typer(runner_app, name="runner", help="Commands for managing Actions runners.")


register_commands()
