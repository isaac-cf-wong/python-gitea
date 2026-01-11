"""Asynchronous User Resource for Gitea API."""

from __future__ import annotations

from typing import Any, Literal

from gitea.resource.async_resource import AsyncResource
from gitea.user.base import BaseUser


class AsyncUser(BaseUser, AsyncResource):
    """Asynchronous Gitea User resource."""

    async def get_user(self, username: str | None = None, **kwargs: Any) -> dict[str, Any]:
        """Get user information.

        Args:
            username: The username of the user to retrieve. If None, retrieves the authenticated user.
            **kwargs: Additional arguments for the request.

        Returns:
            The authenticated user's information as a dictionary.
        """
        endpoint = f"/users/{username}" if username else "/user"
        return await self._get(endpoint=endpoint, **kwargs)

    async def get_workflow_jobs(
        self,
        status: Literal["pending", "queued", "in_progress", "failure", "success", "skipped"],
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Get workflow jobs for the authenticated user filtered by status.

        Args:
            status: The status to filter workflow jobs by.
            page: The page number for pagination.
            limit: The number of items per page for pagination.
            **kwargs: Additional arguments for the request.

        Returns:
            A dictionary containing the workflow jobs with the specified status.
        """
        endpoint = "/user/actions/jobs"
        params = self._build_get_workflow_jobs_params(status=status, page=page, limit=limit)
        return await self._get(endpoint=endpoint, params=params, **kwargs)

    async def get_user_level_runners(self, runner_id: str | None = None, **kwargs: Any) -> dict[str, Any]:
        """Get user-level runners for the authenticated user.

        Args:
            runner_id: The ID of a specific runner to retrieve. If None, retrieves all user-level runners.
            **kwargs: Additional arguments for the request.

        Returns:
            A dictionary containing the user-level runners.
        """
        endpoint = "/user/actions/runners" if runner_id is None else f"/user/actions/runners/{runner_id}"
        return await self._get(endpoint=endpoint, **kwargs)

    async def get_registration_token(self, **kwargs: Any) -> dict[str, Any]:
        """Get a registration token for adding a new user-level runner.

        Args:
            **kwargs: Additional arguments for the request.

        Returns:
            A dictionary containing the registration token.
        """
        endpoint = "/user/actions/runners/registration-token"
        return await self._get(endpoint=endpoint, **kwargs)

    async def delete_user_level_runner(self, runner_id: str, **kwargs: Any) -> dict[str, Any]:
        """Delete a user-level runner.

        Args:
            runner_id: The ID of the runner to delete.
            **kwargs: Additional arguments for the request.

        Returns:
            A dictionary containing the response from the delete operation.
        """
        endpoint = f"/user/actions/runners/{runner_id}"
        return await self._delete(endpoint=endpoint, **kwargs)

    async def get_workflow_runs(  # noqa: PLR0913
        self,
        event: str | None = None,
        branch: str | None = None,
        status: Literal["pending", "queued", "in_progress", "failure", "success", "skipped"] | None = None,
        actor: str | None = None,
        head_sha: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Get workflow runs for the authenticated user filtered by various parameters.

        Args:
            event: The event that triggered the workflow run.
            branch: The branch name to filter workflow runs.
            status: The status to filter workflow runs by.
            actor: The username of the actor who triggered the workflow run.
            head_sha: The commit SHA to filter workflow runs.
            page: The page number for pagination.
            limit: The number of items per page for pagination.

        Returns:
            A dictionary containing the workflow runs with the specified filters.
        """
        endpoint = "/user/actions/runs"
        params = self._build_get_workflow_runs_params(
            event=event, branch=branch, status=status, actor=actor, head_sha=head_sha, page=page, limit=limit
        )
        return await self._get(endpoint=endpoint, params=params, **kwargs)
