"""Unit tests for the Organization class."""

from unittest.mock import MagicMock, patch

import pytest

from gitea.organization.organization import Organization

ORGANIZATION = {"id": 23, "username": "my-org", "full_name": "My Org", "visibility": "limited"}


class TestOrganization:
    """Test cases for the Organization class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock Gitea client."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = [ORGANIZATION]
        mock_response.status_code = 200
        client._request.return_value = mock_response
        return client

    @pytest.fixture
    def organization(self, mock_client):
        """Fixture to create an Organization instance."""
        return Organization(client=mock_client)

    def test_list_organizations_authenticated(self, organization, mock_client):
        """Test list_organizations for the authenticated account."""
        with patch("gitea.organization.organization.process_response") as mock_process:
            mock_process.return_value = ([ORGANIZATION], 200)
            result = organization.list_organizations()
            mock_client._request.assert_called_once_with(method="GET", endpoint="/user/orgs", params={})
            assert result == ([ORGANIZATION], {"status_code": 200})

    def test_list_organizations_by_username(self, organization, mock_client):
        """Test list_organizations for a named account."""
        with patch("gitea.organization.organization.process_response") as mock_process:
            mock_process.return_value = ([ORGANIZATION], 200)
            result = organization.list_organizations(username="testuser")
            mock_client._request.assert_called_once_with(method="GET", endpoint="/users/testuser/orgs", params={})
            assert result == ([ORGANIZATION], {"status_code": 200})

    def test_list_organizations_with_pagination(self, organization, mock_client):
        """Test list_organizations with pagination parameters."""
        with patch("gitea.organization.organization.process_response") as mock_process:
            mock_process.return_value = ([ORGANIZATION], 200)
            result = organization.list_organizations(page=2, limit=50)
            mock_client._request.assert_called_once_with(
                method="GET", endpoint="/user/orgs", params={"page": 2, "limit": 50}
            )
            assert result == ([ORGANIZATION], {"status_code": 200})

    def test_list_organizations_by_username_with_pagination(self, organization, mock_client):
        """Test list_organizations for a named account with pagination."""
        with patch("gitea.organization.organization.process_response") as mock_process:
            mock_process.return_value = ([ORGANIZATION], 200)
            result = organization.list_organizations(username="testuser", page=3, limit=100)
            mock_client._request.assert_called_once_with(
                method="GET", endpoint="/users/testuser/orgs", params={"page": 3, "limit": 100}
            )
            assert result == ([ORGANIZATION], {"status_code": 200})

    def test_list_organizations_empty_result(self, organization, mock_client):
        """Test list_organizations with an empty result."""
        with patch("gitea.organization.organization.process_response") as mock_process:
            mock_process.return_value = ([], 200)
            result = organization.list_organizations()
            mock_client._request.assert_called_once()
            assert result == ([], {"status_code": 200})

    def test_list_organizations_error_response(self, organization, mock_client):
        """Test list_organizations with an error response."""
        with patch("gitea.organization.organization.process_response") as mock_process:
            mock_process.return_value = ({"error": "Not Found"}, 404)
            result = organization.list_organizations(username="nonexistent")
            mock_client._request.assert_called_once()
            assert result == ({"error": "Not Found"}, {"status_code": 404})

    def test_list_organizations_defaults_to_an_empty_listing(self, organization, mock_client):
        """A response without a body should be read as no organizations, not as None."""
        with patch("gitea.organization.organization.process_response") as mock_process:
            mock_process.return_value = ([], 200)
            organization.list_organizations()
            assert mock_process.call_args.kwargs["default"] == []

    def test_list_organizations_parses_the_response_it_fetched(self, organization, mock_client):
        """The response the request returned should be the one that is parsed.

        Asserting only on the endpoint leaves the handover between the request and
        the parsing untested: a method that fetched the right URL and then parsed
        something else - or nothing - answers a stubbed parser just as well.
        """
        with patch("gitea.organization.organization.process_response") as mock_process:
            mock_process.return_value = ([ORGANIZATION], 200)
            organization.list_organizations()
            assert mock_process.call_args.kwargs["response"] is mock_client._request.return_value

    def test_list_organizations_with_kwargs(self, organization, mock_client):
        """Test list_organizations passing additional kwargs to the _get method."""
        with patch("gitea.organization.organization.process_response") as mock_process:
            mock_process.return_value = ([ORGANIZATION], 200)
            result = organization.list_organizations(headers={"Custom": "Header"})
            mock_client._request.assert_called_once_with(
                method="GET", endpoint="/user/orgs", params={}, headers={"Custom": "Header"}
            )
            assert result == ([ORGANIZATION], {"status_code": 200})
