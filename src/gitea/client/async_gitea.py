"""Asynchronous Gitea API client implementation."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientSession, ClientTimeout

from gitea.client.base import Client


class AsyncGitea(Client):  # pylint: disable=too-few-public-methods
    """Asynchronous Gitea API client."""

    def __init__(self, token: str | None = None, base_url: str = "https://gitea.com") -> None:
        """Initialize the asynchronous Gitea client.

        Args:
            token: The API token for authentication.
            base_url: The base URL of the Gitea instance.
        """
        super().__init__(token=token, base_url=base_url)
        self.session: ClientSession | None = None

    async def __aenter__(self) -> AsyncGitea:
        """Enter the asynchronous context manager.

        Returns:
            The AsyncGitea client instance.
        """
        if self.session is not None and not self.session.closed:
            raise RuntimeError("AsyncGitea session already open; do not re-enter context manager.")
        self.session = ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the asynchronous context manager.

        Args:
            exc_type: The exception type.
            exc_val: The exception value.
            exc_tb: The traceback.
        """
        if self.session:
            await self.session.close()
            self.session = None

    def _get_session(self, headers: dict | None = None, **kwargs: Any) -> ClientSession:
        """Get or create the aiohttp ClientSession.

        Args:
            headers: Optional headers to include in the session.
            **kwargs: Additional arguments for ClientSession.

        Returns:
            The aiohttp ClientSession instance.
        """
        return ClientSession(headers=headers, **kwargs)

    async def _request(
        self, method: str, endpoint: str, headers: dict | None = None, timeout: int = 30, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Make an asynchronous HTTP request to the Gitea API.

        Args:
            method: The HTTP method (GET, POST, etc.).
            endpoint: The API endpoint.
            headers: Optional headers to include in the request.
            timeout: Request timeout in seconds.
            **kwargs: Additional arguments for the request.

        Returns:
            The JSON response from the API. None for 204 No Content responses.
        """
        if self.session is None:
            raise RuntimeError(
                "AsyncGitea must be used as an async context manager. "
                + "Use 'async with AsyncGitea(...) as client:' to ensure proper resource cleanup."
            )

        url = self._build_url(endpoint=endpoint)
        request_headers = {**self.headers, **(headers or {})}
        timeout_obj = ClientTimeout(total=timeout)
        async with self.session.request(
            method=method, url=url, headers=request_headers, timeout=timeout_obj, **kwargs
        ) as response:
            response.raise_for_status()

            # Handle 204 No Content responses
            if response.status == 204:  # noqa: PLR2004
                return None

            return await response.json()
