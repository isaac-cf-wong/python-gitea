"""The artifacts an Actions run produced: listing, reading, downloading, deleting.

An artifact is a file a job uploaded, and the reason this family reads differently
from the rest is that one of its endpoints answers with the file. `list_artifacts`
and `get_artifact` describe artifacts - the name, the size, when it expires;
`download_artifact` hands back the zip archive itself, as bytes.

Uploading is deliberately absent, and not an omission: Gitea has no REST endpoint
for it. An artifact is uploaded from inside a running job, by the runner, over the
Actions protocol rather than over this API, so there is nothing here to call. What
can be done from outside a run is what this module offers.

The asynchronous mirror of `gitea.actions.artifact`. The endpoints, the
arguments and the answers are that module's, and it is the one to read for what
each method does and why. The difference here is `aiohttp` in place of
`requests`, and the awaits that come with it.
"""

from __future__ import annotations

from typing import Any, cast

from aiohttp import ClientResponse

from gitea.actions.base import BaseActions
from gitea.resource.async_resource import AsyncResource
from gitea.utils.response import process_async_binary_response, process_async_response


class AsyncArtifacts(BaseActions, AsyncResource):
    """The Actions endpoints over a repository's artifacts."""

    async def _list_artifacts(
        self,
        owner: str,
        repository: str,
        run_id: int | None = None,
        name: str | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """List the artifacts of a repository, or of one of its runs.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run whose artifacts are listed.
            name: The name to list the artifacts of.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint, params = self._list_artifacts_helper(owner=owner, repository=repository, run_id=run_id, name=name)
        return await self._get(endpoint=endpoint, params=params, **kwargs)

    async def list_artifacts(
        self,
        owner: str,
        repository: str,
        run_id: int | None = None,
        name: str | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """List the artifacts of a repository, or of one of its runs.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            run_id: The ID of the run whose artifacts are listed. None lists
                every artifact of the repository, which - as with the run listing -
                is a different endpoint rather than the same one unfiltered.
            name: The name to list the artifacts of. A run that uploads one
                artifact per job has several artifacts of the same name, so this
                narrows the listing rather than identifying one artifact.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the listing - an object carrying `total_count` and
            `artifacts`, as the endpoint answers with - and a dictionary with
            metadata. Each entry carries `expired`, and an expired artifact is
            still listed: Gitea keeps the record after deleting the archive, so a
            caller about to download one reads that first.

        """
        response = await self._list_artifacts(owner=owner, repository=repository, run_id=run_id, name=name, **kwargs)
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _get_artifact(self, owner: str, repository: str, artifact_id: int, **kwargs: Any) -> ClientResponse:
        """Get one artifact of a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            artifact_id: The ID of the artifact.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._get_artifact_endpoint(owner=owner, repository=repository, artifact_id=artifact_id)
        return await self._get(endpoint=endpoint, **kwargs)

    async def get_artifact(
        self, owner: str, repository: str, artifact_id: int, **kwargs: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Get one artifact of a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            artifact_id: The ID of the artifact.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the artifact as a dictionary - its `size_in_bytes`
            is what a caller sizes a download by, and `expired` whether there is
            an archive left to download at all - and a dictionary with metadata.

        """
        response = await self._get_artifact(owner=owner, repository=repository, artifact_id=artifact_id, **kwargs)
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _download_artifact(self, owner: str, repository: str, artifact_id: int, **kwargs: Any) -> ClientResponse:
        """Download the archive of one artifact.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            artifact_id: The ID of the artifact.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._download_artifact_endpoint(owner=owner, repository=repository, artifact_id=artifact_id)
        return await self._get(endpoint=endpoint, **kwargs)

    async def download_artifact(
        self, owner: str, repository: str, artifact_id: int, **kwargs: Any
    ) -> tuple[bytes, dict[str, Any]]:
        """Download the archive of one artifact.

        The endpoint answers `302` and redirects to the blob; both HTTP clients
        follow that, so what arrives is the archive. It is handed back as bytes
        and not decoded: an artifact is a zip file, and decoding it as text -
        which is what the job log endpoint's answer gets - would replace every
        byte that is not valid UTF-8 and produce an archive that no longer opens.

        The whole archive is read into memory. An artifact is a build output
        rather than a dataset, so this is usually a few megabytes; a caller with
        a much larger one is better served by `get_artifact` and its
        `archive_download_url`.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            artifact_id: The ID of the artifact.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the zip archive and a dictionary with metadata. An
            artifact whose archive has expired answers with no body, so the empty
            bytes are an artifact that is gone rather than one that is empty -
            `expired` on the artifact itself is what says which.

        """
        response = await self._download_artifact(owner=owner, repository=repository, artifact_id=artifact_id, **kwargs)
        archive, status_code = await process_async_binary_response(response)
        return archive, {"status_code": status_code}

    async def _delete_artifact(self, owner: str, repository: str, artifact_id: int, **kwargs: Any) -> ClientResponse:
        """Delete one artifact of a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            artifact_id: The ID of the artifact.
            **kwargs: Additional arguments for the request.

        Returns:
            The HTTP response object.

        """
        endpoint = self._get_artifact_endpoint(owner=owner, repository=repository, artifact_id=artifact_id)
        return await self._delete(endpoint=endpoint, **kwargs)

    async def delete_artifact(
        self, owner: str, repository: str, artifact_id: int, **kwargs: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Delete one artifact of a repository.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            artifact_id: The ID of the artifact.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing an empty dictionary - the endpoint answers `204`
            with no body - and a dictionary with metadata.

        """
        response = await self._delete_artifact(owner=owner, repository=repository, artifact_id=artifact_id, **kwargs)
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}
