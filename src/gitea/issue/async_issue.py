"""Asynchronous Gitea Issue resource."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, cast

from aiohttp import ClientResponse

from gitea.issue.base import BaseIssue
from gitea.resource.async_resource import AsyncResource
from gitea.utils.response import process_async_response


class AsyncIssue(BaseIssue, AsyncResource):
    """Asynchronous Gitea Issue resource."""

    async def _list_issues(  # noqa: PLR0913
        self,
        owner: str,
        repository: str,
        state: Literal["closed", "open", "all"] | None = None,
        labels: list[str] | None = None,
        search_string: str | None = None,
        issue_type: Literal["Issues", "pulls"] | None = None,
        milestones: list[str] | list[int] | None = None,
        since: datetime | None = None,
        before: datetime | None = None,
        created_by: str | None = None,
        assigned_by: str | None = None,
        mentioned_by: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """List issues in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            state: Filter issues by state.
            labels: Filter issues by labels.
            search_string: Filter issues by search string.
            issue_type: Filter by issue type.
            milestones: Filter issues by milestones.
            since: Filter issues updated since this time.
            before: Filter issues updated before this time.
            created_by: Filter issues created by this user.
            assigned_by: Filter issues assigned to this user.
            mentioned_by: Filter issues mentioning this user.
            page: The page number for pagination.
            limit: The number of issues per page.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_issues_helper(
            owner=owner,
            repository=repository,
            state=state,
            labels=labels,
            search_string=search_string,
            issue_type=issue_type,
            milestones=milestones,
            since=since,
            before=before,
            created_by=created_by,
            assigned_by=assigned_by,
            mentioned_by=mentioned_by,
            page=page,
            limit=limit,
        )
        return await self._get(endpoint=endpoint, params=params, **kwargs)

    async def list_issues(  # noqa: PLR0913
        self,
        owner: str,
        repository: str,
        state: Literal["closed", "open", "all"] | None = None,
        labels: list[str] | None = None,
        search_string: str | None = None,
        issue_type: Literal["Issues", "pulls"] | None = None,
        milestones: list[str] | list[int] | None = None,
        since: datetime | None = None,
        before: datetime | None = None,
        created_by: str | None = None,
        assigned_by: str | None = None,
        mentioned_by: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], int]:
        """List issues in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            state: Filter issues by state.
            labels: Filter issues by labels.
            search_string: Filter issues by search string.
            issue_type: Filter by issue type.
            milestones: Filter issues by milestones.
            since: Filter issues updated since this time.
            before: Filter issues updated before this time.
            created_by: Filter issues created by this user.
            assigned_by: Filter issues assigned to this user.
            mentioned_by: Filter issues mentioning this user.
            page: The page number for pagination.
            limit: The number of issues per page.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the list of issues as a list of dictionaries and the status code.

        """
        response = await self._list_issues(
            owner=owner,
            repository=repository,
            state=state,
            labels=labels,
            search_string=search_string,
            issue_type=issue_type,
            milestones=milestones,
            since=since,
            before=before,
            created_by=created_by,
            assigned_by=assigned_by,
            mentioned_by=mentioned_by,
            page=page,
            limit=limit,
            **kwargs,
        )
        data, status_code = await process_async_response(response)
        return cast(list[dict[str, Any]], data), status_code

    async def _get_issue(self, owner: str, repository: str, index: int, **kwargs: Any) -> ClientResponse:
        """Get a single issue by its index.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._get_issue_helper(owner=owner, repository=repository, index=index)
        return await self._get(endpoint=endpoint, **kwargs)

    async def get_issue(self, owner: str, repository: str, index: int, **kwargs: Any) -> tuple[dict[str, Any], int]:
        """Get a single issue by its index.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the issue as a dictionary and the status code.

        """
        response = await self._get_issue(owner=owner, repository=repository, index=index, **kwargs)
        data, status_code = await process_async_response(response)
        return cast(dict[str, Any], data), status_code
