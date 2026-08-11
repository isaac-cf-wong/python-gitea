"""Base class for Gitea Label resource."""

from __future__ import annotations

from typing import Any


class BaseLabel:
    """Base class for Gitea Label resource."""

    def _list_labels_endpoint(self, owner: str, repository: str) -> str:
        """Construct the endpoint URL for listing labels in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.

        Returns:
            The endpoint URL for listing labels.

        """
        return f"/repos/{owner}/{repository}/labels"

    def _list_labels_helper(
        self,
        owner: str,
        repository: str,
        page: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for listing labels in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            page: The page number for pagination.
            limit: The number of labels per page.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._list_labels_endpoint(owner=owner, repository=repository)

        params = {}
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        return endpoint, params

    def _create_label_endpoint(self, owner: str, repository: str) -> str:
        """Construct the endpoint URL for creating a label in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.

        Returns:
            The endpoint URL for creating a label.

        """
        return f"/repos/{owner}/{repository}/labels"

    def _create_label_helper(
        self,
        owner: str,
        repository: str,
        name: str,
        color: str,
        description: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for creating a label in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            name: The name of the label.
            color: The color of the label in hexadecimal format (e.g. ``#00aabb``).
            description: The description of the label.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._create_label_endpoint(owner=owner, repository=repository)

        payload: dict[str, Any] = {"name": name, "color": color}

        if description is not None:
            payload["description"] = description

        return endpoint, payload

    def _edit_label_endpoint(self, owner: str, repository: str, label_id: int) -> str:
        """Construct the endpoint URL for editing a label.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            label_id: The ID of the label.

        Returns:
            The endpoint URL for editing a label.

        """
        return f"/repos/{owner}/{repository}/labels/{label_id}"

    def _edit_label_helper(
        self,
        owner: str,
        repository: str,
        label_id: int,
        name: str | None = None,
        color: str | None = None,
        description: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Get the endpoint and parameters for editing a label.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            label_id: The ID of the label.
            name: The new name of the label.
            color: The new color of the label in hexadecimal format.
            description: The new description of the label.

        Returns:
            A tuple containing the endpoint and the request arguments.

        """
        endpoint = self._edit_label_endpoint(owner=owner, repository=repository, label_id=label_id)

        payload = {}
        if name is not None:
            payload["name"] = name
        if color is not None:
            payload["color"] = color
        if description is not None:
            payload["description"] = description

        return endpoint, payload

    def _delete_label_endpoint(self, owner: str, repository: str, label_id: int) -> str:
        """Construct the endpoint URL for deleting a label.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            label_id: The ID of the label.

        Returns:
            The endpoint URL for deleting a label.

        """
        return f"/repos/{owner}/{repository}/labels/{label_id}"

    def _delete_label_helper(self, owner: str, repository: str, label_id: int) -> str:
        """Get the endpoint for deleting a label.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            label_id: The ID of the label.

        Returns:
            The endpoint URL for deleting a label.

        """
        return self._delete_label_endpoint(owner=owner, repository=repository, label_id=label_id)
