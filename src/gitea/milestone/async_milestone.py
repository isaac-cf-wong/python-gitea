"""Asynchronous Gitea Milestone resource."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, cast

from aiohttp import ClientResponse

from gitea.milestone.base import BaseMilestone
from gitea.resource.async_resource import AsyncResource
from gitea.utils.response import process_async_response


class AsyncMilestone(BaseMilestone, AsyncResource):
    """Asynchronous Gitea Milestone resource."""

    async def _list_milestones(
        self,
        owner: str,
        repository: str,
        state: Literal["closed", "open", "all"] | None = None,
        name: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """List milestones in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            state: Filter milestones by state.
            name: Filter milestones by name.
            page: The page number for pagination.
            limit: The number of milestones per page.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_milestones_helper(
            owner=owner,
            repository=repository,
            state=state,
            name=name,
            page=page,
            limit=limit,
        )
        return await self._get(endpoint=endpoint, params=params, **kwargs)

    async def list_milestones(
        self,
        owner: str,
        repository: str,
        state: Literal["closed", "open", "all"] | None = None,
        name: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """List milestones in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            state: Filter milestones by state.
            name: Filter milestones by name.
            page: The page number for pagination.
            limit: The number of milestones per page.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing a list of milestones as dictionaries and a dictionary with metadata.

        """
        response = await self._list_milestones(
            owner=owner,
            repository=repository,
            state=state,
            name=name,
            page=page,
            limit=limit,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    async def _create_milestone(
        self,
        owner: str,
        repository: str,
        title: str,
        description: str | None = None,
        due_on: datetime | None = None,
        state: Literal["closed", "open"] | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """Create a milestone in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            title: The title of the milestone.
            description: The description of the milestone.
            due_on: The due date of the milestone.
            state: The state of the milestone.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._create_milestone_helper(
            owner=owner,
            repository=repository,
            title=title,
            description=description,
            due_on=due_on,
            state=state,
        )
        return await self._post(endpoint=endpoint, json=payload, **kwargs)

    async def create_milestone(
        self,
        owner: str,
        repository: str,
        title: str,
        description: str | None = None,
        due_on: datetime | None = None,
        state: Literal["closed", "open"] | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Create a milestone in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            title: The title of the milestone.
            description: The description of the milestone.
            due_on: The due date of the milestone.
            state: The state of the milestone.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the created milestone as a dictionary and a dictionary with metadata.

        """
        response = await self._create_milestone(
            owner=owner,
            repository=repository,
            title=title,
            description=description,
            due_on=due_on,
            state=state,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}
