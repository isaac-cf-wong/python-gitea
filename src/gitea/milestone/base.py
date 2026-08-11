"""Base class for Gitea Milestone resource."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal


class BaseMilestone:
    """Base class for Gitea Milestone resource."""

    def _list_milestones_endpoint(self, owner: str, repository: str) -> str:
        """Construct the endpoint URL for listing milestones in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.

        Returns:
            The endpoint URL for listing milestones.

        """
        return f"/repos/{owner}/{repository}/milestones"

    def _list_milestones_helper(
        self,
        owner: str,
        repository: str,
        state: Literal["closed", "open", "all"] | None = None,
        name: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing milestones in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            state: Filter milestones by state.
            name: Filter milestones by name.
            page: The page number for pagination.
            limit: The number of milestones per page.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._list_milestones_endpoint(owner=owner, repository=repository)

        params = {}
        if state is not None:
            params["state"] = state
        if name is not None:
            params["name"] = name
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        return endpoint, params

    def _create_milestone_endpoint(self, owner: str, repository: str) -> str:
        """Construct the endpoint URL for creating a milestone in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.

        Returns:
            The endpoint URL for creating a milestone.

        """
        return f"/repos/{owner}/{repository}/milestones"

    def _create_milestone_helper(
        self,
        owner: str,
        repository: str,
        title: str,
        description: str | None = None,
        due_on: datetime | None = None,
        state: Literal["closed", "open"] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for creating a milestone in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            title: The title of the milestone.
            description: The description of the milestone.
            due_on: The due date of the milestone.
            state: The state of the milestone.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._create_milestone_endpoint(owner=owner, repository=repository)

        payload: dict[str, Any] = {"title": title}

        if description is not None:
            payload["description"] = description
        if due_on is not None:
            payload["due_on"] = due_on.isoformat()
        if state is not None:
            payload["state"] = state

        return endpoint, payload
