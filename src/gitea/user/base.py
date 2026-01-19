"""Base class for Gitea User resource."""

from __future__ import annotations

from typing import Any


class BaseUser:
    """Base class for Gitea User resource."""

    def _get_user_endpoint(self, username: str | None) -> str:
        """Determine the user endpoint based on username or account ID.

        Args:
            username: The username of the user.

        Returns:
            The API endpoint for the user.
        """
        return "/user" if username is None else f"/users/{username}"

    def _get_user_helper(self, username: str | None = None, **kwargs: Any) -> tuple[str, dict[str, Any]]:
        """Get user information.

        Args:
            username: The username of the user to retrieve. If None, retrieves the authenticated user.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the endpoint and the request arguments.
                - The API endpoint for the user.
                - A dictionary of request arguments.
        """
        endpoint = self._get_user_endpoint(username=username)
        default_headers = {
            "Content-Type": "application/json",
        }
        headers = kwargs.get("headers", {})
        headers = {**default_headers, **headers}
        kwargs["headers"] = headers

        return endpoint, kwargs

    def _update_user_settings_endpoint(self) -> str:
        """Get the endpoint for updating user settings.

        Returns:
            The API endpoint for updating user settings.
        """
        return "/user/settings"

    def _update_user_settings_helper(  # noqa: PLR0913
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
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        """Get the endpoint and request arguments for updating user settings.

        Args:
            diff_view_style: The preferred diff view style.
            full_name: The full name of the user.
            hide_activity: Whether to hide the user's activity.
            hide_email: Whether to hide the user's email.
            language: The preferred language.
            location: The location of the user.
            theme: The preferred theme.
            website: The user's website.
            **kwargs: Additional arguments for the request.

        Returns:
            A tuple containing the endpoint, payload, and request arguments.
                - The API endpoint for updating user settings.
                - A dictionary representing the payload for the request.
                - A dictionary of request arguments.
        """
        endpoint = self._update_user_settings_endpoint()
        default_headers = {
            "Content-Type": "application/json",
        }
        headers = kwargs.get("headers", {})
        headers = {**default_headers, **headers}
        kwargs["headers"] = headers

        payload = {}
        if diff_view_style is not None:
            payload["diff_view_style"] = diff_view_style
        if full_name is not None:
            payload["full_name"] = full_name
        if hide_activity is not None:
            payload["hide_activity"] = hide_activity
        if hide_email is not None:
            payload["hide_email"] = hide_email
        if language is not None:
            payload["language"] = language
        if location is not None:
            payload["location"] = location
        if theme is not None:
            payload["theme"] = theme
        if website is not None:
            payload["website"] = website

        return endpoint, payload, kwargs
