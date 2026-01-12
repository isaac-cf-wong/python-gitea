"""Base class for Gitea User resource."""

from __future__ import annotations

from typing import Literal


class BaseUser:
    """Base class for Gitea User resource."""

    def _build_get_workflow_jobs_params(
        self,
        status: Literal["pending", "queued", "in_progress", "failure", "success", "skipped"],
        page: int | None = None,
        limit: int | None = None,
    ) -> dict[str, str]:
        """Build parameters for getting workflow jobs.

        Args:
            status: The status to filter workflow jobs by.
            page: The page number for pagination.
            limit: The number of items per page for pagination.

        Returns:
            A dictionary of parameters for the request.
        """
        params: dict[str, str] = {"status": status}
        if page is not None:
            params["page"] = str(page)
        if limit is not None:
            params["limit"] = str(limit)
        return params

    def _build_get_workflow_runs_params(  # noqa: PLR0913
        self,
        event: str | None = None,
        branch: str | None = None,
        status: Literal["pending", "queued", "in_progress", "failure", "success", "skipped"] | None = None,
        actor: str | None = None,
        head_sha: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> dict[str, str]:
        """Build parameters for getting workflow runs.

        Args:
            event: The event to filter workflow runs by.
            branch: The branch to filter workflow runs by.
            status: The status to filter workflow runs by.
            actor: The actor to filter workflow runs by.
            head_sha: The head SHA to filter workflow runs by.
            page: The page number for pagination.
            limit: The number of items per page for pagination.

        Returns:
            A dictionary of parameters for the request.
        """
        params: dict[str, str] = {}
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
        if page is not None:
            params["page"] = str(page)
        if limit is not None:
            params["limit"] = str(limit)
        return params
