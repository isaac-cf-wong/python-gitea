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
"""

from __future__ import annotations

import json
from typing import Any


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
            payload: JSON-serializable body to answer with.

        """
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

    def request(self, method: str, url: str, **kwargs: Any) -> RecordedResponse:
        """Record a request and answer it with the fixed payload.

        Args:
            method: HTTP method the client asked for.
            url: Full URL the client built.
            **kwargs: Headers, timeout and body, which are not recorded.

        Returns:
            The recorded response.

        """
        self.requests.append((method, url))
        return RecordedResponse(self.payload)

    def close(self) -> None:
        """Close the session, as leaving the client's context manager does."""

    @property
    def urls(self) -> list[str]:
        """The URLs requested so far, in order.

        Returns:
            One URL per recorded request.

        """
        return [url for _, url in self.requests]
