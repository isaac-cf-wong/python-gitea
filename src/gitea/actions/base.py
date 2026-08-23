"""Base class for the Gitea Actions resource: every path it addresses, in one place.

The Actions endpoints differ from the rest of this API in three ways worth knowing
before reading the methods below.

**Most listings answer with an object, and some do not.**
`/actions/workflows`, `/actions/runs`, `/actions/runs/{run}/jobs`,
`/actions/artifacts` and `/actions/runners` each answer with an object carrying
`total_count` and the array under a key of its own (`workflows`,
`workflow_runs`, `jobs`, `artifacts`, `runners`). So those listing methods hand
back a dictionary where `list_labels` and its neighbours hand back a list, and
their default for a response without a body is the empty object rather than the
empty list. The secret and variable listings are the exception: those two answer
with a bare array, as the rest of the API does, and so hand back a list and fall
back to the empty one. The difference is Gitea's, not this library's, and a
caller reading `["secrets"]` off a secret listing is reading a key that endpoint
never sends.

**Two endpoints do not answer with JSON at all.** The logs of a job are the log
file, and an artifact is the zip archive; `get_workflow_job_logs` therefore hands
back text and `download_artifact` hands back bytes. Both are the payload itself
rather than a parsed body, and neither response has a field naming what it
carries - which is why the CLI commands over them add the job or the artifact
they asked for.

**Most of the API exists at four scopes.** Secrets, variables, runners and the
run and job listings belong to a repository, to an organization, to the
authenticated account or to the instance, and the path differs while the request
does not. Which one a call means is decided by the coordinates it was given, and
`gitea.actions.scope` is where that decision and its refusals live; the builders
here name the scopes their endpoint offers and let it reject the rest. The
workflow endpoints, the run management endpoints and the artifact endpoints have
no form but the repository one.
"""

from __future__ import annotations

from typing import Any

from gitea.actions.scope import EVERY_SCOPE, ORGANIZATION, REPOSITORY, REPOSITORY_ONLY, USER, resolve_scope

# The scopes each family of endpoints is offered at, declared once so that a
# refusal is the same refusal from the client and from the CLI.
#
# A secret can be set and deleted for the authenticated account but not listed
# there - Gitea offers no `GET /user/actions/secrets` - and neither secrets nor
# variables have an instance-wide form. Runners and the run and job listings have
# all four.
SECRET_SCOPES = frozenset({REPOSITORY, ORGANIZATION})
SECRET_ENTRY_SCOPES = SECRET_SCOPES | {USER}
VARIABLE_SCOPES = SECRET_ENTRY_SCOPES
RUNNER_SCOPES = EVERY_SCOPE
LISTING_SCOPES = EVERY_SCOPE


def _query_flag(value: bool) -> str:
    """Spell a boolean query parameter the way the API documents it.

    Neither HTTP client sends a Python `bool` usefully: `yarl`, which the
    asynchronous client builds its URLs with, refuses one outright, and
    `requests` would encode it as `True` - which Gitea's parser happens to
    accept, so the two clients would disagree about the same call without
    either of them failing. Both are given `true` or `false` instead.

    Args:
        value: The flag as the caller passed it.

    Returns:
        The flag as it is written in a query string.

    """
    return "true" if value else "false"


class BaseActions:
    """Base class for the Gitea Actions resource."""

    def _repository_actions_endpoint(self, owner: str, repository: str) -> str:
        """Construct the path a repository's Actions endpoints sit under.

        The families with no owner-wide form - workflows, run management and
        artifacts - all start here, so the path is built in one place rather than
        spelled out in each of them.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.

        Returns:
            The path of the repository's Actions endpoints.

        """
        _, endpoint = resolve_scope(owner=owner, repository=repository, offered=REPOSITORY_ONLY)
        return endpoint

    def _list_workflows_endpoint(self, owner: str, repository: str) -> str:
        """Construct the endpoint URL for listing a repository's workflows.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.

        Returns:
            The endpoint URL for listing workflows.

        """
        return f"{self._repository_actions_endpoint(owner=owner, repository=repository)}/workflows"

    def _get_workflow_endpoint(self, owner: str, repository: str, workflow_id: str) -> str:
        """Construct the endpoint URL for one workflow of a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            workflow_id: The workflow's file name, such as `build.yml`.

        Returns:
            The endpoint URL of the workflow.

        """
        return f"{self._list_workflows_endpoint(owner=owner, repository=repository)}/{workflow_id}"

    def _dispatch_workflow_endpoint(self, owner: str, repository: str, workflow_id: str) -> str:
        """Construct the endpoint URL for dispatching a workflow.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            workflow_id: The workflow's file name, such as `build.yml`.

        Returns:
            The endpoint URL for dispatching the workflow.

        """
        return f"{self._get_workflow_endpoint(owner=owner, repository=repository, workflow_id=workflow_id)}/dispatches"

    def _dispatch_workflow_helper(
        self,
        owner: str,
        repository: str,
        workflow_id: str,
        ref: str,
        inputs: dict[str, str] | None = None,
        return_run_details: bool | None = None,
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        """Get the endpoint, parameters and body for dispatching a workflow.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            workflow_id: The workflow's file name, such as `build.yml`.
            ref: The branch or tag to run the workflow on, such as
                `refs/heads/main` or `main`.
            inputs: The `workflow_dispatch` inputs, as the workflow declares
                them. Gitea takes them as strings.
            return_run_details: Whether to ask the response to identify the run
                that was started. The endpoint answers `204` without a body
                unless this is set, so a caller that wants to follow the run it
                just started asks for it here rather than guessing which run is
                its own. Instances older than the parameter ignore it and answer
                `204` as before.

        Returns:
            A tuple containing the endpoint, the query parameters and the
            request body.

        """
        endpoint = self._dispatch_workflow_endpoint(owner=owner, repository=repository, workflow_id=workflow_id)

        params: dict[str, Any] = {}
        if return_run_details is not None:
            params["return_run_details"] = _query_flag(return_run_details)

        payload: dict[str, Any] = {"ref": ref}
        if inputs is not None:
            payload["inputs"] = inputs

        return endpoint, params, payload

    def _list_workflow_runs_endpoint(
        self,
        owner: str | None = None,
        repository: str | None = None,
        workflow_id: str | None = None,
        admin: bool = False,
    ) -> str:
        """Construct the endpoint URL for listing workflow runs.

        Args:
            owner: The owner of the repository, or the organization whose runs
                are listed.
            repository: The name of the repository, to list its runs alone.
            workflow_id: The workflow's file name, such as `build.yml`, to list
                the runs of that workflow alone. None lists the runs of every
                workflow in the scope.
            admin: Whether to list the runs of the whole instance.

        Returns:
            The endpoint URL for listing workflow runs.

        Raises:
            ValueError: If a workflow is named outside a repository, since only a
                repository's runs can be narrowed to one of its workflows.

        """
        scope, endpoint = resolve_scope(owner=owner, repository=repository, admin=admin, offered=LISTING_SCOPES)
        if workflow_id is None:
            return f"{endpoint}/runs"
        if scope != REPOSITORY:
            raise ValueError(
                f"only a repository's runs can be narrowed to one workflow, and {workflow_id!r} was asked for "
                f"outside one: pass `repository` too, or drop `workflow_id`."
            )
        return f"{self._get_workflow_endpoint(owner=owner, repository=repository, workflow_id=workflow_id)}/runs"

    def _list_workflow_runs_helper(
        self,
        owner: str | None = None,
        repository: str | None = None,
        workflow_id: str | None = None,
        admin: bool = False,
        event: str | None = None,
        branch: str | None = None,
        status: str | None = None,
        actor: str | None = None,
        head_sha: str | None = None,
        exclude_pull_requests: bool | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing workflow runs.

        Args:
            owner: The owner of the repository, or the organization whose runs
                are listed.
            repository: The name of the repository, to list its runs alone.
            workflow_id: The workflow's file name, such as `build.yml`, to list
                the runs of that workflow alone.
            admin: Whether to list the runs of the whole instance.
            event: The event that triggered the run, such as `push`.
            branch: The branch the run is on.
            status: The status of the run: `pending`, `queued`, `in_progress`,
                `failure`, `success` or `skipped`.
            actor: The user who triggered the run.
            head_sha: The commit the run was triggered for.
            exclude_pull_requests: Whether to leave the `pull_requests` field of
                each run empty. Only a repository's listing takes it.
            page: The page number for pagination.
            limit: The number of runs per page.

        Returns:
            A tuple containing the endpoint and the query parameters.

        Raises:
            ValueError: If the pull requests are asked to be excluded from a
                listing that is not a repository's, since the wider listings do
                not offer the parameter and would answer with the field filled
                in as though it had never been asked for.

        """
        endpoint = self._list_workflow_runs_endpoint(
            owner=owner, repository=repository, workflow_id=workflow_id, admin=admin
        )
        if exclude_pull_requests is not None and repository is None:
            raise ValueError(
                "only a repository's run listing can leave out the pull requests of each run; "
                "the wider listings send them whatever is asked."
            )

        params: dict[str, Any] = {}
        if event is not None:
            params["event"] = event
        if branch is not None:
            params["branch"] = branch
        if status is not None:
            params["status"] = status
        if actor is not None:
            params["actor"] = actor
        if head_sha is not None:
            params["head_sha"] = head_sha
        if exclude_pull_requests is not None:
            params["exclude_pull_requests"] = _query_flag(exclude_pull_requests)
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        return endpoint, params

    def _get_workflow_run_endpoint(self, owner: str, repository: str, run_id: int) -> str:
        """Construct the endpoint URL for one workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.

        Returns:
            The endpoint URL of the run.

        """
        return f"{self._repository_actions_endpoint(owner=owner, repository=repository)}/runs/{run_id}"

    def _list_workflow_run_jobs_endpoint(self, owner: str, repository: str, run_id: int) -> str:
        """Construct the endpoint URL for listing the jobs of a workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.

        Returns:
            The endpoint URL for listing the run's jobs.

        """
        return f"{self._get_workflow_run_endpoint(owner=owner, repository=repository, run_id=run_id)}/jobs"

    def _list_workflow_run_jobs_helper(
        self,
        owner: str,
        repository: str,
        run_id: int,
        status: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing the jobs of a workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.
            status: The status of the jobs to list: `pending`, `queued`,
                `in_progress`, `failure`, `success` or `skipped`.
            page: The page number for pagination.
            limit: The number of jobs per page.

        Returns:
            A tuple containing the endpoint and the query parameters.

        """
        endpoint = self._list_workflow_run_jobs_endpoint(owner=owner, repository=repository, run_id=run_id)

        params: dict[str, Any] = {}
        if status is not None:
            params["status"] = status
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        return endpoint, params

    def _get_workflow_job_endpoint(self, owner: str, repository: str, job_id: int) -> str:
        """Construct the endpoint URL for one job of a workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            job_id: The ID of the job.

        Returns:
            The endpoint URL of the job.

        """
        return f"{self._repository_actions_endpoint(owner=owner, repository=repository)}/jobs/{job_id}"

    def _get_workflow_job_logs_endpoint(self, owner: str, repository: str, job_id: int) -> str:
        """Construct the endpoint URL for the logs of one job.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            job_id: The ID of the job.

        Returns:
            The endpoint URL of the job's logs.

        """
        return f"{self._get_workflow_job_endpoint(owner=owner, repository=repository, job_id=job_id)}/logs"

    def _list_workflow_jobs_helper(
        self,
        owner: str | None = None,
        repository: str | None = None,
        admin: bool = False,
        status: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing the jobs of a whole scope.

        This is the listing of every job the scope has, which is a different
        endpoint from `_list_workflow_run_jobs_helper` - the jobs of one run.
        The wide one is how a caller finds the job that is holding a queue up
        without walking every run to get to it.

        Args:
            owner: The owner of the repository, or the organization whose jobs
                are listed.
            repository: The name of the repository, to list its jobs alone.
            admin: Whether to list the jobs of the whole instance.
            status: The status of the jobs to list: `pending`, `queued`,
                `in_progress`, `failure`, `success` or `skipped`.
            page: The page number for pagination.
            limit: The number of jobs per page.

        Returns:
            A tuple containing the endpoint and the query parameters.

        """
        _, actions = resolve_scope(owner=owner, repository=repository, admin=admin, offered=LISTING_SCOPES)

        params: dict[str, Any] = {}
        if status is not None:
            params["status"] = status
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        return f"{actions}/jobs", params

    def _cancel_workflow_run_endpoint(self, owner: str, repository: str, run_id: int, force: bool = False) -> str:
        """Construct the endpoint URL for cancelling a workflow run.

        Gitea has two endpoints for this and they are not the same request.
        `cancel` asks the run to stop and waits for its jobs to notice, which a
        job whose runner has gone away never does; `force-cancel` marks the run
        cancelled regardless, and is the one that gets a stuck run out of the
        way. Neither is a fallback for the other, so which one is meant is said
        here rather than guessed.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.
            force: Whether to mark the run cancelled without waiting for its
                jobs to stop.

        Returns:
            The endpoint URL for cancelling the run.

        """
        run = self._get_workflow_run_endpoint(owner=owner, repository=repository, run_id=run_id)
        return f"{run}/force-cancel" if force else f"{run}/cancel"

    def _approve_workflow_run_endpoint(self, owner: str, repository: str, run_id: int) -> str:
        """Construct the endpoint URL for approving a workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.

        Returns:
            The endpoint URL for approving the run.

        """
        return f"{self._get_workflow_run_endpoint(owner=owner, repository=repository, run_id=run_id)}/approve"

    def _rerun_workflow_run_endpoint(
        self, owner: str, repository: str, run_id: int, failed_jobs_only: bool = False
    ) -> str:
        """Construct the endpoint URL for rerunning a workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.
            failed_jobs_only: Whether to rerun only the jobs of the run that
                failed, rather than all of them.

        Returns:
            The endpoint URL for rerunning the run.

        """
        run = self._get_workflow_run_endpoint(owner=owner, repository=repository, run_id=run_id)
        return f"{run}/rerun-failed-jobs" if failed_jobs_only else f"{run}/rerun"

    def _rerun_workflow_job_endpoint(self, owner: str, repository: str, run_id: int, job_id: int) -> str:
        """Construct the endpoint URL for rerunning one job of a workflow run.

        This is the one job endpoint addressed through its run: reading a job
        takes the job alone, because Gitea addresses one directly, but rerunning
        it goes through the run the rerun belongs to.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run the job belongs to.
            job_id: The ID of the job.

        Returns:
            The endpoint URL for rerunning the job.

        """
        run = self._get_workflow_run_endpoint(owner=owner, repository=repository, run_id=run_id)
        return f"{run}/jobs/{job_id}/rerun"

    def _list_artifacts_endpoint(self, owner: str, repository: str, run_id: int | None = None) -> str:
        """Construct the endpoint URL for listing artifacts.

        As with the run listing, naming a run addresses a different endpoint
        rather than adding a filter to the same one.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run whose artifacts are listed. None lists
                every artifact of the repository.

        Returns:
            The endpoint URL for listing artifacts.

        """
        if run_id is None:
            return f"{self._repository_actions_endpoint(owner=owner, repository=repository)}/artifacts"
        return f"{self._get_workflow_run_endpoint(owner=owner, repository=repository, run_id=run_id)}/artifacts"

    def _list_artifacts_helper(
        self, owner: str, repository: str, run_id: int | None = None, name: str | None = None
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing artifacts.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run whose artifacts are listed.
            name: The name of the artifact, to list the artifacts uploaded under
                that name alone. A run that uploads one artifact per job has
                several artifacts of the same name, so this narrows rather than
                identifies.

        Returns:
            A tuple containing the endpoint and the query parameters.

        """
        endpoint = self._list_artifacts_endpoint(owner=owner, repository=repository, run_id=run_id)

        params: dict[str, Any] = {}
        if name is not None:
            params["name"] = name

        return endpoint, params

    def _get_artifact_endpoint(self, owner: str, repository: str, artifact_id: int) -> str:
        """Construct the endpoint URL for one artifact.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            artifact_id: The ID of the artifact.

        Returns:
            The endpoint URL of the artifact.

        """
        actions = self._repository_actions_endpoint(owner=owner, repository=repository)
        return f"{actions}/artifacts/{artifact_id}"

    def _download_artifact_endpoint(self, owner: str, repository: str, artifact_id: int) -> str:
        """Construct the endpoint URL for downloading an artifact's archive.

        The endpoint answers `302` and redirects to the blob, so the request that
        reaches it is followed rather than read; both HTTP clients follow a
        redirect by default, and what arrives is the zip archive itself.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            artifact_id: The ID of the artifact.

        Returns:
            The endpoint URL of the artifact's archive.

        """
        return f"{self._get_artifact_endpoint(owner=owner, repository=repository, artifact_id=artifact_id)}/zip"

    def _list_secrets_helper(
        self,
        owner: str | None = None,
        repository: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing the secrets of a scope.

        A secret's value is never listed - Gitea stores it write-only - so the
        entries carry the name, the description and when it was set, and that is
        all there is to read back.

        Args:
            owner: The owner of the repository, or the organization whose secrets
                are listed.
            repository: The name of the repository, to list its secrets alone.
            page: The page number for pagination.
            limit: The number of secrets per page.

        Returns:
            A tuple containing the endpoint and the query parameters.

        """
        _, actions = resolve_scope(owner=owner, repository=repository, offered=SECRET_SCOPES)

        params: dict[str, Any] = {}
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        return f"{actions}/secrets", params

    def _secret_endpoint(self, secret_name: str, owner: str | None = None, repository: str | None = None) -> str:
        """Construct the endpoint URL for one secret of a scope.

        Args:
            secret_name: The name of the secret.
            owner: The owner of the repository, or the organization the secret
                belongs to.
            repository: The name of the repository the secret belongs to.

        Returns:
            The endpoint URL of the secret.

        """
        _, actions = resolve_scope(owner=owner, repository=repository, offered=SECRET_ENTRY_SCOPES)
        return f"{actions}/secrets/{secret_name}"

    def _create_or_update_secret_helper(
        self,
        secret_name: str,
        data: str,
        owner: str | None = None,
        repository: str | None = None,
        description: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and body for setting a secret.

        One endpoint both creates and updates: Gitea answers `201` when the
        secret was new and `204` when it replaced one, and neither answer carries
        a body. So a caller that needs to know which it did reads the status code,
        and one that only needs the secret to hold the value it passed does not
        have to look first.

        Args:
            secret_name: The name of the secret.
            data: The value to store. It is write-only: no endpoint reads it back.
            owner: The owner of the repository, or the organization the secret
                belongs to.
            repository: The name of the repository the secret belongs to.
            description: What the secret is for, shown alongside it in the web
                UI. Omitted rather than sent empty when it was not given, so
                setting a secret does not clear the description it had.

        Returns:
            A tuple containing the endpoint and the request body.

        """
        endpoint = self._secret_endpoint(secret_name=secret_name, owner=owner, repository=repository)

        payload: dict[str, Any] = {"data": data}
        if description is not None:
            payload["description"] = description

        return endpoint, payload

    def _list_variables_helper(
        self,
        owner: str | None = None,
        repository: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing the variables of a scope.

        A variable is the readable counterpart of a secret: its value comes back
        in the listing, under `data`.

        Args:
            owner: The owner of the repository, or the organization whose
                variables are listed.
            repository: The name of the repository, to list its variables alone.
            page: The page number for pagination.
            limit: The number of variables per page.

        Returns:
            A tuple containing the endpoint and the query parameters.

        """
        _, actions = resolve_scope(owner=owner, repository=repository, offered=VARIABLE_SCOPES)

        params: dict[str, Any] = {}
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        return f"{actions}/variables", params

    def _variable_endpoint(self, variable_name: str, owner: str | None = None, repository: str | None = None) -> str:
        """Construct the endpoint URL for one variable of a scope.

        Args:
            variable_name: The name of the variable.
            owner: The owner of the repository, or the organization the variable
                belongs to.
            repository: The name of the repository the variable belongs to.

        Returns:
            The endpoint URL of the variable.

        """
        _, actions = resolve_scope(owner=owner, repository=repository, offered=VARIABLE_SCOPES)
        return f"{actions}/variables/{variable_name}"

    def _create_variable_helper(
        self,
        variable_name: str,
        value: str,
        owner: str | None = None,
        repository: str | None = None,
        description: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and body for creating a variable.

        Creating and updating are two endpoints here, where a secret has one: a
        `POST` to a name that already exists answers `409` rather than replacing
        it. So creating a variable is safe to retry against a name a caller
        believes to be free, and replacing one is asked for explicitly.

        Args:
            variable_name: The name of the variable to create.
            value: The value to store.
            owner: The owner of the repository, or the organization the variable
                belongs to.
            repository: The name of the repository the variable belongs to.
            description: What the variable is for, shown alongside it in the web
                UI.

        Returns:
            A tuple containing the endpoint and the request body.

        """
        endpoint = self._variable_endpoint(variable_name=variable_name, owner=owner, repository=repository)

        payload: dict[str, Any] = {"value": value}
        if description is not None:
            payload["description"] = description

        return endpoint, payload

    def _update_variable_helper(
        self,
        variable_name: str,
        value: str,
        owner: str | None = None,
        repository: str | None = None,
        new_name: str | None = None,
        description: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and body for updating a variable.

        Args:
            variable_name: The name of the variable to update, which is the one
                the endpoint is addressed by.
            value: The value to store. The endpoint requires it, so an update
                that only means to rename a variable still sends the value it is
                to keep.
            owner: The owner of the repository, or the organization the variable
                belongs to.
            repository: The name of the repository the variable belongs to.
            new_name: A name to rename the variable to. It reaches the body as
                `name`, which is what Gitea calls it; omitting it leaves the name
                alone, and sending it empty would too.
            description: What the variable is for.

        Returns:
            A tuple containing the endpoint and the request body.

        """
        endpoint = self._variable_endpoint(variable_name=variable_name, owner=owner, repository=repository)

        payload: dict[str, Any] = {"value": value}
        if new_name is not None:
            payload["name"] = new_name
        if description is not None:
            payload["description"] = description

        return endpoint, payload

    def _list_runners_helper(
        self,
        owner: str | None = None,
        repository: str | None = None,
        admin: bool = False,
        disabled: bool | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing the runners of a scope.

        A runner registered at a wider scope runs the jobs of everything under
        it, and a scope's listing shows the runners registered *to that scope*
        rather than every runner that could pick up its jobs. So a repository
        whose jobs are all run by an organization runner has an empty listing of
        its own, which is not the same as having nowhere to run them.

        Args:
            owner: The owner of the repository, or the organization whose runners
                are listed.
            repository: The name of the repository, to list its runners alone.
            admin: Whether to list the runners of the whole instance.
            disabled: Whether to list the disabled runners rather than the
                enabled ones. Omitted when it was not asked about, which is what
                lists both.

        Returns:
            A tuple containing the endpoint and the query parameters.

        """
        _, actions = resolve_scope(owner=owner, repository=repository, admin=admin, offered=RUNNER_SCOPES)

        params: dict[str, Any] = {}
        if disabled is not None:
            params["disabled"] = _query_flag(disabled)

        return f"{actions}/runners", params

    def _runner_endpoint(
        self,
        runner_id: int,
        owner: str | None = None,
        repository: str | None = None,
        admin: bool = False,
    ) -> str:
        """Construct the endpoint URL for one runner of a scope.

        A runner is addressed through the scope it is registered to, so reading a
        runner by ID through a scope it does not belong to answers `404` even
        though the ID exists.

        Args:
            runner_id: The ID of the runner.
            owner: The owner of the repository, or the organization the runner
                belongs to.
            repository: The name of the repository the runner belongs to.
            admin: Whether the runner is registered to the whole instance.

        Returns:
            The endpoint URL of the runner.

        """
        _, actions = resolve_scope(owner=owner, repository=repository, admin=admin, offered=RUNNER_SCOPES)
        return f"{actions}/runners/{runner_id}"

    def _update_runner_helper(
        self,
        runner_id: int,
        disabled: bool,
        owner: str | None = None,
        repository: str | None = None,
        admin: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and body for updating a runner.

        Disabling is the only field Gitea offers here, and it is required rather
        than optional: there is no partial update to make of a runner, so an
        update always says which of the two states it means.

        Args:
            runner_id: The ID of the runner.
            disabled: Whether the runner is to stop taking jobs.
            owner: The owner of the repository, or the organization the runner
                belongs to.
            repository: The name of the repository the runner belongs to.
            admin: Whether the runner is registered to the whole instance.

        Returns:
            A tuple containing the endpoint and the request body.

        """
        endpoint = self._runner_endpoint(runner_id=runner_id, owner=owner, repository=repository, admin=admin)
        return endpoint, {"disabled": disabled}

    def _runner_registration_token_endpoint(
        self, owner: str | None = None, repository: str | None = None, admin: bool = False
    ) -> str:
        """Construct the endpoint URL for a scope's runner registration token.

        The token is what `act_runner register` is given, and it is the scope's
        rather than one runner's: a token taken from an organization registers a
        runner to that organization, whatever repository the runner then runs
        jobs for.

        Args:
            owner: The owner of the repository, or the organization to register
                a runner to.
            repository: The name of the repository to register a runner to.
            admin: Whether to register a runner to the whole instance.

        Returns:
            The endpoint URL of the scope's registration token.

        """
        _, actions = resolve_scope(owner=owner, repository=repository, admin=admin, offered=RUNNER_SCOPES)
        return f"{actions}/runners/registration-token"
