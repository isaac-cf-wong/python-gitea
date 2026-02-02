"""Base class for Gitea pull request resource."""

from __future__ import annotations

from typing import Any, Literal


class BasePullRequest:
    """Base class for Gitea Pull Request resource."""

    def _list_pull_requests_endpoint(self, owner: str, repository: str) -> str:
        """Construct the endpoint URL for listing pull requests in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.

        Returns:
            The endpoint URL for listing pull requests.

        """
        return f"/repos/{owner}/{repository}/pulls"

    def _list_pull_requests_helper(  # noqa: PLR0913
        self,
        owner: str,
        repository: str,
        base_branch: str | None = None,
        state: Literal["open", "closed", "all"] | None = None,
        sort: (
            Literal["oldest", "recentupdate", "recentclose", "leastupdate", "mostcomment", "leastcomment", "priority"]
            | None
        ) = None,
        milestone: int | None = None,
        labels: list[int] | None = None,
        poster: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing pull requests in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            base_branch: Filter pull requests by base branch.
            state: Filter pull requests by state.
            sort: Sort pull requests by the given criteria.
            milestone: Filter pull requests by milestone.
            labels: Filter pull requests by labels.
            poster: Filter pull requests by poster.
            page: The page number for pagination.
            limit: The number of pull requests per page.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._list_pull_requests_endpoint(owner, repository)
        params: dict[str, Any] = {}

        if base_branch is not None:
            params["base"] = base_branch
        if state is not None:
            params["state"] = state
        if sort is not None:
            params["sort"] = sort
        if milestone is not None:
            params["milestone"] = milestone
        if labels is not None:
            params["labels"] = labels
        if poster is not None:
            params["poster"] = poster
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        return endpoint, params
