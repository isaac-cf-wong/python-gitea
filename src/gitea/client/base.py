"""Base client class for Gitea API interactions."""

from __future__ import annotations

from typing import Any


class Client:  # pylint: disable=too-few-public-methods
    """Abstract base class for Gitea clients."""

    def __init__(self, token: str | None, base_url: str) -> None:
        """Construct the base client.

        Args:
            token: The API token for authentication.
            base_url: The base URL of the Gitea instance.
        """
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.headers: dict[str, Any] = {}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    @property
    def api_url(self) -> str:
        """Return the base API URL.

        Returns:
            str: The base API URL.
        """
        return f"{self.base_url}/api/v1"

    def _build_url(self, endpoint: str) -> str:
        """Construct the full URL for a given endpoint.

        Args:
            endpoint (str): The API endpoint.

        Returns:
            str: The full URL.
        """
        return f"{self.api_url}/{endpoint.lstrip('/')}"
