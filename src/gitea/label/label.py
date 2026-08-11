"""Gitea Label resource."""

from __future__ import annotations

from typing import Any, cast

from requests import Response

from gitea.label.base import BaseLabel
from gitea.resource.resource import Resource
from gitea.utils.response import process_response


class Label(BaseLabel, Resource):
    """Gitea Label resource."""

    def _list_labels(
        self,
        owner: str,
        repository: str,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> Response:
        """List labels in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            page: The page number for pagination.
            limit: The number of labels per page.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_labels_helper(
            owner=owner,
            repository=repository,
            page=page,
            limit=limit,
        )
        return self._get(endpoint=endpoint, params=params, **kwargs)

    def list_labels(
        self,
        owner: str,
        repository: str,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """List labels in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            page: The page number for pagination.
            limit: The number of labels per page.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing a list of labels as dictionaries and a dictionary with metadata.

        """
        response = self._list_labels(
            owner=owner,
            repository=repository,
            page=page,
            limit=limit,
            **kwargs,
        )
        data, status_code = process_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    def _create_label(
        self,
        owner: str,
        repository: str,
        name: str,
        color: str,
        description: str | None = None,
        **kwargs: Any,
    ) -> Response:
        """Create a label in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            name: The name of the label.
            color: The color of the label in hexadecimal format (e.g. ``#00aabb``).
            description: The description of the label.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._create_label_helper(
            owner=owner,
            repository=repository,
            name=name,
            color=color,
            description=description,
        )
        return self._post(endpoint=endpoint, json=payload, **kwargs)

    def create_label(
        self,
        owner: str,
        repository: str,
        name: str,
        color: str,
        description: str | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Create a label in a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            name: The name of the label.
            color: The color of the label in hexadecimal format (e.g. ``#00aabb``).
            description: The description of the label.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the created label as a dictionary and a dictionary with metadata.

        """
        response = self._create_label(
            owner=owner,
            repository=repository,
            name=name,
            color=color,
            description=description,
            **kwargs,
        )
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _edit_label(
        self,
        owner: str,
        repository: str,
        label_id: int,
        name: str | None = None,
        color: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> Response:
        """Edit a label.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            label_id: The ID of the label.
            name: The new name of the label.
            color: The new color of the label in hexadecimal format.
            description: The new description of the label.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._edit_label_helper(
            owner=owner,
            repository=repository,
            label_id=label_id,
            name=name,
            color=color,
            description=description,
        )
        return self._patch(endpoint=endpoint, json=payload, **kwargs)

    def edit_label(
        self,
        owner: str,
        repository: str,
        label_id: int,
        name: str | None = None,
        color: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Edit a label.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            label_id: The ID of the label.
            name: The new name of the label.
            color: The new color of the label in hexadecimal format.
            description: The new description of the label.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the updated label as a dictionary and a dictionary with metadata.

        """
        response = self._edit_label(
            owner=owner,
            repository=repository,
            label_id=label_id,
            name=name,
            color=color,
            description=description,
            **kwargs,
        )
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _delete_label(
        self,
        owner: str,
        repository: str,
        label_id: int,
        **kwargs: Any,
    ) -> Response:
        """Delete a label.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            label_id: The ID of the label.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._delete_label_helper(owner=owner, repository=repository, label_id=label_id)
        return self._delete(endpoint=endpoint, **kwargs)

    def delete_label(
        self,
        owner: str,
        repository: str,
        label_id: int,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Delete a label.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            label_id: The ID of the label.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing an empty dictionary and a dictionary with metadata.

        """
        response = self._delete_label(
            owner=owner,
            repository=repository,
            label_id=label_id,
            **kwargs,
        )
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}
