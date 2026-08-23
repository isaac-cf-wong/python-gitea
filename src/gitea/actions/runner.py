"""The Actions runners of a repository, an organization, an account or the instance.

A runner is the machine that executes jobs, and it is registered to one scope. It
then runs the jobs of everything under that scope, which is why the same runner
can be the reason a repository's workflows work and be absent from that
repository's own listing: the listing shows what is registered *there*, not what
could pick up its jobs. An empty repository listing is therefore not a repository
with nowhere to run.

Registering a runner is not something this API does. What it offers is the
registration token of a scope - `create_runner_registration_token` - which is
what `act_runner register` is then given; the runner itself joins over the Actions
protocol. So the lifecycle here is: take a token, register out of band, then list,
read, disable or remove what appeared.

This is the one family offered at all four scopes, the instance-wide one included.
"""

from __future__ import annotations

from typing import Any, cast

from requests import Response

from gitea.actions.base import BaseActions
from gitea.resource.resource import Resource
from gitea.utils.response import process_response


class Runners(BaseActions, Resource):
    """The Actions endpoints over the runners of a scope."""

    def _list_runners(
        self,
        owner: str | None = None,
        repository: str | None = None,
        admin: bool = False,
        disabled: bool | None = None,
        **kwargs: Any,
    ) -> Response:
        """List the runners of a scope.

        Args:
            owner: The owner of the repository, or the organization whose runners
                are listed.
            repository: The name of the repository, to list its runners alone.
            admin: Whether to list the runners of the whole instance.
            disabled: Whether to list the disabled runners rather than the
                enabled ones.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_runners_helper(owner=owner, repository=repository, admin=admin, disabled=disabled)
        return self._get(endpoint=endpoint, params=params, **kwargs)

    def list_runners(
        self,
        owner: str | None = None,
        repository: str | None = None,
        admin: bool = False,
        disabled: bool | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """List the runners of a scope.

        Args:
            owner: The owner of the repository, or the organization whose runners
                are listed. Omitting both this and `repository` lists the runners
                of the authenticated account.
            repository: The name of the repository, to list its runners alone.
            admin: Whether to list the runners of the whole instance, which
                answers only to an administrator's token.
            disabled: Whether to list the disabled runners rather than the enabled
                ones. Left unasked when it is None, which lists both.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the listing - an object carrying `total_count` and
            `runners`, as the endpoint answers with - and a dictionary with
            metadata. `status` on each entry is whether the runner is reachable,
            and `busy` whether it is running something; a runner can be online
            and disabled at once, and then takes no jobs.

        """
        response = self._list_runners(owner=owner, repository=repository, admin=admin, disabled=disabled, **kwargs)
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _get_runner(
        self,
        runner_id: int,
        owner: str | None = None,
        repository: str | None = None,
        admin: bool = False,
        **kwargs: Any,
    ) -> Response:
        """Get one runner of a scope.

        Args:
            runner_id: The ID of the runner.
            owner: The owner of the repository, or the organization the runner
                belongs to.
            repository: The name of the repository the runner belongs to.
            admin: Whether the runner is registered to the whole instance.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._runner_endpoint(runner_id=runner_id, owner=owner, repository=repository, admin=admin)
        return self._get(endpoint=endpoint, **kwargs)

    def get_runner(
        self,
        runner_id: int,
        owner: str | None = None,
        repository: str | None = None,
        admin: bool = False,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Get one runner of a scope.

        A runner is addressed through the scope it is registered to, so asking for
        a real runner through a scope it does not belong to answers `404`: the ID
        exists, the runner is simply not that scope's.

        Args:
            runner_id: The ID of the runner.
            owner: The owner of the repository, or the organization the runner
                belongs to. Omitting both this and `repository` reads a runner of
                the authenticated account.
            repository: The name of the repository the runner belongs to.
            admin: Whether the runner is registered to the whole instance.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the runner as a dictionary - its `labels` are what
            a job's `runs-on` is matched against - and a dictionary with metadata.

        """
        response = self._get_runner(runner_id=runner_id, owner=owner, repository=repository, admin=admin, **kwargs)
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _update_runner(
        self,
        runner_id: int,
        disabled: bool,
        owner: str | None = None,
        repository: str | None = None,
        admin: bool = False,
        **kwargs: Any,
    ) -> Response:
        """Update one runner of a scope.

        Args:
            runner_id: The ID of the runner.
            disabled: Whether the runner is to stop taking jobs.
            owner: The owner of the repository, or the organization the runner
                belongs to.
            repository: The name of the repository the runner belongs to.
            admin: Whether the runner is registered to the whole instance.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, payload = self._update_runner_helper(
            runner_id=runner_id, disabled=disabled, owner=owner, repository=repository, admin=admin
        )
        return self._patch(endpoint=endpoint, json=payload, **kwargs)

    def update_runner(
        self,
        runner_id: int,
        disabled: bool,
        owner: str | None = None,
        repository: str | None = None,
        admin: bool = False,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Disable or re-enable one runner of a scope.

        Disabling is the only field Gitea offers, and it is required rather than
        optional: there is no partial update to make of a runner, so an update
        always says which of the two states it means. Disabling is the reversible
        alternative to `delete_runner` - the runner stays registered and stops
        taking jobs, so it can be brought back without re-registering it.

        Args:
            runner_id: The ID of the runner.
            disabled: Whether the runner is to stop taking jobs.
            owner: The owner of the repository, or the organization the runner
                belongs to. Omitting both this and `repository` updates a runner
                of the authenticated account.
            repository: The name of the repository the runner belongs to.
            admin: Whether the runner is registered to the whole instance.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the runner as it now stands and a dictionary with
            metadata.

        """
        response = self._update_runner(
            runner_id=runner_id,
            disabled=disabled,
            owner=owner,
            repository=repository,
            admin=admin,
            **kwargs,
        )
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _delete_runner(
        self,
        runner_id: int,
        owner: str | None = None,
        repository: str | None = None,
        admin: bool = False,
        **kwargs: Any,
    ) -> Response:
        """Delete one runner of a scope.

        Args:
            runner_id: The ID of the runner.
            owner: The owner of the repository, or the organization the runner
                belongs to.
            repository: The name of the repository the runner belongs to.
            admin: Whether the runner is registered to the whole instance.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._runner_endpoint(runner_id=runner_id, owner=owner, repository=repository, admin=admin)
        return self._delete(endpoint=endpoint, **kwargs)

    def delete_runner(
        self,
        runner_id: int,
        owner: str | None = None,
        repository: str | None = None,
        admin: bool = False,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Remove one runner from a scope.

        The registration is what is removed. A runner process that is still
        running keeps trying to poll and is refused, so removing a runner is the
        server-side half of retiring one; `update_runner` is the reversible
        alternative when the machine is meant to come back.

        Args:
            runner_id: The ID of the runner.
            owner: The owner of the repository, or the organization the runner
                belongs to. Omitting both this and `repository` removes a runner
                of the authenticated account.
            repository: The name of the repository the runner belongs to.
            admin: Whether the runner is registered to the whole instance.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing an empty dictionary - the endpoint answers `204`
            with no body - and a dictionary with metadata.

        """
        response = self._delete_runner(runner_id=runner_id, owner=owner, repository=repository, admin=admin, **kwargs)
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    def _create_runner_registration_token(
        self,
        owner: str | None = None,
        repository: str | None = None,
        admin: bool = False,
        **kwargs: Any,
    ) -> Response:
        """Get the registration token of a scope.

        Args:
            owner: The owner of the repository, or the organization to register a
                runner to.
            repository: The name of the repository to register a runner to.
            admin: Whether to register a runner to the whole instance.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._runner_registration_token_endpoint(owner=owner, repository=repository, admin=admin)
        return self._post(endpoint=endpoint, **kwargs)

    def create_runner_registration_token(
        self,
        owner: str | None = None,
        repository: str | None = None,
        admin: bool = False,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Get the registration token a runner joins a scope with.

        The token belongs to the scope rather than to one runner: a token taken
        from an organization registers a runner to that organization, and every
        runner registered with it lands there. It is a credential - anything
        holding it can attach a machine that will then execute the scope's jobs -
        so it is worth treating like one.

        Args:
            owner: The owner of the repository, or the organization to register a
                runner to. Omitting both this and `repository` asks for the token
                of the authenticated account.
            repository: The name of the repository to register a runner to.
            admin: Whether to register a runner to the whole instance, which
                answers only to an administrator's token.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the token as a dictionary, under `token`, and a
            dictionary with metadata.

        """
        response = self._create_runner_registration_token(owner=owner, repository=repository, admin=admin, **kwargs)
        data, status_code = process_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}
