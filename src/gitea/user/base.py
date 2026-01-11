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
