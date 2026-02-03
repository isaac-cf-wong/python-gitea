"""Asynchronous User Resource for Gitea API."""

from __future__ import annotations

from typing import Any, cast

from aiohttp import ClientResponse

from gitea.resource.async_resource import AsyncResource
from gitea.user.base import BaseUser
from gitea.utils.response import process_async_response


class AsyncUser(BaseUser, AsyncResource):
    """Asynchronous Gitea User resource."""

    async def _get_user(self, username: str | None = None, **kwargs: Any) -> ClientResponse:
        """Asynchronously get user information.

        Args:
            username: The username of the user to retrieve. If None, retrieves the authenticated user.
            **kwargs: Additional arguments for the request.

        Returns:
            The authenticated user's information as a ClientResponse object.

        """
        endpoint, kwargs = self._get_user_helper(username=username, **kwargs)
        return await self._get(endpoint=endpoint, **kwargs)

    async def get_user(self, username: str | None = None, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        """Asynchronously get user information.

        Args:
            username: The username of the user to retrieve. If None, retrieves the authenticated user.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the user information as a dictionary and a dictionary with the status code.

        """
        response = await self._get_user(username=username, **kwargs)
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}

    async def _update_user_settings(  # noqa: PLR0913
        self,
        diff_view_style: str | None = None,
        full_name: str | None = None,
        hide_activity: bool | None = None,
        hide_email: bool | None = None,
        language: str | None = None,
        location: str | None = None,
        theme: str | None = None,
        website: str | None = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """Asynchronously update user settings.

        Args:
            diff_view_style: The preferred diff view style.
            full_name: The full name of the user.
            hide_activity: Whether to hide user activity.
            hide_email: Whether to hide user email.
            language: The preferred language.
            location: The location of the user.
            theme: The preferred theme.
            website: The user's website.
            **kwargs: Additional arguments for the request.

        Returns:
            The response as a ClientResponse object.

        """
        endpoint, payload, kwargs = self._update_user_settings_helper(
            diff_view_style=diff_view_style,
            full_name=full_name,
            hide_activity=hide_activity,
            hide_email=hide_email,
            language=language,
            location=location,
            theme=theme,
            website=website,
            **kwargs,
        )
        return await self._patch(endpoint=endpoint, json=payload, **kwargs)

    async def update_user_settings(  # noqa: PLR0913
        self,
        diff_view_style: str | None = None,
        full_name: str | None = None,
        hide_activity: bool | None = None,
        hide_email: bool | None = None,
        language: str | None = None,
        location: str | None = None,
        theme: str | None = None,
        website: str | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Asynchronously update user settings.

        Args:
            diff_view_style: The preferred diff view style.
            full_name: The full name of the user.
            hide_activity: Whether to hide user activity.
            hide_email: Whether to hide user email.
            language: The preferred language.
            location: The location of the user.
            theme: The preferred theme.
            website: The user's website.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the updated user information as a dictionary and a dictionary with the status code.

        """
        response = await self._update_user_settings(
            diff_view_style=diff_view_style,
            full_name=full_name,
            hide_activity=hide_activity,
            hide_email=hide_email,
            language=language,
            location=location,
            theme=theme,
            website=website,
            **kwargs,
        )
        data, status_code = await process_async_response(response, default={})
        return cast(dict[str, Any], data), {"status_code": status_code}
