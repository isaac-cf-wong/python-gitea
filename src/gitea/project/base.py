"""Base class for Gitea Project resource."""

from __future__ import annotations

from typing import Any, Literal


class BaseProject:
    """Base class for Gitea Project resource."""

    def _list_projects_endpoint(self, owner: str, repository: str) -> str:
        """Construct the endpoint URL for listing projects in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.

        Returns:
            The endpoint URL for listing projects.

        """
        return f"/repos/{owner}/{repository}/projects"

    def _list_projects_helper(
        self,
        owner: str,
        repository: str,
        state: Literal["open", "closed", "all"] | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing projects in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            state: Filter projects by state.
            page: The page number for pagination.
            limit: The number of projects per page.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._list_projects_endpoint(owner=owner, repository=repository)

        params = {}
        if state is not None:
            params["state"] = state
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        return endpoint, params

    def _get_project_endpoint(self, owner: str, repository: str, project_id: int) -> str:
        """Construct the endpoint URL for getting a project in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.

        Returns:
            The endpoint URL for getting the project.

        """
        return f"/repos/{owner}/{repository}/projects/{project_id}"

    def _get_project_helper(self, owner: str, repository: str, project_id: int) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for getting a project in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._get_project_endpoint(owner=owner, repository=repository, project_id=project_id)
        return endpoint, {}

    def _create_project_helper(
        self,
        owner: str,
        repository: str,
        title: str,
        description: str | None = None,
        template_type: str | None = None,
        card_type: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and payload for creating a project in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            title: The title of the project.
            description: The description of the project.
            template_type: The template type of the project.
            card_type: The card type of the project.

        Returns:
            A tuple containing the endpoint and the request payload.

        """
        endpoint = self._list_projects_endpoint(owner=owner, repository=repository)

        payload: dict[str, Any] = {"title": title}

        if description is not None:
            payload["description"] = description
        if template_type is not None:
            payload["template_type"] = template_type
        if card_type is not None:
            payload["card_type"] = card_type

        return endpoint, payload

    def _edit_project_helper(
        self,
        owner: str,
        repository: str,
        project_id: int,
        title: str | None = None,
        description: str | None = None,
        card_type: str | None = None,
        state: Literal["open", "closed"] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and payload for editing a project in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.
            title: The title of the project.
            description: The description of the project.
            card_type: The card type of the project.
            state: The state of the project.

        Returns:
            A tuple containing the endpoint and the request payload.

        """
        endpoint = self._get_project_endpoint(owner=owner, repository=repository, project_id=project_id)

        payload: dict[str, Any] = {}

        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        if card_type is not None:
            payload["card_type"] = card_type
        if state is not None:
            payload["state"] = state

        return endpoint, payload

    def _delete_project_helper(self, owner: str, repository: str, project_id: int) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for deleting a project in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._get_project_endpoint(owner=owner, repository=repository, project_id=project_id)
        return endpoint, {}

    def _list_project_columns_endpoint(self, owner: str, repository: str, project_id: int) -> str:
        """Construct the endpoint URL for listing a project's columns.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.

        Returns:
            The endpoint URL for listing the project's columns.

        """
        return f"/repos/{owner}/{repository}/projects/{project_id}/columns"

    def _list_project_columns_helper(
        self,
        owner: str,
        repository: str,
        project_id: int,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing a project's columns.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.
            page: The page number for pagination.
            limit: The number of columns per page.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._list_project_columns_endpoint(owner=owner, repository=repository, project_id=project_id)

        params = {}
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        return endpoint, params

    def _create_project_column_helper(
        self,
        owner: str,
        repository: str,
        project_id: int,
        title: str,
        color: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and payload for creating a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.
            title: The title of the column.
            color: The color of the column in 6-digit hex format.

        Returns:
            A tuple containing the endpoint and the request payload.

        """
        endpoint = self._list_project_columns_endpoint(owner=owner, repository=repository, project_id=project_id)

        payload: dict[str, Any] = {"title": title}

        if color is not None:
            payload["color"] = color

        return endpoint, payload

    def _get_project_column_endpoint(self, owner: str, repository: str, project_id: int, column_id: int) -> str:
        """Construct the endpoint URL for getting a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.
            column_id: The ID of the column.

        Returns:
            The endpoint URL for getting the project column.

        """
        return f"/repos/{owner}/{repository}/projects/{project_id}/columns/{column_id}"

    def _get_project_column_helper(
        self,
        owner: str,
        repository: str,
        project_id: int,
        column_id: int,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for getting a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.
            column_id: The ID of the column.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._get_project_column_endpoint(
            owner=owner, repository=repository, project_id=project_id, column_id=column_id
        )
        return endpoint, {}

    def _edit_project_column_helper(
        self,
        owner: str,
        repository: str,
        project_id: int,
        column_id: int,
        title: str | None = None,
        color: str | None = None,
        sorting: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and payload for editing a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.
            column_id: The ID of the column.
            title: The title of the column.
            color: The color of the column in 6-digit hex format.
            sorting: The position of the column within the project.

        Returns:
            A tuple containing the endpoint and the request payload.

        """
        endpoint = self._get_project_column_endpoint(
            owner=owner, repository=repository, project_id=project_id, column_id=column_id
        )

        payload: dict[str, Any] = {}

        if title is not None:
            payload["title"] = title
        if color is not None:
            payload["color"] = color
        if sorting is not None:
            payload["sorting"] = sorting

        return endpoint, payload

    def _delete_project_column_helper(
        self,
        owner: str,
        repository: str,
        project_id: int,
        column_id: int,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for deleting a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.
            column_id: The ID of the column.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._get_project_column_endpoint(
            owner=owner, repository=repository, project_id=project_id, column_id=column_id
        )
        return endpoint, {}

    def _set_default_project_column_helper(
        self,
        owner: str,
        repository: str,
        project_id: int,
        column_id: int,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for setting a project's default column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.
            column_id: The ID of the column.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = f"/repos/{owner}/{repository}/projects/{project_id}/columns/{column_id}/default"
        return endpoint, {}

    def _move_project_columns_helper(
        self,
        owner: str,
        repository: str,
        project_id: int,
        column_ids: list[int],
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and payload for reordering a project's columns.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.
            column_ids: Every column ID of the project, in the desired left-to-right order.

        Returns:
            A tuple containing the endpoint and the request payload.

        """
        endpoint = f"/repos/{owner}/{repository}/projects/{project_id}/columns/move"

        payload: dict[str, Any] = {"column_ids": column_ids}

        return endpoint, payload

    def _list_project_column_issues_endpoint(
        self,
        owner: str,
        repository: str,
        project_id: int,
        column_id: int,
    ) -> str:
        """Construct the endpoint URL for listing issues in a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.
            column_id: The ID of the column.

        Returns:
            The endpoint URL for listing issues in the project column.

        """
        return f"/repos/{owner}/{repository}/projects/{project_id}/columns/{column_id}/issues"

    def _list_project_column_issues_helper(
        self,
        owner: str,
        repository: str,
        project_id: int,
        column_id: int,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing issues in a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.
            column_id: The ID of the column.
            page: The page number for pagination.
            limit: The number of issues per page.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._list_project_column_issues_endpoint(
            owner=owner, repository=repository, project_id=project_id, column_id=column_id
        )

        params = {}
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        return endpoint, params

    def _add_issue_to_project_column_helper(
        self,
        owner: str,
        repository: str,
        project_id: int,
        column_id: int,
        issue_id: int,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for adding an issue to a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.
            column_id: The ID of the column.
            issue_id: The ID of the issue.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = f"/repos/{owner}/{repository}/projects/{project_id}/columns/{column_id}/issues/{issue_id}"
        return endpoint, {}

    def _remove_issue_from_project_column_helper(
        self,
        owner: str,
        repository: str,
        project_id: int,
        column_id: int,
        issue_id: int,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for removing an issue from a project column.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.
            column_id: The ID of the column.
            issue_id: The ID of the issue.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = f"/repos/{owner}/{repository}/projects/{project_id}/columns/{column_id}/issues/{issue_id}"
        return endpoint, {}

    def _move_project_issue_helper(
        self,
        owner: str,
        repository: str,
        project_id: int,
        issue_id: int,
        column_id: int,
        sorting: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and payload for moving an issue between a project's columns.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            project_id: The ID of the project.
            issue_id: The ID of the issue.
            column_id: The target column ID.
            sorting: The position within the column, ascending.

        Returns:
            A tuple containing the endpoint and the request payload.

        """
        endpoint = f"/repos/{owner}/{repository}/projects/{project_id}/issues/{issue_id}/move"

        payload: dict[str, Any] = {"column_id": column_id}

        if sorting is not None:
            payload["sorting"] = sorting

        return endpoint, payload
