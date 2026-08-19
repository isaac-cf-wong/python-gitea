"""Unit tests for the BaseOrganization class."""

from gitea.organization.base import BaseOrganization


class TestBaseOrganization:
    """Test cases for the BaseOrganization base class."""

    def test_list_organizations_endpoint_authenticated(self):
        """Test _list_organizations_endpoint for the authenticated account."""
        base_organization = BaseOrganization()
        endpoint = base_organization._list_organizations_endpoint(username=None)
        assert endpoint == "/user/orgs"

    def test_list_organizations_endpoint_by_username(self):
        """Test _list_organizations_endpoint for a named account."""
        base_organization = BaseOrganization()
        endpoint = base_organization._list_organizations_endpoint(username="testuser")
        assert endpoint == "/users/testuser/orgs"

    def test_list_organizations_endpoint_defaults_to_the_authenticated_account(self):
        """Test _list_organizations_endpoint with no argument at all."""
        base_organization = BaseOrganization()
        assert base_organization._list_organizations_endpoint() == "/user/orgs"

    def test_list_organizations_helper_authenticated(self):
        """Test _list_organizations_helper for the authenticated account."""
        base_organization = BaseOrganization()
        endpoint, params = base_organization._list_organizations_helper(username=None)
        assert endpoint == "/user/orgs"
        assert params == {}

    def test_list_organizations_helper_by_username(self):
        """Test _list_organizations_helper for a named account."""
        base_organization = BaseOrganization()
        endpoint, params = base_organization._list_organizations_helper(username="testuser")
        assert endpoint == "/users/testuser/orgs"
        assert params == {}

    def test_list_organizations_helper_with_pagination(self):
        """Test _list_organizations_helper with both pagination parameters."""
        base_organization = BaseOrganization()
        endpoint, params = base_organization._list_organizations_helper(username=None, page=2, limit=50)
        assert endpoint == "/user/orgs"
        assert params == {"page": 2, "limit": 50}

    def test_list_organizations_helper_by_username_with_pagination(self):
        """Test _list_organizations_helper for a named account with pagination."""
        base_organization = BaseOrganization()
        endpoint, params = base_organization._list_organizations_helper(username="testuser", page=1, limit=20)
        assert endpoint == "/users/testuser/orgs"
        assert params == {"page": 1, "limit": 20}

    def test_list_organizations_helper_page_only(self):
        """Test _list_organizations_helper with only the page parameter."""
        base_organization = BaseOrganization()
        endpoint, params = base_organization._list_organizations_helper(username=None, page=5)
        assert endpoint == "/user/orgs"
        assert params == {"page": 5}

    def test_list_organizations_helper_limit_only(self):
        """Test _list_organizations_helper with only the limit parameter."""
        base_organization = BaseOrganization()
        endpoint, params = base_organization._list_organizations_helper(username=None, limit=75)
        assert endpoint == "/user/orgs"
        assert params == {"limit": 75}
