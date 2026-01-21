"""Base class for Gitea Issue resource."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal


class BaseIssue:
    """Base class for Gitea Issue resource."""

    def _list_issues_endpoint(self, owner: str, repository: str) -> str:
        """Construct the endpoint URL for listing issues in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.

        Returns:
            The endpoint URL for listing issues.

        """
        return f"/repos/{owner}/{repository}/issues"

    def _list_issues_helper(  # noqa: PLR0913
        self,
        owner: str,
        repository: str,
        state: Literal["closed", "open", "all"] | None = None,
        labels: list[str] | None = None,
        search_string: str | None = None,
        issue_type: Literal["issues", "pulls"] | None = None,
        milestones: list[str] | list[int] | None = None,
        since: datetime | None = None,
        before: datetime | None = None,
        created_by: str | None = None,
        assigned_by: str | None = None,
        mentioned_by: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing issues in a repository.

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

        Returns:
            A tuple containing the endpoint and the request arguments.

                - The API endpoint for listing issues.
                - A dictionary of request arguments.

        """
        endpoint = self._list_issues_endpoint(owner=owner, repository=repository)

        params = {}
        if state is not None:
            params["state"] = state
        if labels is not None:
            params["labels"] = ",".join(labels)
        if search_string is not None:
            params["q"] = search_string
        if issue_type is not None:
            params["type"] = issue_type
        if milestones is not None:
            params["milestone"] = ",".join(str(m) for m in milestones)
        if since is not None:
            params["since"] = since.isoformat()
        if before is not None:
            params["before"] = before.isoformat()
        if created_by is not None:
            params["created_by"] = created_by
        if assigned_by is not None:
            params["assigned_by"] = assigned_by
        if mentioned_by is not None:
            params["mentioned_by"] = mentioned_by
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        return endpoint, params

    def _get_issue_endpoint(self, owner: str, repository: str, index: int) -> str:
        """Construct the endpoint URL for a specific issue in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.

        Returns:
            The endpoint URL for the specific issue.

        """
        return f"/repos/{owner}/{repository}/issues/{index}"

    def _get_issue_helper(self, owner: str, repository: str, index: int) -> str:
        """Get the endpoint and parameters for retrieving a specific issue in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.

        Returns:
            The API endpoint for retrieving the specific issue.

        """
        endpoint = self._get_issue_endpoint(owner=owner, repository=repository, index=index)
        return endpoint

    def _edit_issue_endpoint(self, owner: str, repository: str, index: int) -> str:
        """Construct the endpoint URL for editing a specific issue in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.

        Returns:
            The endpoint URL for editing the specific issue.

        """
        return f"/repos/{owner}/{repository}/issues/{index}"

    def _edit_issue_helper(  # noqa: PLR0913
        self,
        owner: str,
        repository: str,
        index: int,
        assignee: str | None = None,
        assignees: list[str] | None = None,
        body: str | None = None,
        due_date: datetime | None = None,
        milestone: int | None = None,
        ref: str | None = None,
        state: Literal["closed", "open", "all"] | None = None,
        title: str | None = None,
        unset_due_date: bool | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for editing a specific issue in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            assignee: The new assignee of the issue.
            assignees: The new assignees of the issue.
            body: The new body of the issue.
            due_date: The new due date of the issue.
            milestone: The new milestone of the issue.
            ref: The new reference of the issue.
            state: The new state of the issue.
            title: The new title of the issue.
            unset_due_date: Whether to unset the due date of the issue.

        Returns:
            A tuple containing the endpoint and the request arguments.

                - The API endpoint for editing the specific issue.
                - A dictionary of request arguments.

        """
        endpoint = self._edit_issue_endpoint(owner=owner, repository=repository, index=index)

        payload = {}

        if assignee is not None:
            payload["assignee"] = assignee
        if assignees is not None:
            payload["assignees"] = assignees
        if body is not None:
            payload["body"] = body
        if due_date is not None:
            payload["due_date"] = due_date.isoformat()
        if milestone is not None:
            payload["milestone"] = milestone
        if ref is not None:
            payload["ref"] = ref
        if state is not None:
            payload["state"] = state
        if title is not None:
            payload["title"] = title
        if unset_due_date is not None:
            payload["unset_due_date"] = unset_due_date

        return endpoint, payload
