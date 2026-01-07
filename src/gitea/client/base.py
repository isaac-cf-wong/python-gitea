"""Base client class for Gitea API interactions."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Client(ABC):  # pylint: disable=too-few-public-methods
    """Abstract base class for Gitea clients."""

    def __init__(self, token: str, base_url: str) -> None:
        """Construct the base client.

        Args:
            token: The API token for authentication.
            base_url: The base URL of the Gitea instance.
        """
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"token {self.token}",
        }

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

    @abstractmethod
    async def _request(
        self, method: str, endpoint: str, headers: dict | None = None, timeout: int = 30, **kwargs
    ) -> dict:
        """Perform an HTTP request to the specified endpoint.

        Args:
            method: The HTTP method (GET, POST, etc.).
            endpoint: The API endpoint.
            headers: Additional headers to include in the request.
            timeout: Request timeout in seconds.

        Returns:
            dict: The JSON response.
        """
