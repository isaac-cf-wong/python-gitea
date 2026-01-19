"""Base class for Gitea API resources."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from requests import Response

if TYPE_CHECKING:
    from gitea.client.gitea import Gitea


class Resource:
    """Base class for Gitea API resources."""

    def __init__(self, client: Gitea) -> None:
        """Initialize the Resource with a Gitea client.

        Args:
            client: An instance of the Gitea client.
        """
        self.client = client

    def _get(self, endpoint: str, **kwargs: Any) -> Response:
        """Helper method to perform a GET request.

        Args:
            endpoint: The API endpoint.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response.
        """
        return self.client._request(method="GET", endpoint=endpoint, **kwargs)

    def _post(self, endpoint: str, **kwargs: Any) -> Response:
        """Helper method to perform a POST request.

        Args:
            endpoint: The API endpoint.
            **kwargs: Additional arguments for the request.

        Returns:
            The HttP response.
        """
        return self.client._request(method="POST", endpoint=endpoint, **kwargs)

    def _put(self, endpoint: str, **kwargs: Any) -> Response:
        """Helper method to perform a PUT request.

        Args:
            endpoint: The API endpoint.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response.
        """
        return self.client._request(method="PUT", endpoint=endpoint, **kwargs)

    def _delete(self, endpoint: str, **kwargs: Any) -> Response:
        """Helper method to perform a DELETE request.

        Args:
            endpoint: The API endpoint.
            **kwargs: Additional arguments for the request.

        Returns:
            The Http response.
        """
        return self.client._request(method="DELETE", endpoint=endpoint, **kwargs)

    def _patch(self, endpoint: str, **kwargs: Any) -> Response:
        """Helper method to perform a PATCH request.

        Args:
            endpoint: The API endpoint.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response.
        """
        return self.client._request(method="PATCH", endpoint=endpoint, **kwargs)
