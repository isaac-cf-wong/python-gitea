"""Base class for the Gitea Actions resource.

The Actions endpoints differ from the rest of this API in one way worth knowing
before reading the methods below: a listing does not answer with a bare JSON
array. `/actions/workflows`, `/actions/runs` and `/actions/runs/{run}/jobs` each
answer with an object carrying `total_count` and the array under a key of its own
(`workflows`, `workflow_runs`, `jobs`). So the listing methods here hand back a
dictionary where `list_labels` and its neighbours hand back a list, and their
default for a response without a body is the empty object rather than the empty
list.

The other difference is the job log endpoint, which answers with the log itself
rather than with a JSON document. `get_workflow_job_logs` therefore returns text,
and is the one method here whose payload is not a parsed body.
"""

from __future__ import annotations

from typing import Any


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

    def _list_workflows_endpoint(self, owner: str, repository: str) -> str:
        """Construct the endpoint URL for listing a repository's workflows.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.

        Returns:
            The endpoint URL for listing workflows.

        """
        return f"/repos/{owner}/{repository}/actions/workflows"

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

    def _list_workflow_runs_endpoint(self, owner: str, repository: str, workflow_id: str | None = None) -> str:
        """Construct the endpoint URL for listing workflow runs.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            workflow_id: The workflow's file name, such as `build.yml`, to list
                the runs of that workflow alone. None lists the runs of every
                workflow in the repository.

        Returns:
            The endpoint URL for listing workflow runs.

        """
        if workflow_id is None:
            return f"/repos/{owner}/{repository}/actions/runs"
        return f"{self._get_workflow_endpoint(owner=owner, repository=repository, workflow_id=workflow_id)}/runs"

    def _list_workflow_runs_helper(
        self,
        owner: str,
        repository: str,
        workflow_id: str | None = None,
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
            owner: The owner of the repository.
            repository: The name of the repository.
            workflow_id: The workflow's file name, such as `build.yml`, to list
                the runs of that workflow alone.
            event: The event that triggered the run, such as `push`.
            branch: The branch the run is on.
            status: The status of the run: `pending`, `queued`, `in_progress`,
                `failure`, `success` or `skipped`.
            actor: The user who triggered the run.
            head_sha: The commit the run was triggered for.
            exclude_pull_requests: Whether to leave the `pull_requests` field of
                each run empty.
            page: The page number for pagination.
            limit: The number of runs per page.

        Returns:
            A tuple containing the endpoint and the query parameters.

        """
        endpoint = self._list_workflow_runs_endpoint(owner=owner, repository=repository, workflow_id=workflow_id)

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
        return f"/repos/{owner}/{repository}/actions/runs/{run_id}"

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
        return f"/repos/{owner}/{repository}/actions/jobs/{job_id}"

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
