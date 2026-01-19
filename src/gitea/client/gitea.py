"""Gitea API client implementation."""

from __future__ import annotations

from typing import Any

import requests

from gitea.client.base import Client
from gitea.user.user import User


class Gitea(Client):  # pylint: disable=too-few-public-methods
    """Synchronous Gitea API client."""

    def __init__(self, token: str | None = None, base_url: str = "https://gitea.com") -> None:
        """Initialize the Gitea client.

        Args:
            token: The API token for authentication.
            base_url: The base URL of the Gitea instance.
        """
        super().__init__(token=token, base_url=base_url)
        self.session: requests.Session | None = None
        self.user = User(client=self)

    def __str__(self) -> str:
        """Return a string representation of the Gitea client.

        Returns:
            A string representing the Gitea client.
        """
        return f"Gitea Client(base_url={self.base_url})"

    def __enter__(self) -> Gitea:
        """Enter the context manager.

        Returns:
            The Gitea client instance.
        """
        if self.session is not None:
            raise RuntimeError("Gitea session already open; do not re-enter context manager.")
        self.session = requests.Session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager.

        Args:
            exc_type: The exception type.
            exc_val: The exception value.
            exc_tb: The traceback.
        """
        if self.session:
            self.session.close()
            self.session = None

    def _request(
        self, method: str, endpoint: str, headers: dict | None = None, timeout: int = 30, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Make an HTTP request to the Gitea API.

        Args:
            method: The HTTP method (GET, POST, etc.).
            endpoint: The API endpoint.
            headers: Additional headers for the request.
            timeout: Timeout for the request in seconds.
            **kwargs: Additional arguments for the request.

        Returns:
            The JSON response from the API. None for 204 No Content responses.
        """
        if self.session is None:
            raise RuntimeError(
                "Gitea must be used as a context manager. "
                + "Use 'with Gitea(...) as client:' to ensure proper resource cleanup."
            )
        url = self._build_url(endpoint=endpoint)
        response = self.session.request(
            method, url, headers={**self.headers, **(headers or {})}, timeout=timeout, **kwargs
        )
        response.raise_for_status()

        # Handle 204 No Content responses
        if response.status_code == 204:  # noqa: PLR2004
            return None

        return response.json()
