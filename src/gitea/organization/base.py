"""Base class for Gitea Organization resource.

Two endpoints answer "which organizations are there", and what separates them is
whose organizations are being asked for: `/user/orgs` lists those of the account
the token belongs to, and `/users/{username}/orgs` those of a named account.

Gitea also serves a site-wide listing at `/orgs`, which a token that is not
scoped for it is refused. A listing of the organizations an account can see
therefore cannot be read from it, and it is not wrapped here.
"""

from __future__ import annotations

from typing import Any


class BaseOrganization:
    """Base class for Gitea Organization resource."""

    def _list_organizations_endpoint(self, username: str | None = None) -> str:
        """Construct the endpoint URL for listing organizations.

        If username is None, it lists the organizations of the authenticated
        account. If username is provided, it lists that account's organizations.

        Args:
            username: The account whose organizations are listed.

        Returns:
            The endpoint URL for listing organizations.

        """
        if username is None:
            return "/user/orgs"
        return f"/users/{username}/orgs"

    def _list_organizations_helper(
        self,
        username: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing organizations.

        Args:
            username: The account whose organizations are listed.
            page: The page number for pagination.
            limit: The number of organizations per page.

        Returns:
            A tuple containing the endpoint URL and a dictionary of parameters.

        """
        endpoint = self._list_organizations_endpoint(username=username)
        params = {}
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit
        return endpoint, params
