"""Gitea Actions resource."""

from __future__ import annotations

from typing import Any, cast

from requests import Response

from gitea.actions.base import BaseActions
from gitea.resource.resource import Resource
from gitea.utils.response import process_response, process_text_response


class Actions(BaseActions, Resource):
    """Gitea Actions resource."""

    def _list_workflows(self, owner: str, repository: str, **kwargs: Any) -> Response:
        """List the workflows of a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._list_workflows_endpoint(owner=owner, repository=repository)
        return self._get(endpoint=endpoint, **kwargs)

    def list_workflows(self, owner: str, repository: str, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        """List the workflows of a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the listing - an object carrying `total_count`
            and `workflows`, as the endpoint answers with - and a dictionary
            with metadata.

        """
        response = self._list_workflows(owner=owner, repository=repository, **kwargs)
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _get_workflow(self, owner: str, repository: str, workflow_id: str, **kwargs: Any) -> Response:
        """Get one workflow of a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            workflow_id: The workflow's file name, such as `build.yml`.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._get_workflow_endpoint(owner=owner, repository=repository, workflow_id=workflow_id)
        return self._get(endpoint=endpoint, **kwargs)

    def get_workflow(
        self, owner: str, repository: str, workflow_id: str, **kwargs: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Get one workflow of a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            workflow_id: The workflow's file name, such as `build.yml`.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the workflow as a dictionary and a dictionary
            with metadata.

        """
        response = self._get_workflow(owner=owner, repository=repository, workflow_id=workflow_id, **kwargs)
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _dispatch_workflow(
        self,
        owner: str,
        repository: str,
        workflow_id: str,
        ref: str,
        inputs: dict[str, str] | None = None,
        return_run_details: bool | None = None,
        **kwargs: Any,
    ) -> Response:
        """Start a workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            workflow_id: The workflow's file name, such as `build.yml`.
            ref: The branch or tag to run the workflow on.
            inputs: The `workflow_dispatch` inputs the workflow declares.
            return_run_details: Whether to ask the response to identify the run
                that was started.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params, payload = self._dispatch_workflow_helper(
            owner=owner,
            repository=repository,
            workflow_id=workflow_id,
            ref=ref,
            inputs=inputs,
            return_run_details=return_run_details,
        )
        return self._post(endpoint=endpoint, params=params, json=payload, **kwargs)

    def dispatch_workflow(
        self,
        owner: str,
        repository: str,
        workflow_id: str,
        ref: str,
        inputs: dict[str, str] | None = None,
        return_run_details: bool | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Start a workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            workflow_id: The workflow's file name, such as `build.yml`.
            ref: The branch or tag to run the workflow on.
            inputs: The `workflow_dispatch` inputs the workflow declares.
            return_run_details: Whether to ask the response to identify the run
                that was started.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the run details - `workflow_run_id`, `run_url`
            and `html_url` - when they were asked for and the instance sends
            them, an empty dictionary otherwise, and a dictionary with metadata.
            The endpoint answers `204` without a body unless
            `return_run_details` was set, so an empty payload with a `204`
            status is a dispatch that was accepted rather than one that failed.

        """
        response = self._dispatch_workflow(
            owner=owner,
            repository=repository,
            workflow_id=workflow_id,
            ref=ref,
            inputs=inputs,
            return_run_details=return_run_details,
            **kwargs,
        )
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _list_workflow_runs(
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
        **kwargs: Any,
    ) -> Response:
        """List the workflow runs of a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            workflow_id: The workflow's file name, to list its runs alone.
            event: The event that triggered the run.
            branch: The branch the run is on.
            status: The status of the runs to list.
            actor: The user who triggered the run.
            head_sha: The commit the run was triggered for.
            exclude_pull_requests: Whether to leave each run's
                `pull_requests` field empty.
            page: The page number for pagination.
            limit: The number of runs per page.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_workflow_runs_helper(
            owner=owner,
            repository=repository,
            workflow_id=workflow_id,
            event=event,
            branch=branch,
            status=status,
            actor=actor,
            head_sha=head_sha,
            exclude_pull_requests=exclude_pull_requests,
            page=page,
            limit=limit,
        )
        return self._get(endpoint=endpoint, params=params, **kwargs)

    def list_workflow_runs(
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
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """List the workflow runs of a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            workflow_id: The workflow's file name, to list its runs alone.
            event: The event that triggered the run.
            branch: The branch the run is on.
            status: The status of the runs to list.
            actor: The user who triggered the run.
            head_sha: The commit the run was triggered for.
            exclude_pull_requests: Whether to leave each run's
                `pull_requests` field empty.
            page: The page number for pagination.
            limit: The number of runs per page.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the listing - an object carrying `total_count`
            and `workflow_runs`, as the endpoint answers with - and a dictionary
            with metadata.

        """
        response = self._list_workflow_runs(
            owner=owner,
            repository=repository,
            workflow_id=workflow_id,
            event=event,
            branch=branch,
            status=status,
            actor=actor,
            head_sha=head_sha,
            exclude_pull_requests=exclude_pull_requests,
            page=page,
            limit=limit,
            **kwargs,
        )
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _get_workflow_run(self, owner: str, repository: str, run_id: int, **kwargs: Any) -> Response:
        """Get one workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._get_workflow_run_endpoint(owner=owner, repository=repository, run_id=run_id)
        return self._get(endpoint=endpoint, **kwargs)

    def get_workflow_run(
        self, owner: str, repository: str, run_id: int, **kwargs: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Get one workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the run as a dictionary - its `status` and
            `conclusion` are what say how it went - and a dictionary with
            metadata.

        """
        response = self._get_workflow_run(owner=owner, repository=repository, run_id=run_id, **kwargs)
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _list_workflow_run_jobs(
        self,
        owner: str,
        repository: str,
        run_id: int,
        status: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> Response:
        """List the jobs of a workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.
            status: The status of the jobs to list.
            page: The page number for pagination.
            limit: The number of jobs per page.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_workflow_run_jobs_helper(
            owner=owner,
            repository=repository,
            run_id=run_id,
            status=status,
            page=page,
            limit=limit,
        )
        return self._get(endpoint=endpoint, params=params, **kwargs)

    def list_workflow_run_jobs(
        self,
        owner: str,
        repository: str,
        run_id: int,
        status: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """List the jobs of a workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.
            status: The status of the jobs to list.
            page: The page number for pagination.
            limit: The number of jobs per page.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the listing - an object carrying `total_count`
            and `jobs`, as the endpoint answers with - and a dictionary with
            metadata.

        """
        response = self._list_workflow_run_jobs(
            owner=owner,
            repository=repository,
            run_id=run_id,
            status=status,
            page=page,
            limit=limit,
            **kwargs,
        )
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _get_workflow_job(self, owner: str, repository: str, job_id: int, **kwargs: Any) -> Response:
        """Get one job of a workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            job_id: The ID of the job.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._get_workflow_job_endpoint(owner=owner, repository=repository, job_id=job_id)
        return self._get(endpoint=endpoint, **kwargs)

    def get_workflow_job(
        self, owner: str, repository: str, job_id: int, **kwargs: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Get one job of a workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            job_id: The ID of the job.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the job as a dictionary - including its `steps`,
            each with a `status` and a `conclusion` of its own - and a
            dictionary with metadata.

        """
        response = self._get_workflow_job(owner=owner, repository=repository, job_id=job_id, **kwargs)
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _get_workflow_job_logs(self, owner: str, repository: str, job_id: int, **kwargs: Any) -> Response:
        """Download the logs of one job.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            job_id: The ID of the job.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._get_workflow_job_logs_endpoint(owner=owner, repository=repository, job_id=job_id)
        return self._get(endpoint=endpoint, **kwargs)

    def get_workflow_job_logs(
        self, owner: str, repository: str, job_id: int, **kwargs: Any
    ) -> tuple[str, dict[str, Any]]:
        """Download the logs of one job.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            job_id: The ID of the job.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the log text and a dictionary with metadata. The
            endpoint answers with the log itself rather than with a JSON
            document, so this is the one method here handing back text; a job
            that has produced no output yet answers with an empty string.

        """
        response = self._get_workflow_job_logs(owner=owner, repository=repository, job_id=job_id, **kwargs)
        logs, status_code = process_text_response(response)
        return logs, {"status_code": status_code}
