"""Asynchronous Gitea Comment resource."""

from __future__ import annotations

from typing import Any, cast

from aiohttp import ClientResponse

from gitea.comment.base import BaseComment
from gitea.resource.async_resource import AsyncResource
from gitea.utils.response import process_async_response


class AsyncComment(BaseComment, AsyncResource):
    """Asynchronous Gitea Comment resource."""

    async def _list_comments(
        self,
        owner: str,
        repository: str,
        index: int,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """List comments on an issue.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            page: The page number for pagination.
            limit: The number of comments per page.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_comments_helper(
            owner=owner,
            repository=repository,
            index=index,
            page=page,
            limit=limit,
        )
        return await self._get(endpoint=endpoint, params=params, **kwargs)

    async def list_comments(
        self,
        owner: str,
        repository: str,
        index: int,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """List comments on an issue.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            page: The page number for pagination.
            limit: The number of comments per page.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing a list of comments as dictionaries and a dictionary with metadata.

        """
        response = await self._list_comments(
            owner=owner,
            repository=repository,
            index=index,
            page=page,
            limit=limit,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    async def _create_comment(
        self,
        owner: str,
        repository: str,
        index: int,
        body: str,
        **kwargs: Any,
    ) -> ClientResponse:
        """Create a comment on an issue.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            body: The body of the comment.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._create_comment_helper(
            owner=owner,
            repository=repository,
            index=index,
            body=body,
        )
        return await self._post(endpoint=endpoint, json=payload, **kwargs)

    async def create_comment(
        self,
        owner: str,
        repository: str,
        index: int,
        body: str,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Create a comment on an issue.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            body: The body of the comment.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the created comment as a dictionary and a dictionary with metadata.

        """
        response = await self._create_comment(
            owner=owner,
            repository=repository,
            index=index,
            body=body,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _edit_comment(
        self,
        owner: str,
        repository: str,
        comment_id: int,
        body: str,
        **kwargs: Any,
    ) -> ClientResponse:
        """Edit a comment.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            comment_id: The ID of the comment.
            body: The new body of the comment.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._edit_comment_helper(
            owner=owner,
            repository=repository,
            comment_id=comment_id,
            body=body,
        )
        return await self._patch(endpoint=endpoint, json=payload, **kwargs)

    async def edit_comment(
        self,
        owner: str,
        repository: str,
        comment_id: int,
        body: str,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Edit a comment.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            comment_id: The ID of the comment.
            body: The new body of the comment.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the updated comment as a dictionary and a dictionary with metadata.

        """
        response = await self._edit_comment(
            owner=owner,
            repository=repository,
            comment_id=comment_id,
            body=body,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _delete_comment(
        self,
        owner: str,
        repository: str,
        comment_id: int,
        **kwargs: Any,
    ) -> ClientResponse:
        """Delete a comment.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            comment_id: The ID of the comment.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._delete_comment_helper(owner=owner, repository=repository, comment_id=comment_id)
        return await self._delete(endpoint=endpoint, **kwargs)

    async def delete_comment(
        self,
        owner: str,
        repository: str,
        comment_id: int,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Delete a comment.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            comment_id: The ID of the comment.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing an empty dictionary and a dictionary with metadata.

        """
        response = await self._delete_comment(
            owner=owner,
            repository=repository,
            comment_id=comment_id,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}
