"""Base class for Gitea Comment resource."""

from __future__ import annotations

from typing import Any


class BaseComment:
    """Base class for Gitea Comment resource."""

    def _list_comments_endpoint(self, owner: str, repository: str, index: int) -> str:
        """Construct the endpoint URL for listing comments on an issue.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.

        Returns:
            The endpoint URL for listing comments.

        """
        return f"/repos/{owner}/{repository}/issues/{index}/comments"

    def _list_comments_helper(
        self,
        owner: str,
        repository: str,
        index: int,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing comments on an issue.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            page: The page number for pagination.
            limit: The number of comments per page.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._list_comments_endpoint(owner=owner, repository=repository, index=index)

        params = {}
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        return endpoint, params

    def _create_comment_endpoint(self, owner: str, repository: str, index: int) -> str:
        """Construct the endpoint URL for creating a comment on an issue.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.

        Returns:
            The endpoint URL for creating a comment.

        """
        return f"/repos/{owner}/{repository}/issues/{index}/comments"

    def _create_comment_helper(
        self,
        owner: str,
        repository: str,
        index: int,
        body: str,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for creating a comment on an issue.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            body: The body of the comment.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._create_comment_endpoint(owner=owner, repository=repository, index=index)
        return endpoint, {"body": body}

    def _edit_comment_endpoint(self, owner: str, repository: str, comment_id: int) -> str:
        """Construct the endpoint URL for editing a comment.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            comment_id: The ID of the comment.

        Returns:
            The endpoint URL for editing a comment.

        """
        return f"/repos/{owner}/{repository}/issues/comments/{comment_id}"

    def _edit_comment_helper(
        self,
        owner: str,
        repository: str,
        comment_id: int,
        body: str,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for editing a comment.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            comment_id: The ID of the comment.
            body: The new body of the comment.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._edit_comment_endpoint(owner=owner, repository=repository, comment_id=comment_id)
        return endpoint, {"body": body}

    def _delete_comment_endpoint(self, owner: str, repository: str, comment_id: int) -> str:
        """Construct the endpoint URL for deleting a comment.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            comment_id: The ID of the comment.

        Returns:
            The endpoint URL for deleting a comment.

        """
        return f"/repos/{owner}/{repository}/issues/comments/{comment_id}"

    def _delete_comment_helper(self, owner: str, repository: str, comment_id: int) -> str:
        """Get the endpoint for deleting a comment.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            comment_id: The ID of the comment.

        Returns:
            The endpoint URL for deleting a comment.

        """
        return self._delete_comment_endpoint(owner=owner, repository=repository, comment_id=comment_id)
