"""Asynchronous Pull Request API for Gitea."""

from __future__ import annotations

from typing import Any, Literal, cast

from aiohttp import ClientResponse

from gitea.pull_request.base import BasePullRequest
from gitea.resource.async_resource import AsyncResource
from gitea.utils.response import process_async_response


class AsyncPullRequest(BasePullRequest, AsyncResource):
    """Asynchronous Pull Request API for Gitea."""

    async def _list_pull_requests(  # noqa: PLR0913
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
        **kwargs: Any,
    ) -> ClientResponse:
        """List pull requests in a repository.

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
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_pull_requests_helper(
            owner=owner,
            repository=repository,
            base_branch=base_branch,
            state=state,
            sort=sort,
            milestone=milestone,
            labels=labels,
            poster=poster,
            page=page,
            limit=limit,
        )
        return await self._get(endpoint=endpoint, params=params, **kwargs)

    async def list_pull_requests(  # noqa: PLR0913
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
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], int]:
        """List pull requests in a repository.

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
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing a list of pull requests and the total count.

                - A list of dictionaries representing pull requests.
                - Status code of the response.

        """
        response = await self._list_pull_requests(
            owner=owner,
            repository=repository,
            base_branch=base_branch,
            state=state,
            sort=sort,
            milestone=milestone,
            labels=labels,
            poster=poster,
            page=page,
            limit=limit,
            **kwargs,
        )
        data, status_code = await process_async_response(response)
        return cast(list[dict[str, Any]], data), status_code
