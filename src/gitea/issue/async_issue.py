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

    async def _list_issues(
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

    async def list_issues(
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
        data, status_code = await process_async_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

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

    async def get_issue(
        self, owner: str, repository: str, index: int, **kwargs: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
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
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _edit_issue(
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
    ) -> ClientResponse:
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
        return await self._patch(endpoint=endpoint, json=payload, **kwargs)

    async def edit_issue(
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
            A tuple containing the edited issue as a dictionary and the status code.

        """
        response = await self._edit_issue(
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
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _create_issue(
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
    ) -> ClientResponse:
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
        return await self._post(endpoint=endpoint, json=payload, **kwargs)

    async def create_issue(
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
        response = await self._create_issue(
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
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _list_issue_dependencies(
        self,
        owner: str,
        repository: str,
        index: int,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
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
        return await self._get(endpoint=endpoint, params=params, **kwargs)

    async def list_issue_dependencies(
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
        response = await self._list_issue_dependencies(
            owner=owner,
            repository=repository,
            index=index,
            page=page,
            limit=limit,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    async def _create_issue_dependency(
        self,
        owner: str,
        repository: str,
        index: int,
        dependency_owner: str,
        dependency_repository: str,
        dependency_index: int,
        **kwargs: Any,
    ) -> ClientResponse:
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
        return await self._post(endpoint=endpoint, json=payload, **kwargs)

    async def create_issue_dependency(
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
        response = await self._create_issue_dependency(
            owner=owner,
            repository=repository,
            index=index,
            dependency_owner=dependency_owner,
            dependency_repository=dependency_repository,
            dependency_index=dependency_index,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _remove_issue_dependency(
        self,
        owner: str,
        repository: str,
        index: int,
        dependency_owner: str,
        dependency_repository: str,
        dependency_index: int,
        **kwargs: Any,
    ) -> ClientResponse:
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
        return await self._delete(endpoint=endpoint, json=payload, **kwargs)

    async def remove_issue_dependency(
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
        response = await self._remove_issue_dependency(
            owner=owner,
            repository=repository,
            index=index,
            dependency_owner=dependency_owner,
            dependency_repository=dependency_repository,
            dependency_index=dependency_index,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _list_issue_labels(
        self,
        owner: str,
        repository: str,
        index: int,
        **kwargs: Any,
    ) -> ClientResponse:
        """List the labels of an issue.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._issue_labels_endpoint(owner=owner, repository=repository, index=index)
        return await self._get(endpoint=endpoint, **kwargs)

    async def list_issue_labels(
        self,
        owner: str,
        repository: str,
        index: int,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """List the labels of an issue.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing a list of the issue's labels as dictionaries and a dictionary with metadata.

        """
        response = await self._list_issue_labels(owner=owner, repository=repository, index=index, **kwargs)
        data, status_code = await process_async_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    async def _add_issue_labels(
        self,
        owner: str,
        repository: str,
        index: int,
        labels: list[int | str],
        **kwargs: Any,
    ) -> ClientResponse:
        """Add labels to an issue, keeping the labels it already has.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            labels: The labels to add, as IDs or, on a Gitea recent enough to accept them, names.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._issue_labels_helper(owner=owner, repository=repository, index=index, labels=labels)
        return await self._post(endpoint=endpoint, json=payload, **kwargs)

    async def add_issue_labels(
        self,
        owner: str,
        repository: str,
        index: int,
        labels: list[int | str],
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Add labels to an issue, keeping the labels it already has.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            labels: The labels to add, as IDs or, on a Gitea recent enough to accept them, names.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing a list of the issue's resulting labels as dictionaries and a dictionary with metadata.

        """
        response = await self._add_issue_labels(
            owner=owner, repository=repository, index=index, labels=labels, **kwargs
        )
        data, status_code = await process_async_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    async def _replace_issue_labels(
        self,
        owner: str,
        repository: str,
        index: int,
        labels: list[int | str],
        **kwargs: Any,
    ) -> ClientResponse:
        """Replace every label of an issue with the given ones.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            labels: The labels the issue is left with, as IDs or, on a Gitea recent enough to accept them, names.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._issue_labels_helper(owner=owner, repository=repository, index=index, labels=labels)
        return await self._put(endpoint=endpoint, json=payload, **kwargs)

    async def replace_issue_labels(
        self,
        owner: str,
        repository: str,
        index: int,
        labels: list[int | str],
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Replace every label of an issue with the given ones.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            labels: The labels the issue is left with, as IDs or, on a Gitea recent enough to accept them, names.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing a list of the issue's resulting labels as dictionaries and a dictionary with metadata.

        """
        response = await self._replace_issue_labels(
            owner=owner, repository=repository, index=index, labels=labels, **kwargs
        )
        data, status_code = await process_async_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    async def _remove_issue_label(
        self,
        owner: str,
        repository: str,
        index: int,
        label: int,
        **kwargs: Any,
    ) -> ClientResponse:
        """Remove one label from an issue.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            label: The ID of the label to remove.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._issue_label_endpoint(owner=owner, repository=repository, index=index, label=label)
        return await self._delete(endpoint=endpoint, **kwargs)

    async def remove_issue_label(
        self,
        owner: str,
        repository: str,
        index: int,
        label: int,
        **kwargs: Any,
    ) -> tuple[None, dict[str, Any]]:
        """Remove one label from an issue.

        Gitea answers `204 No Content`, so there is no data; list the issue's
        labels to read back what it is left with.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            label: The ID of the label to remove.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing None and a dictionary with metadata.

        """
        response = await self._remove_issue_label(
            owner=owner, repository=repository, index=index, label=label, **kwargs
        )
        _, status_code = await process_async_response(response)
        return None, {"status_code": status_code}

    async def _clear_issue_labels(
        self,
        owner: str,
        repository: str,
        index: int,
        **kwargs: Any,
    ) -> ClientResponse:
        """Remove every label from an issue.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._issue_labels_endpoint(owner=owner, repository=repository, index=index)
        return await self._delete(endpoint=endpoint, **kwargs)

    async def clear_issue_labels(
        self,
        owner: str,
        repository: str,
        index: int,
        **kwargs: Any,
    ) -> tuple[None, dict[str, Any]]:
        """Remove every label from an issue.

        Gitea answers `204 No Content`, so there is no data.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            index: The index of the issue.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing None and a dictionary with metadata.

        """
        response = await self._clear_issue_labels(owner=owner, repository=repository, index=index, **kwargs)
        _, status_code = await process_async_response(response)
        return None, {"status_code": status_code}
