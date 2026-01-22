"""Asynchronous Resource Base Class for Gitea API interactions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiohttp import ClientResponse

if TYPE_CHECKING:
    from gitea.client.async_gitea import AsyncGitea


class AsyncResource:
    """Base class for asynchronous Gitea API resources."""

    def __init__(self, client: AsyncGitea) -> None:
        """Initialize the Resource with a AsyncGitea client.

        Args:
            client: An instance of the AsyncGitea client.

        """
        self.client = client

    async def _get(self, endpoint: str, **kwargs: Any) -> ClientResponse:
        """Perform a GET request.

        Args:
            endpoint: The API endpoint.
            **kwargs: Additional arguments for the request.

        Returns:
            The response as a ClientResponse object.

        """
        return await self.client._request(method="GET", endpoint=endpoint, **kwargs)

    async def _post(self, endpoint: str, **kwargs: Any) -> ClientResponse:
        """Perform a POST request.

        Args:
            endpoint: The API endpoint.
            **kwargs: Additional arguments for the request.

        Returns:
            The response as a ClientResponse object.

        """
        return await self.client._request(method="POST", endpoint=endpoint, **kwargs)

    async def _put(self, endpoint: str, **kwargs: Any) -> ClientResponse:
        """Perform a PUT request.

        Args:
            endpoint: The API endpoint.
            **kwargs: Additional arguments for the request.

        Returns:
            The response as a ClientResponse object.

        """
        return await self.client._request(method="PUT", endpoint=endpoint, **kwargs)

    async def _delete(self, endpoint: str, **kwargs: Any) -> ClientResponse:
        """Perform a DELETE request.

        Args:
            endpoint: The API endpoint.
            **kwargs: Additional arguments for the request.

        Returns:
            The response as a ClientResponse object.

        """
        return await self.client._request(method="DELETE", endpoint=endpoint, **kwargs)

    async def _patch(self, endpoint: str, **kwargs: Any) -> ClientResponse:
        """Perform a PATCH request.

        Args:
            endpoint: The API endpoint.
            **kwargs: Additional arguments for the request.

        Returns:
            The response as a ClientResponse object.

        """
        return await self.client._request(method="PATCH", endpoint=endpoint, **kwargs)
