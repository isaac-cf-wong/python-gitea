"""What a resource needs of the client that owns it.

`Resource` and `AsyncResource` reach for exactly one thing on their client:
`_request`. Naming that as a protocol here, rather than importing the concrete
`Gitea` and `AsyncGitea`, is what keeps the dependency running one way. The
clients build the resources, so a resource that imported its client back -
even under `TYPE_CHECKING` - would close a cycle across most of the package.

Neither protocol is `runtime_checkable`, and nothing here is meant to be
subclassed: `Gitea` and `AsyncGitea` satisfy these structurally, by having the
method, and a test double satisfies them the same way.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from aiohttp import ClientResponse
    from requests import Response


class ClientProtocol(Protocol):
    """The part of a synchronous client that a `Resource` uses."""

    def _request(
        self, method: str, endpoint: str, headers: dict | None = None, timeout: int = 30, **kwargs: Any
    ) -> Response:
        """Make an HTTP request to the Gitea API.

        Args:
            method: The HTTP method (GET, POST, etc.).
            endpoint: The API endpoint.
            headers: Additional headers for the request.
            timeout: Timeout for the request in seconds.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        ...


class AsyncClientProtocol(Protocol):
    """The part of an asynchronous client that an `AsyncResource` uses."""

    async def _request(
        self, method: str, endpoint: str, headers: dict | None = None, timeout: int = 30, **kwargs: Any
    ) -> ClientResponse:
        """Make an asynchronous HTTP request to the Gitea API.

        Args:
            method: The HTTP method (GET, POST, etc.).
            endpoint: The API endpoint.
            headers: Optional headers to include in the request.
            timeout: Request timeout in seconds.
            **kwargs: Additional arguments for the request.

        Returns:
            The aiohttp ClientResponse object.

        """
        ...
