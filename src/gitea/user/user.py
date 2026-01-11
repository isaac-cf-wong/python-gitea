"""Gitea User resource."""

from __future__ import annotations

from typing import Any, Literal

from gitea.resource.resource import Resource


class User(Resource):
    """Gitea User resource."""

    def get_user(self, username: str | None = None, **kwargs) -> dict[str, Any]:
        """Get user information.

        Args:
            username: The username of the user to retrieve. If None, retrieves the authenticated user.
            **kwargs: Additional arguments for the request.

        Returns:
            The authenticated user's information as a dictionary.
        """
        endpoint = f"/users/{username}" if username else "/user"
        return self._get(endpoint=endpoint, **kwargs)

    def get_workflow_jobs(
        self,
        status: Literal["pending", "queued", "in_progress", "failure", "success", "skipped"],
        page: int | None = None,
        limit: int | None = None,
        **kwargs,
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
        endpoint = "user/actions/jobs"
        payload = {"status": status}
        if page is not None:
            payload["page"] = str(page)
        if limit is not None:
            payload["limit"] = str(limit)
        return self._get(endpoint=endpoint, params=payload, **kwargs)

    def get_user_level_runners(self, **kwargs) -> dict[str, Any]:
        """Get user-level runners for the authenticated user.

        Returns:
            A dictionary containing the user-level runners.
        """
        endpoint = "/user/runners"
        return self._get(endpoint=endpoint, **kwargs)
