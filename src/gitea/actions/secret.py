"""The Actions secrets of a repository, an organization or the authenticated account.

A secret is write-only. Setting one sends the value; nothing reads it back - the
listing carries the name, the description and when it was set, and that is all
Gitea will say. So there is no `get_secret` here, and the absence is the API's
rather than an omission.

Two things about the scopes are worth knowing. Setting and deleting work for a
repository, for an organization and for the authenticated account, but *listing*
does not: Gitea has no `GET /user/actions/secrets`, so a listing asked for
without an owner is refused here rather than answered `404` - which would read as
"no secrets" instead of "no such endpoint". And a job sees the secrets of every
scope above it, so a repository's listing is not the set of secrets its workflows
can read.
"""

from __future__ import annotations

from typing import Any, cast

from requests import Response

from gitea.actions.base import BaseActions
from gitea.resource.resource import Resource
from gitea.utils.response import process_response


class Secrets(BaseActions, Resource):
    """The Actions endpoints over the secrets of a scope."""

    def _list_secrets(
        self,
        owner: str | None = None,
        repository: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> Response:
        """List the secrets of a scope.

        Args:
            owner: The owner of the repository, or the organization whose secrets
                are listed.
            repository: The name of the repository, to list its secrets alone.
            page: The page number for pagination.
            limit: The number of secrets per page.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_secrets_helper(owner=owner, repository=repository, page=page, limit=limit)
        return self._get(endpoint=endpoint, params=params, **kwargs)

    def list_secrets(
        self,
        owner: str | None = None,
        repository: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """List the secrets of a scope.

        Args:
            owner: The owner of the repository, or the organization whose secrets
                are listed. Required: Gitea offers no listing for the
                authenticated account's own secrets.
            repository: The name of the repository, to list its secrets alone.
                Omitting it lists the organization's.
            page: The page number for pagination.
            limit: The number of secrets per page.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the secrets as a list and a dictionary with
            metadata. This listing is one of the two in the Actions API that
            answers with a bare array rather than with an object, so there is no
            `total_count` alongside it and no `secrets` key to read it out of.

        Raises:
            ValueError: If no owner was given, since the authenticated account's
                secrets cannot be listed.

        """
        response = self._list_secrets(owner=owner, repository=repository, page=page, limit=limit, **kwargs)
        data, status_code = process_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    def _create_or_update_secret(
        self,
        secret_name: str,
        data: str,
        owner: str | None = None,
        repository: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> Response:
        """Set a secret of a scope.

        Args:
            secret_name: The name of the secret.
            data: The value to store.
            owner: The owner of the repository, or the organization the secret
                belongs to.
            repository: The name of the repository the secret belongs to.
            description: What the secret is for.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._create_or_update_secret_helper(
            secret_name=secret_name,
            data=data,
            owner=owner,
            repository=repository,
            description=description,
        )
        return self._put(endpoint=endpoint, json=payload, **kwargs)

    def create_or_update_secret(
        self,
        secret_name: str,
        data: str,
        owner: str | None = None,
        repository: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Set a secret of a scope, creating it or replacing its value.

        One endpoint does both, which is why this is not split into a create and
        an update: Gitea answers `201` when the secret was new and `204` when it
        replaced one. Both are success, so a caller that only needs the secret to
        hold the value it passed does not have to look first, and one that needs to
        know which happened reads the status code out of the metadata.

        The entity is named first here, and the scope after it, because the scope
        is the optional part: `secret_name` and `data` are always needed, while
        `owner` and `repository` are what choose between a repository's secret, an
        organization's and the authenticated account's.

        Args:
            secret_name: The name of the secret.
            data: The value to store. Nothing reads it back.
            owner: The owner of the repository, or the organization the secret
                belongs to. Omitting both this and `repository` sets a secret of
                the authenticated account.
            repository: The name of the repository the secret belongs to.
            description: What the secret is for, shown alongside it in the web
                UI. Left out of the request when it was not given, so replacing a
                value does not clear the description the secret had.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing an empty dictionary - neither answer carries a
            body - and a dictionary with metadata.

        """
        response = self._create_or_update_secret(
            secret_name=secret_name,
            data=data,
            owner=owner,
            repository=repository,
            description=description,
            **kwargs,
        )
        parsed, status_code = process_response(response, default={})
        return cast(dict[str, Any], parsed), {"status_code": status_code}

    def _delete_secret(
        self,
        secret_name: str,
        owner: str | None = None,
        repository: str | None = None,
        **kwargs: Any,
    ) -> Response:
        """Delete a secret of a scope.

        Args:
            secret_name: The name of the secret.
            owner: The owner of the repository, or the organization the secret
                belongs to.
            repository: The name of the repository the secret belongs to.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._secret_endpoint(secret_name=secret_name, owner=owner, repository=repository)
        return self._delete(endpoint=endpoint, **kwargs)

    def delete_secret(
        self,
        secret_name: str,
        owner: str | None = None,
        repository: str | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Delete a secret of a scope.

        Args:
            secret_name: The name of the secret.
            owner: The owner of the repository, or the organization the secret
                belongs to. Omitting both this and `repository` deletes a secret
                of the authenticated account.
            repository: The name of the repository the secret belongs to.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing an empty dictionary - the endpoint answers `204`
            with no body - and a dictionary with metadata.

        """
        response = self._delete_secret(secret_name=secret_name, owner=owner, repository=repository, **kwargs)
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}
