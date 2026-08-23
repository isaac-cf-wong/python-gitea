"""CLI commands for Gitea Actions.

The commands are grouped by what they address, which is also the order an
automation reaches for them: a `workflow` is the file in the repository and what
is dispatched, a `run` is one execution of it and what carries the status, and a
`job` is a step of a run and what carries the logs.

    gitea-cli actions workflow dispatch --workflow-id build.yml --ref main
    gitea-cli actions run list --status in_progress
    gitea-cli actions run jobs --run-id 42
    gitea-cli actions job logs --job-id 118

Every command here addresses a repository, since Gitea offers no owner-wide form
of these endpoints.
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
    help="Commands for inspecting Actions workflow runs.",
    rich_markup_mode="rich",
)

job_app = typer.Typer(
    name="job",
    help="Commands for inspecting the jobs of an Actions workflow run.",
    rich_markup_mode="rich",
)


def register_commands() -> None:
    """Register the Actions commands to their groups, and the groups to the app."""
    from gitea.cli.actions.job.get import get_job_command  # noqa: PLC0415
    from gitea.cli.actions.job.logs import job_logs_command  # noqa: PLC0415
    from gitea.cli.actions.run.get import get_run_command  # noqa: PLC0415
    from gitea.cli.actions.run.jobs import list_run_jobs_command  # noqa: PLC0415
    from gitea.cli.actions.run.list import list_runs_command  # noqa: PLC0415
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

    run_app.command("list", help="List workflow runs, most recent first.")(list_runs_command)
    run_app.command("get", help="Get one workflow run, including its status and conclusion.")(get_run_command)
    run_app.command("jobs", help="List the jobs of one workflow run.")(list_run_jobs_command)

    job_app.command("get", help="Get one job of a workflow run, including its steps.")(get_job_command)
    job_app.command(
        "logs",
        help=(
            "Print the logs of one job. Text output is the log itself, so it can be piped or redirected; "
            "'--output json' wraps it in the envelope instead."
        ),
    )(job_logs_command)

    actions_app.add_typer(workflow_app, name="workflow", help="Commands for managing Actions workflows.")
    actions_app.add_typer(run_app, name="run", help="Commands for inspecting Actions workflow runs.")
    actions_app.add_typer(job_app, name="job", help="Commands for inspecting the jobs of a workflow run.")


register_commands()
