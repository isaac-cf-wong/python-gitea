"""Gitea Issue resource."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, cast

from requests import Response

from gitea.issue.base import BaseIssue
from gitea.resource.resource import Resource
from gitea.utils.response import process_response


class Issue(BaseIssue, Resource):
    """Gitea Issue resource."""

    def _list_issues(
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
        **kwargs: Any,
    ) -> Response:
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
        return self._get(endpoint=endpoint, params=params, **kwargs)

    def list_issues(
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
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
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
            A tuple containing a list of issues as dictionaries and a dictionary with metadata.

        """
        response = self._list_issues(
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
        data, status_code = process_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    def _get_issue(self, owner: str, repository: str, index: int, **kwargs: Any) -> Response:
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
        return self._get(endpoint=endpoint, **kwargs)

    def get_issue(
        self, owner: str, repository: str, index: int, **kwargs: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Get a single issue by its index.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the issue as a dictionary and a dictionary with metadata.

        """
        response = self._get_issue(owner=owner, repository=repository, index=index, **kwargs)
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _edit_issue(
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
        state: Literal["closed", "open"] | None = None,
        title: str | None = None,
        unset_due_date: bool | None = None,
        **kwargs: Any,
    ) -> Response:
        """Edit a specific issue in a repository.

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
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._edit_issue_helper(
            owner=owner,
            repository=repository,
            index=index,
            assignee=assignee,
            assignees=assignees,
            body=body,
            due_date=due_date,
            milestone=milestone,
            ref=ref,
            state=state,
            title=title,
            unset_due_date=unset_due_date,
        )
        return self._patch(endpoint=endpoint, json=payload, **kwargs)

    def edit_issue(
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
        state: Literal["closed", "open"] | None = None,
        title: str | None = None,
        unset_due_date: bool | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Edit a specific issue in a repository.

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
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the updated issue as a dictionary and a dictionary with metadata.

        """
        response = self._edit_issue(
            owner=owner,
            repository=repository,
            index=index,
            assignee=assignee,
            assignees=assignees,
            body=body,
            due_date=due_date,
            milestone=milestone,
            ref=ref,
            state=state,
            title=title,
            unset_due_date=unset_due_date,
            **kwargs,
        )
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _create_issue(
        self,
        owner: str,
        repository: str,
        title: str,
        assignee: str | None = None,
        assignees: list[str] | None = None,
        body: str | None = None,
        closed: bool | None = None,
        due_date: datetime | None = None,
        labels: list[int] | None = None,
        milestone: int | None = None,
        ref: str | None = None,
        **kwargs: Any,
    ) -> Response:
        """Create an issue in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            title: The title of the new issue.
            assignee: The username to assign the issue to.
            assignees: The usernames to assign the issue to.
            body: The body of the new issue.
            closed: Whether the issue is created closed.
            due_date: The due date of the new issue.
            labels: The label IDs to apply to the new issue.
            milestone: The milestone ID to associate with the new issue.
            ref: The reference of the new issue.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._create_issue_helper(
            owner=owner,
            repository=repository,
            title=title,
            assignee=assignee,
            assignees=assignees,
            body=body,
            closed=closed,
            due_date=due_date,
            labels=labels,
            milestone=milestone,
            ref=ref,
        )
        return self._post(endpoint=endpoint, json=payload, **kwargs)

    def create_issue(
        self,
        owner: str,
        repository: str,
        title: str,
        assignee: str | None = None,
        assignees: list[str] | None = None,
        body: str | None = None,
        closed: bool | None = None,
        due_date: datetime | None = None,
        labels: list[int] | None = None,
        milestone: int | None = None,
        ref: str | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Create an issue in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            title: The title of the new issue.
            assignee: The username to assign the issue to.
            assignees: The usernames to assign the issue to.
            body: The body of the new issue.
            closed: Whether the issue is created closed.
            due_date: The due date of the new issue.
            labels: The label IDs to apply to the new issue.
            milestone: The milestone ID to associate with the new issue.
            ref: The reference of the new issue.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the created issue as a dictionary and a dictionary with metadata.

        """
        response = self._create_issue(
            owner=owner,
            repository=repository,
            title=title,
            assignee=assignee,
            assignees=assignees,
            body=body,
            closed=closed,
            due_date=due_date,
            labels=labels,
            milestone=milestone,
            ref=ref,
            **kwargs,
        )
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _list_issue_dependencies(
        self,
        owner: str,
        repository: str,
        index: int,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> Response:
        """List an issue's dependencies.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            page: The page number for pagination.
            limit: The number of dependencies per page.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_issue_dependencies_helper(
            owner=owner,
            repository=repository,
            index=index,
            page=page,
            limit=limit,
        )
        return self._get(endpoint=endpoint, params=params, **kwargs)

    def list_issue_dependencies(
        self,
        owner: str,
        repository: str,
        index: int,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """List an issue's dependencies.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            page: The page number for pagination.
            limit: The number of dependencies per page.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing a list of dependency issues as dictionaries and a dictionary with metadata.

        """
        response = self._list_issue_dependencies(
            owner=owner,
            repository=repository,
            index=index,
            page=page,
            limit=limit,
            **kwargs,
        )
        data, status_code = process_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    def _create_issue_dependency(
        self,
        owner: str,
        repository: str,
        index: int,
        dependency_owner: str,
        dependency_repository: str,
        dependency_index: int,
        **kwargs: Any,
    ) -> Response:
        """Make an issue depend on another issue.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the target issue.
            dependency_owner: The owner of the dependency issue's repository.
            dependency_repository: The name of the dependency issue's repository.
            dependency_index: The index of the dependency issue.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._create_issue_dependency_helper(
            owner=owner,
            repository=repository,
            index=index,
            dependency_owner=dependency_owner,
            dependency_repository=dependency_repository,
            dependency_index=dependency_index,
        )
        return self._post(endpoint=endpoint, json=payload, **kwargs)

    def create_issue_dependency(
        self,
        owner: str,
        repository: str,
        index: int,
        dependency_owner: str,
        dependency_repository: str,
        dependency_index: int,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Make an issue depend on another issue.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the target issue.
            dependency_owner: The owner of the dependency issue's repository.
            dependency_repository: The name of the dependency issue's repository.
            dependency_index: The index of the dependency issue.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the target issue as a dictionary and a dictionary with metadata.

        """
        response = self._create_issue_dependency(
            owner=owner,
            repository=repository,
            index=index,
            dependency_owner=dependency_owner,
            dependency_repository=dependency_repository,
            dependency_index=dependency_index,
            **kwargs,
        )
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _remove_issue_dependency(
        self,
        owner: str,
        repository: str,
        index: int,
        dependency_owner: str,
        dependency_repository: str,
        dependency_index: int,
        **kwargs: Any,
    ) -> Response:
        """Remove an issue dependency.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the target issue.
            dependency_owner: The owner of the dependency issue's repository.
            dependency_repository: The name of the dependency issue's repository.
            dependency_index: The index of the dependency issue.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._remove_issue_dependency_helper(
            owner=owner,
            repository=repository,
            index=index,
            dependency_owner=dependency_owner,
            dependency_repository=dependency_repository,
            dependency_index=dependency_index,
        )
        return self._delete(endpoint=endpoint, json=payload, **kwargs)

    def remove_issue_dependency(
        self,
        owner: str,
        repository: str,
        index: int,
        dependency_owner: str,
        dependency_repository: str,
        dependency_index: int,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Remove an issue dependency.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the target issue.
            dependency_owner: The owner of the dependency issue's repository.
            dependency_repository: The name of the dependency issue's repository.
            dependency_index: The index of the dependency issue.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the target issue as a dictionary and a dictionary with metadata.

        """
        response = self._remove_issue_dependency(
            owner=owner,
            repository=repository,
            index=index,
            dependency_owner=dependency_owner,
            dependency_repository=dependency_repository,
            dependency_index=dependency_index,
            **kwargs,
        )
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}
