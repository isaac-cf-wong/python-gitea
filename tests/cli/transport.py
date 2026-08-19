"""Recording stand-in for the HTTP session a CLI invocation makes its requests through.

Patching the client itself proves that a command ran, but not where it sent the
user: a stub whose every attribute answers the same way accepts a call to the
repository endpoint and the organization one alike. Standing in one level lower -
at the session the real client builds its URLs for - keeps the client, the
resource and the path building under test and records the URL each command
actually asked for.

Use it by patching the session the client constructs:

    session = RecordingSession()
    with patch("gitea.client.gitea.requests.Session", return_value=session):
        result = runner.invoke(app, [...])

    assert session.requests == [("GET", "https://gitea.invalid/api/v1/orgs/org/projects/1")]

`RecordingSession` answers every request alike. `RoutedSession` answers each
endpoint with a payload of its own, for a command reaching several - resolving an
issue before acting on it, walking a board's columns before their issues - and
`NO_CONTENT` answers as an endpoint that succeeds without a body does, so a
command whose endpoint really answers `204` is not tested against a body the API
never sends.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any


class NoContent:
    """The answer of an endpoint that reports success without a body.

    A `DELETE` answers `204 No Content`, and a payload of `None` would still be
    a body carrying `null`. A test asserting on what such a command emits has to
    be answered the way the real endpoint answers, or it pins a shape the API
    never produces.
    """

    def __repr__(self) -> str:
        """Name the sentinel in a test failure.

        Returns:
            The name this is referred to by.

        """
        return "NO_CONTENT"


NO_CONTENT = NoContent()


class RecordedResponse:
    """The answer the recording session gives, shaped like the response a request returns.

    Only the parts `process_response` and the client's error handling read are
    provided, so an addition to either shows up as an attribute error here
    rather than as a test passing against a response the real code could not
    have produced.
    """

    def __init__(self, payload: Any) -> None:
        """Hold the payload this response carries.

        Args:
            payload: JSON-serializable body to answer with, or `NO_CONTENT` to
                answer as an endpoint that succeeds without a body does.

        """
        if isinstance(payload, NoContent):
            self.status_code = 204
            self.content = b""
        else:
            self.status_code = 200
            self.content = json.dumps(payload).encode()

    def json(self) -> Any:
        """Parse the body, as the real response does.

        Returns:
            The payload this response carries.

        """
        return json.loads(self.content)

    def raise_for_status(self) -> None:
        """Raise nothing: the recorded response is always a success."""

    def close(self) -> None:
        """Release the response, as the client does on a failure."""


class RecordingSession:
    """Session that records the requests it is asked to make and answers them all alike.

    The payload defaults to an empty listing because a command paging through a
    listing stops on the first short page, and a full page of a fixed size would
    page forever.
    """

    def __init__(self, payload: Any = None) -> None:
        """Start a session recording nothing yet.

        Args:
            payload: Body every request is answered with. Defaults to an empty
                listing.

        """
        self.payload: Any = [] if payload is None else payload
        self.requests: list[tuple[str, str]] = []
        self.headers: list[dict[str, Any]] = []
        self.params: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> RecordedResponse:
        """Record a request and answer it with the fixed payload.

        Args:
            method: HTTP method the client asked for.
            url: Full URL the client built.
            **kwargs: Timeout and body, which are not recorded, and headers and
                query parameters, which are: the headers carry the credentials
                the command resolved, and a command reaching the right URL
                unauthenticated is not a command that works, while the
                parameters carry what it asked that endpoint for.

        Returns:
            The recorded response.

        """
        self._record(method, url, **kwargs)
        return RecordedResponse(self.payload)

    def _record(self, method: str, url: str, **kwargs: Any) -> None:
        """Keep what one request was made with.

        Args:
            method: HTTP method the client asked for.
            url: Full URL the client built.
            **kwargs: The headers and the query parameters, which are kept, and
                the timeout and body, which are not.

        """
        self.requests.append((method, url))
        self.headers.append(dict(kwargs.get("headers") or {}))
        self.params.append(dict(kwargs.get("params") or {}))

    def close(self) -> None:
        """Close the session, as leaving the client's context manager does."""

    @property
    def urls(self) -> list[str]:
        """The URLs requested so far, in order.

        Returns:
            One URL per recorded request.

        """
        return [url for _, url in self.requests]


class RoutedSession(RecordingSession):
    """Session answering each request with the payload declared for its endpoint.

    A command reaching more than one endpoint - resolving an issue before acting
    on it, walking a board's columns before their issues - needs a different
    payload per endpoint, which the one fixed payload of `RecordingSession`
    cannot give it.

    Routes are matched in order and the first whose fragment appears in the URL
    answers, so a route for `/columns/1/issues` has to be declared before one for
    `/columns`, whose fragment the longer URL also contains. Anything unrouted is
    answered with the fixed payload, as before.
    """

    def __init__(self, routes: Sequence[tuple[str, Any]], payload: Any = None) -> None:
        """Start a session answering the given endpoints.

        Args:
            routes: The fragment to match and the payload to answer it with, in
                the order they are matched.
            payload: Body every unrouted request is answered with. Defaults to
                an empty listing, as `RecordingSession` does.

        """
        super().__init__(payload)
        self.routes = list(routes)

    def request(self, method: str, url: str, **kwargs: Any) -> RecordedResponse:
        """Record a request and answer it with the payload its endpoint declared.

        Args:
            method: HTTP method the client asked for.
            url: Full URL the client built.
            **kwargs: Timeout and body, which are not recorded, and headers and
                query parameters, which are.

        Returns:
            The recorded response.

        """
        self._record(method, url, **kwargs)
        for fragment, payload in self.routes:
            if fragment in url:
                return RecordedResponse(payload)
        return RecordedResponse(self.payload)
