"""Gitea User resource."""

from __future__ import annotations

from typing import Any

from gitea.resource.resource import Resource


class User(Resource):
    """Gitea User resource."""

    def get_user(self, username: str | None = None, **kwargs) -> dict[str, Any]:
        """Get user information.

        Args:
            username: The username of the user to retrieve. If None, retrieves the authenticated user.
            **kwargs: Additional arguments for the request.

        Returns:
            The authenticated user's information as a dictionary.
        """
        endpoint = f"/users/{username}" if username else "/user"
        return self._get(endpoint=endpoint, **kwargs)
