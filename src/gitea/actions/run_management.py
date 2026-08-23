"""Acting on an Actions workflow run: cancelling, approving, rerunning, deleting.

The rest of the Actions resource reads. These four write, and what they answer
with is worth knowing before calling them:

* Cancelling and approving answer `200` with the run as it now stands, so the
  result says what the request did rather than only that it was accepted.
* Rerunning answers `201` with the run, except for the failed-jobs form, which
  answers `201` with no body at all. An empty result there is a rerun that
  started, not one that failed.
* Deleting answers `204`, as a delete does everywhere in this API.

None of them has an owner-wide form: a run belongs to a repository, and so does
every one of these.
"""

from __future__ import annotations

from typing import Any, cast

from requests import Response

from gitea.actions.base import BaseActions
from gitea.resource.resource import Resource
from gitea.utils.response import process_response


class RunManagement(BaseActions, Resource):
    """The Actions endpoints that act on a workflow run."""

    def _cancel_workflow_run(
        self, owner: str, repository: str, run_id: int, force: bool = False, **kwargs: Any
    ) -> Response:
        """Cancel a workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.
            force: Whether to mark the run cancelled without waiting for its
                jobs to stop.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._cancel_workflow_run_endpoint(owner=owner, repository=repository, run_id=run_id, force=force)
        return self._post(endpoint=endpoint, **kwargs)

    def cancel_workflow_run(
        self, owner: str, repository: str, run_id: int, force: bool = False, **kwargs: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Cancel a workflow run.

        Cancelling asks the run's jobs to stop and waits for them to notice,
        which a job whose runner has gone away never does. `force` marks the run
        cancelled regardless - a different endpoint, not a retry of the same one -
        and is what gets a run stuck in `in_progress` out of the way.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.
            force: Whether to mark the run cancelled without waiting for its
                jobs to stop.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the run as it now stands - its `status` is what
            says whether the cancellation has taken effect yet - and a dictionary
            with metadata.

        """
        response = self._cancel_workflow_run(owner=owner, repository=repository, run_id=run_id, force=force, **kwargs)
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _approve_workflow_run(self, owner: str, repository: str, run_id: int, **kwargs: Any) -> Response:
        """Approve a workflow run that is waiting for approval.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._approve_workflow_run_endpoint(owner=owner, repository=repository, run_id=run_id)
        return self._post(endpoint=endpoint, **kwargs)

    def approve_workflow_run(
        self, owner: str, repository: str, run_id: int, **kwargs: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Approve a workflow run that is waiting for approval.

        A run triggered by a first-time contributor's pull request, or one whose
        jobs target an environment with a protection rule, sits in `blocked`
        until someone with write access approves it. This is that approval; a run
        that was not waiting for one answers `409`.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the run as it now stands and a dictionary with
            metadata.

        """
        response = self._approve_workflow_run(owner=owner, repository=repository, run_id=run_id, **kwargs)
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _rerun_workflow_run(
        self, owner: str, repository: str, run_id: int, failed_jobs_only: bool = False, **kwargs: Any
    ) -> Response:
        """Rerun a workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.
            failed_jobs_only: Whether to rerun only the jobs that failed.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._rerun_workflow_run_endpoint(
            owner=owner, repository=repository, run_id=run_id, failed_jobs_only=failed_jobs_only
        )
        return self._post(endpoint=endpoint, **kwargs)

    def rerun_workflow_run(
        self, owner: str, repository: str, run_id: int, failed_jobs_only: bool = False, **kwargs: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Rerun a workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.
            failed_jobs_only: Whether to rerun only the jobs that failed, which
                is a different endpoint and the one to reach for when a run
                failed on one flaky job out of many.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the run the rerun is on and a dictionary with
            metadata. The failed-jobs form answers `201` with no body, so an
            empty payload with a `201` status is a rerun that started rather than
            one that failed.

        """
        response = self._rerun_workflow_run(
            owner=owner, repository=repository, run_id=run_id, failed_jobs_only=failed_jobs_only, **kwargs
        )
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _rerun_workflow_job(self, owner: str, repository: str, run_id: int, job_id: int, **kwargs: Any) -> Response:
        """Rerun one job of a workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run the job belongs to.
            job_id: The ID of the job.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._rerun_workflow_job_endpoint(owner=owner, repository=repository, run_id=run_id, job_id=job_id)
        return self._post(endpoint=endpoint, **kwargs)

    def rerun_workflow_job(
        self, owner: str, repository: str, run_id: int, job_id: int, **kwargs: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Rerun one job of a workflow run.

        This is the one job endpoint that takes the run as well: reading a job
        takes the job alone, because Gitea addresses one directly, but the rerun
        goes through the run it belongs to.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run the job belongs to.
            job_id: The ID of the job.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the job the rerun is on and a dictionary with
            metadata.

        """
        response = self._rerun_workflow_job(owner=owner, repository=repository, run_id=run_id, job_id=job_id, **kwargs)
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _delete_workflow_run(self, owner: str, repository: str, run_id: int, **kwargs: Any) -> Response:
        """Delete a workflow run.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._get_workflow_run_endpoint(owner=owner, repository=repository, run_id=run_id)
        return self._delete(endpoint=endpoint, **kwargs)

    def delete_workflow_run(
        self, owner: str, repository: str, run_id: int, **kwargs: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Delete a workflow run, its jobs, its logs and its artifacts.

        A run that has not finished cannot be deleted; cancel it first. What is
        deleted goes with it, so this is how a repository is cleared of the logs
        and artifacts of a run rather than only of the run's entry.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing an empty dictionary - the endpoint answers `204`
            with no body - and a dictionary with metadata.

        """
        response = self._delete_workflow_run(owner=owner, repository=repository, run_id=run_id, **kwargs)
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}
