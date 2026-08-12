"""Asynchronous Gitea Project resource."""

from __future__ import annotations

from typing import Any, Literal, cast

from aiohttp import ClientResponse

from gitea.project.base import BaseProject
from gitea.resource.async_resource import AsyncResource
from gitea.utils.response import process_async_response


class AsyncProject(BaseProject, AsyncResource):
    """Asynchronous Gitea Project resource."""

    async def _list_projects(
        self,
        owner: str,
        repository: str | None,
        state: Literal["open", "closed", "all"] | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """List projects.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            state: Filter projects by state.
            page: The page number for pagination.
            limit: The number of projects per page.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_projects_helper(
            owner=owner,
            repository=repository,
            state=state,
            page=page,
            limit=limit,
        )
        return await self._get(endpoint=endpoint, params=params, **kwargs)

    async def list_projects(
        self,
        owner: str,
        repository: str | None,
        state: Literal["open", "closed", "all"] | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """List projects.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            state: Filter projects by state.
            page: The page number for pagination.
            limit: The number of projects per page.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing a list of projects as dictionaries and a dictionary with metadata.

        """
        response = await self._list_projects(
            owner=owner,
            repository=repository,
            state=state,
            page=page,
            limit=limit,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    async def _get_project(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        **kwargs: Any,
    ) -> ClientResponse:
        """Get a project.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._get_project_helper(
            owner=owner,
            repository=repository,
            project_id=project_id,
        )
        return await self._get(endpoint=endpoint, params=params, **kwargs)

    async def get_project(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Get a project.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the project as a dictionary and a dictionary with metadata.

        """
        response = await self._get_project(
            owner=owner,
            repository=repository,
            project_id=project_id,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _create_project(
        self,
        owner: str,
        repository: str | None,
        title: str,
        description: str | None = None,
        template_type: str | None = None,
        card_type: str | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """Create a project.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            title: The title of the project.
            description: The description of the project.
            template_type: The template type of the project.
            card_type: The card type of the project.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._create_project_helper(
            owner=owner,
            repository=repository,
            title=title,
            description=description,
            template_type=template_type,
            card_type=card_type,
        )
        return await self._post(endpoint=endpoint, json=payload, **kwargs)

    async def create_project(
        self,
        owner: str,
        repository: str | None,
        title: str,
        description: str | None = None,
        template_type: str | None = None,
        card_type: str | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Create a project.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            title: The title of the project.
            description: The description of the project.
            template_type: The template type of the project.
            card_type: The card type of the project.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the created project as a dictionary and a dictionary with metadata.

        """
        response = await self._create_project(
            owner=owner,
            repository=repository,
            title=title,
            description=description,
            template_type=template_type,
            card_type=card_type,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _edit_project(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        title: str | None = None,
        description: str | None = None,
        card_type: str | None = None,
        state: Literal["open", "closed"] | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """Edit a project.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            title: The title of the project.
            description: The description of the project.
            card_type: The card type of the project.
            state: The state of the project.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._edit_project_helper(
            owner=owner,
            repository=repository,
            project_id=project_id,
            title=title,
            description=description,
            card_type=card_type,
            state=state,
        )
        return await self._patch(endpoint=endpoint, json=payload, **kwargs)

    async def edit_project(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        title: str | None = None,
        description: str | None = None,
        card_type: str | None = None,
        state: Literal["open", "closed"] | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Edit a project.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            title: The title of the project.
            description: The description of the project.
            card_type: The card type of the project.
            state: The state of the project.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the edited project as a dictionary and a dictionary with metadata.

        """
        response = await self._edit_project(
            owner=owner,
            repository=repository,
            project_id=project_id,
            title=title,
            description=description,
            card_type=card_type,
            state=state,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _delete_project(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        **kwargs: Any,
    ) -> ClientResponse:
        """Delete a project.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._delete_project_helper(
            owner=owner,
            repository=repository,
            project_id=project_id,
        )
        return await self._delete(endpoint=endpoint, params=params, **kwargs)

    async def delete_project(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Delete a project.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the response as a dictionary and a dictionary with metadata.

        """
        response = await self._delete_project(
            owner=owner,
            repository=repository,
            project_id=project_id,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _list_project_columns(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """List a project's columns.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            page: The page number for pagination.
            limit: The number of columns per page.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_project_columns_helper(
            owner=owner,
            repository=repository,
            project_id=project_id,
            page=page,
            limit=limit,
        )
        return await self._get(endpoint=endpoint, params=params, **kwargs)

    async def list_project_columns(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """List a project's columns.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            page: The page number for pagination.
            limit: The number of columns per page.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing a list of columns as dictionaries and a dictionary with metadata.

        """
        response = await self._list_project_columns(
            owner=owner,
            repository=repository,
            project_id=project_id,
            page=page,
            limit=limit,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    async def _create_project_column(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        title: str,
        color: str | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """Create a column in a project.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            title: The title of the column.
            color: The color of the column in 6-digit hex format.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._create_project_column_helper(
            owner=owner,
            repository=repository,
            project_id=project_id,
            title=title,
            color=color,
        )
        return await self._post(endpoint=endpoint, json=payload, **kwargs)

    async def create_project_column(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        title: str,
        color: str | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Create a column in a project.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            title: The title of the column.
            color: The color of the column in 6-digit hex format.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the created column as a dictionary and a dictionary with metadata.

        """
        response = await self._create_project_column(
            owner=owner,
            repository=repository,
            project_id=project_id,
            title=title,
            color=color,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _get_project_column(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        column_id: int,
        **kwargs: Any,
    ) -> ClientResponse:
        """Get a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            column_id: The ID of the column.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._get_project_column_helper(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
        )
        return await self._get(endpoint=endpoint, params=params, **kwargs)

    async def get_project_column(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        column_id: int,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Get a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            column_id: The ID of the column.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the column as a dictionary and a dictionary with metadata.

        """
        response = await self._get_project_column(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _edit_project_column(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        column_id: int,
        title: str | None = None,
        color: str | None = None,
        sorting: int | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """Edit a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            column_id: The ID of the column.
            title: The title of the column.
            color: The color of the column in 6-digit hex format.
            sorting: The position of the column within the project.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._edit_project_column_helper(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
            title=title,
            color=color,
            sorting=sorting,
        )
        return await self._patch(endpoint=endpoint, json=payload, **kwargs)

    async def edit_project_column(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        column_id: int,
        title: str | None = None,
        color: str | None = None,
        sorting: int | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Edit a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            column_id: The ID of the column.
            title: The title of the column.
            color: The color of the column in 6-digit hex format.
            sorting: The position of the column within the project.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the edited column as a dictionary and a dictionary with metadata.

        """
        response = await self._edit_project_column(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
            title=title,
            color=color,
            sorting=sorting,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _delete_project_column(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        column_id: int,
        **kwargs: Any,
    ) -> ClientResponse:
        """Delete a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            column_id: The ID of the column.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._delete_project_column_helper(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
        )
        return await self._delete(endpoint=endpoint, params=params, **kwargs)

    async def delete_project_column(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        column_id: int,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Delete a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            column_id: The ID of the column.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the response as a dictionary and a dictionary with metadata.

        """
        response = await self._delete_project_column(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _set_default_project_column(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        column_id: int,
        **kwargs: Any,
    ) -> ClientResponse:
        """Set a project's default column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            column_id: The ID of the column.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._set_default_project_column_helper(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
        )
        return await self._post(endpoint=endpoint, params=params, **kwargs)

    async def set_default_project_column(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        column_id: int,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Set a project's default column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            column_id: The ID of the column.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the response as a dictionary and a dictionary with metadata.

        """
        response = await self._set_default_project_column(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _move_project_columns(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        column_ids: list[int],
        **kwargs: Any,
    ) -> ClientResponse:
        """Reorder a project's columns.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            column_ids: Every column ID of the project, in the desired left-to-right order.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._move_project_columns_helper(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_ids=column_ids,
        )
        return await self._post(endpoint=endpoint, json=payload, **kwargs)

    async def move_project_columns(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        column_ids: list[int],
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Reorder a project's columns.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            column_ids: Every column ID of the project, in the desired left-to-right order.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the response as a dictionary and a dictionary with metadata.

        """
        response = await self._move_project_columns(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_ids=column_ids,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _list_project_column_issues(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        column_id: int,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """List the issues in a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            column_id: The ID of the column.
            page: The page number for pagination.
            limit: The number of issues per page.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_project_column_issues_helper(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
            page=page,
            limit=limit,
        )
        return await self._get(endpoint=endpoint, params=params, **kwargs)

    async def list_project_column_issues(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        column_id: int,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """List the issues in a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            column_id: The ID of the column.
            page: The page number for pagination.
            limit: The number of issues per page.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing a list of issues as dictionaries and a dictionary with metadata.

        """
        response = await self._list_project_column_issues(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
            page=page,
            limit=limit,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    async def _add_issue_to_project_column(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        column_id: int,
        issue_id: int,
        **kwargs: Any,
    ) -> ClientResponse:
        """Add an issue to a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            column_id: The ID of the column.
            issue_id: The ID of the issue.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._project_column_issue_helper(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
            issue_id=issue_id,
        )
        return await self._post(endpoint=endpoint, params=params, **kwargs)

    async def add_issue_to_project_column(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        column_id: int,
        issue_id: int,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Add an issue to a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            column_id: The ID of the column.
            issue_id: The ID of the issue.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the response as a dictionary and a dictionary with metadata.

        """
        response = await self._add_issue_to_project_column(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
            issue_id=issue_id,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _remove_issue_from_project_column(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        column_id: int,
        issue_id: int,
        **kwargs: Any,
    ) -> ClientResponse:
        """Remove an issue from a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            column_id: The ID of the column.
            issue_id: The ID of the issue.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._project_column_issue_helper(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
            issue_id=issue_id,
        )
        return await self._delete(endpoint=endpoint, params=params, **kwargs)

    async def remove_issue_from_project_column(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        column_id: int,
        issue_id: int,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Remove an issue from a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            column_id: The ID of the column.
            issue_id: The ID of the issue.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the response as a dictionary and a dictionary with metadata.

        """
        response = await self._remove_issue_from_project_column(
            owner=owner,
            repository=repository,
            project_id=project_id,
            column_id=column_id,
            issue_id=issue_id,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _move_project_issue(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        issue_id: int,
        column_id: int,
        sorting: int | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """Move an issue between a project's columns.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            issue_id: The ID of the issue.
            column_id: The target column ID.
            sorting: The position within the column, ascending.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._move_project_issue_helper(
            owner=owner,
            repository=repository,
            project_id=project_id,
            issue_id=issue_id,
            column_id=column_id,
            sorting=sorting,
        )
        return await self._post(endpoint=endpoint, json=payload, **kwargs)

    async def move_project_issue(
        self,
        owner: str,
        repository: str | None,
        project_id: int,
        issue_id: int,
        column_id: int,
        sorting: int | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Move an issue between a project's columns.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository, or None for organization projects.
            project_id: The ID of the project.
            issue_id: The ID of the issue.
            column_id: The target column ID.
            sorting: The position within the column, ascending.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the response as a dictionary and a dictionary with metadata.

        """
        response = await self._move_project_issue(
            owner=owner,
            repository=repository,
            project_id=project_id,
            issue_id=issue_id,
            column_id=column_id,
            sorting=sorting,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}
