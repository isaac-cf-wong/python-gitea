"""Gitea API client implementation."""

from __future__ import annotations

import requests

from gitea.client.base import Client


class Gitea(Client):  # pylint: disable=too-few-public-methods
    """Synchronous Gitea API client."""

    def __init__(self, token: str, base_url: str = "https://gitea.com") -> None:
        """Initialize the Gitea client.

        Args:
            token: The API token for authentication.
            base_url: The base URL of the Gitea instance.
        """
        super().__init__(token=token, base_url=base_url)
        self.session = requests.Session()

    def _request(
        self, method: str, endpoint: str, headers: dict | None = None, timeout: int = 30, **kwargs
    ) -> requests.Response:
        """Make an HTTP request to the Gitea API.

        Args:
            method: The HTTP method (GET, POST, etc.).
            endpoint: The API endpoint.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response.
        """
        url = self._build_url(endpoint=endpoint)
        response = self.session.request(
            method, url, headers={**self.headers, **(headers or {})}, timeout=timeout, **kwargs
        )
        response.raise_for_status()
        return response
