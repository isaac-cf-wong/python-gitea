"""Base class for Gitea Repository resource."""

from __future__ import annotations

from typing import Any


class BaseRepository:
    """Base class for Gitea Repository resource."""

    def _list_repositories_endpoint(self, username: str | None = None, organization: str | None = None) -> str:
        """Construct the endpoint URL for listing repositories.

        If both username and organization are None, it lists repositories for the authenticated user.
        If username is provided, it lists repositories for that user.
        If organization is provided, it lists repositories for that organization.

        Args:
            username: The username to list repositories for.
            organization: The organization to list repositories for.

        Returns:
            The endpoint URL for listing repositories.

        """
        if username is None and organization is None:
            return "/user/repos"
        if username is not None and organization is None:
            return f"/users/{username}/repos"
        if username is None and organization is not None:
            return f"/orgs/{organization}/repos"
        raise ValueError("Either username or organization must be provided, not both.")

    def _list_repositories_helper(
        self,
        username: str | None = None,
        organization: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing repositories.

        Args:
            username: The username to list repositories for.
            organization: The organization to list repositories for.
            page: The page number for pagination.
            limit: The number of repositories per page.

        Returns:
            A tuple containing the endpoint URL and a dictionary of parameters.

        """
        endpoint = self._list_repositories_endpoint(username=username, organization=organization)
        params = {}
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit
        return endpoint, params
