"""Asynchronous Gitea Repository resource."""

from __future__ import annotations

from typing import Any, cast

from aiohttp import ClientResponse

from gitea.repository.base import BaseRepository
from gitea.resource.async_resource import AsyncResource
from gitea.utils.response import process_async_response


class AsyncRepository(AsyncResource, BaseRepository):
    """Asynchronous Gitea Repository resource."""

    async def _list_repositories(
        self,
        username: str | None = None,
        organization: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """List repositories for a user, organization, or authenticated user.

        Args:
            username: The username to list repositories for.
            organization: The organization to list repositories for.
            page: The page number for pagination.
            limit: The number of repositories per page.
            **kwargs: Additional arguments to pass to the request.

        Returns:
            The response object containing the list of repositories.

        """
        endpoint, params = self._list_repositories_helper(
            username=username,
            organization=organization,
            page=page,
            limit=limit,
        )
        return await self._get(endpoint=endpoint, params=params, **kwargs)

    async def list_repositories(
        self,
        username: str | None = None,
        organization: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], int]:
        """List repositories for a user, organization, or authenticated user.

        Args:
            username: The username to list repositories for.
            organization: The organization to list repositories for.
            page: The page number for pagination.
            limit: The number of repositories per page.
            **kwargs: Additional arguments to pass to the request.

        Returns:
            A tuple containing a list of repositories and the status code.

        """
        response = await self._list_repositories(
            username=username,
            organization=organization,
            page=page,
            limit=limit,
            **kwargs,
        )
        data, status_code = await process_async_response(response=response)
        return cast(list[dict[str, Any]], data), status_code
