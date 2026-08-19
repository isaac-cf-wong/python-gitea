"""Asynchronous Gitea Organization resource."""

from __future__ import annotations

from typing import Any, cast

from aiohttp import ClientResponse

from gitea.organization.base import BaseOrganization
from gitea.resource.async_resource import AsyncResource
from gitea.utils.response import process_async_response


class AsyncOrganization(AsyncResource, BaseOrganization):
    """Asynchronous Gitea Organization resource."""

    async def _list_organizations(
        self,
        username: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """List the organizations of an account, or of the authenticated account.

        Args:
            username: The account whose organizations are listed.
            page: The page number for pagination.
            limit: The number of organizations per page.
            **kwargs: Additional arguments to pass to the request.

        Returns:
            The response object containing the list of organizations.

        """
        endpoint, params = self._list_organizations_helper(
            username=username,
            page=page,
            limit=limit,
        )
        return await self._get(endpoint=endpoint, params=params, **kwargs)

    async def list_organizations(
        self,
        username: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """List the organizations of an account, or of the authenticated account.

        Args:
            username: The account whose organizations are listed.
            page: The page number for pagination.
            limit: The number of organizations per page.
            **kwargs: Additional arguments to pass to the request.

        Returns:
            A tuple containing a list of organizations and the status code.

        """
        response = await self._list_organizations(
            username=username,
            page=page,
            limit=limit,
            **kwargs,
        )
        data, status_code = await process_async_response(response=response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}
