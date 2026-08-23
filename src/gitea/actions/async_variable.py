"""The Actions variables of a repository, an organization or the authenticated account.

A variable is the readable counterpart of a secret: the same three scopes, the
same paths with `variables` in place of `secrets`, and a value that comes back -
under `data` - when it is read.

Where a secret has one endpoint that both creates and replaces, a variable has
two, and they behave differently: `create_variable` answers `409` on a name that
already exists, while `update_variable` replaces the value of one that does. So
creating is safe to retry against a name believed to be free, and replacing is
asked for rather than arrived at.

The listing here is the other bare-array listing of the Actions API: a list, not
an object with `total_count`.

The asynchronous mirror of `gitea.actions.variable`. The endpoints, the
arguments and the answers are that module's, and it is the one to read for what
each method does and why. The difference here is `aiohttp` in place of
`requests`, and the awaits that come with it.
"""

from __future__ import annotations

from typing import Any, cast

from aiohttp import ClientResponse

from gitea.actions.base import BaseActions
from gitea.resource.async_resource import AsyncResource
from gitea.utils.response import process_async_response


class AsyncVariables(BaseActions, AsyncResource):
    """The Actions endpoints over the variables of a scope."""

    async def _list_variables(
        self,
        owner: str | None = None,
        repository: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """List the variables of a scope.

        Args:
            owner: The owner of the repository, or the organization whose
                variables are listed.
            repository: The name of the repository, to list its variables alone.
            page: The page number for pagination.
            limit: The number of variables per page.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_variables_helper(owner=owner, repository=repository, page=page, limit=limit)
        return await self._get(endpoint=endpoint, params=params, **kwargs)

    async def list_variables(
        self,
        owner: str | None = None,
        repository: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """List the variables of a scope.

        Args:
            owner: The owner of the repository, or the organization whose
                variables are listed. Omitting both this and `repository` lists
                the variables of the authenticated account.
            repository: The name of the repository, to list its variables alone.
            page: The page number for pagination.
            limit: The number of variables per page.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the variables as a list and a dictionary with
            metadata. Each entry carries the value under `data`, which is what
            makes a variable a variable rather than a secret.

        """
        response = await self._list_variables(owner=owner, repository=repository, page=page, limit=limit, **kwargs)
        data, status_code = await process_async_response(response, default=[])
        return cast(list[dict[str, Any]], data), {"status_code": status_code}

    async def _get_variable(
        self,
        variable_name: str,
        owner: str | None = None,
        repository: str | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """Get one variable of a scope.

        Args:
            variable_name: The name of the variable.
            owner: The owner of the repository, or the organization the variable
                belongs to.
            repository: The name of the repository the variable belongs to.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._variable_endpoint(variable_name=variable_name, owner=owner, repository=repository)
        return await self._get(endpoint=endpoint, **kwargs)

    async def get_variable(
        self,
        variable_name: str,
        owner: str | None = None,
        repository: str | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Get one variable of a scope.

        Args:
            variable_name: The name of the variable.
            owner: The owner of the repository, or the organization the variable
                belongs to. Omitting both this and `repository` reads a variable
                of the authenticated account.
            repository: The name of the repository the variable belongs to.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the variable as a dictionary, its value under
            `data`, and a dictionary with metadata.

        """
        response = await self._get_variable(variable_name=variable_name, owner=owner, repository=repository, **kwargs)
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _create_variable(
        self,
        variable_name: str,
        value: str,
        owner: str | None = None,
        repository: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """Create a variable of a scope.

        Args:
            variable_name: The name of the variable to create.
            value: The value to store.
            owner: The owner of the repository, or the organization the variable
                belongs to.
            repository: The name of the repository the variable belongs to.
            description: What the variable is for.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._create_variable_helper(
            variable_name=variable_name,
            value=value,
            owner=owner,
            repository=repository,
            description=description,
        )
        return await self._post(endpoint=endpoint, json=payload, **kwargs)

    async def create_variable(
        self,
        variable_name: str,
        value: str,
        owner: str | None = None,
        repository: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Create a variable of a scope.

        A name that already exists answers `409` rather than being replaced, so
        this never overwrites a value by accident; `update_variable` is how one is
        replaced on purpose.

        Args:
            variable_name: The name of the variable to create.
            value: The value to store.
            owner: The owner of the repository, or the organization the variable
                belongs to. Omitting both this and `repository` creates a variable
                of the authenticated account.
            repository: The name of the repository the variable belongs to.
            description: What the variable is for, shown alongside it in the web
                UI.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing an empty dictionary - the endpoint answers `201`
            with no body - and a dictionary with metadata.

        """
        response = await self._create_variable(
            variable_name=variable_name,
            value=value,
            owner=owner,
            repository=repository,
            description=description,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _update_variable(
        self,
        variable_name: str,
        value: str,
        owner: str | None = None,
        repository: str | None = None,
        new_name: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """Update a variable of a scope.

        Args:
            variable_name: The name of the variable to update.
            value: The value to store.
            owner: The owner of the repository, or the organization the variable
                belongs to.
            repository: The name of the repository the variable belongs to.
            new_name: A name to rename the variable to.
            description: What the variable is for.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._update_variable_helper(
            variable_name=variable_name,
            value=value,
            owner=owner,
            repository=repository,
            new_name=new_name,
            description=description,
        )
        return await self._put(endpoint=endpoint, json=payload, **kwargs)

    async def update_variable(
        self,
        variable_name: str,
        value: str,
        owner: str | None = None,
        repository: str | None = None,
        new_name: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Update a variable of a scope, replacing its value and optionally its name.

        Args:
            variable_name: The name of the variable to update, which is how the
                endpoint is addressed.
            value: The value to store. Gitea requires it, so an update meaning
                only to rename a variable still sends the value it is to keep -
                read it with `get_variable` first rather than guessing.
            owner: The owner of the repository, or the organization the variable
                belongs to. Omitting both this and `repository` updates a variable
                of the authenticated account.
            repository: The name of the repository the variable belongs to.
            new_name: A name to rename the variable to, sent as the API's `name`.
                Omitting it leaves the name alone.
            description: What the variable is for.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing an empty dictionary - the endpoint answers without
            a body - and a dictionary with metadata.

        """
        response = await self._update_variable(
            variable_name=variable_name,
            value=value,
            owner=owner,
            repository=repository,
            new_name=new_name,
            description=description,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _delete_variable(
        self,
        variable_name: str,
        owner: str | None = None,
        repository: str | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """Delete a variable of a scope.

        Args:
            variable_name: The name of the variable.
            owner: The owner of the repository, or the organization the variable
                belongs to.
            repository: The name of the repository the variable belongs to.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._variable_endpoint(variable_name=variable_name, owner=owner, repository=repository)
        return await self._delete(endpoint=endpoint, **kwargs)

    async def delete_variable(
        self,
        variable_name: str,
        owner: str | None = None,
        repository: str | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Delete a variable of a scope.

        Args:
            variable_name: The name of the variable.
            owner: The owner of the repository, or the organization the variable
                belongs to. Omitting both this and `repository` deletes a variable
                of the authenticated account.
            repository: The name of the repository the variable belongs to.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing an empty dictionary - the endpoint answers without
            a body - and a dictionary with metadata.

        """
        response = await self._delete_variable(
            variable_name=variable_name, owner=owner, repository=repository, **kwargs
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}
