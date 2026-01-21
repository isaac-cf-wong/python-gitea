"""Unit tests for the BaseIssue class."""

from datetime import datetime

from gitea.issue.base import BaseIssue


class TestBaseIssue:
    """Test cases for the BaseIssue base class."""

    def test_list_issues_endpoint(self):
        """Test _list_issues_endpoint."""
        base_issue = BaseIssue()
        endpoint = base_issue._list_issues_endpoint(owner="test_owner", repository="test_repo")
        assert endpoint == "/repos/test_owner/test_repo/issues"

    def test_list_issues_helper_no_params(self):
        """Test _list_issues_helper with no parameters."""
        base_issue = BaseIssue()
        endpoint, params = base_issue._list_issues_helper(owner="test_owner", repository="test_repo")
        assert endpoint == "/repos/test_owner/test_repo/issues"
        assert params == {}

    def test_list_issues_helper_with_params(self):
        """Test _list_issues_helper with various parameters."""
        base_issue = BaseIssue()
        since = datetime(2023, 1, 1)
        before = datetime(2023, 12, 31)
        endpoint, params = base_issue._list_issues_helper(
            owner="test_owner",
            repository="test_repo",
            state="open",
            labels=["bug", "enhancement"],
            search_string="test query",
            issue_type="Issues",
            milestones=[1, 2],
            since=since,
            before=before,
            created_by="user1",
            assigned_by="user2",
            mentioned_by="user3",
            page=1,
            limit=10,
        )
        assert endpoint == "/repos/test_owner/test_repo/issues"
        expected_params = {
            "state": "open",
            "labels": "bug,enhancement",
            "q": "test query",
            "type": "Issues",
            "milestone": "1,2",
            "since": "2023-01-01T00:00:00",
            "before": "2023-12-31T00:00:00",
            "created_by": "user1",
            "assigned_by": "user2",
            "mentioned_by": "user3",
            "page": 1,
            "limit": 10,
        }
        assert params == expected_params

    def test_get_issue_endpoint(self):
        """Test _get_issue_endpoint."""
        base_issue = BaseIssue()
        endpoint = base_issue._get_issue_endpoint(owner="test_owner", repository="test_repo", index=123)
        assert endpoint == "/repos/test_owner/test_repo/issues/123"

    def test_get_issue_helper(self):
        """Test _get_issue_helper."""
        base_issue = BaseIssue()
        endpoint = base_issue._get_issue_helper(owner="test_owner", repository="test_repo", index=123)
        assert endpoint == "/repos/test_owner/test_repo/issues/123"

    def test_edit_issue_endpoint(self):
        """Test _edit_issue_endpoint."""
        base_issue = BaseIssue()
        endpoint = base_issue._edit_issue_endpoint(owner="test_owner", repository="test_repo", index=123)
        assert endpoint == "/repos/test_owner/test_repo/issues/123"

    def test_edit_issue_helper_no_params(self):
        """Test _edit_issue_helper with no parameters."""
        base_issue = BaseIssue()
        endpoint, payload = base_issue._edit_issue_helper(owner="test_owner", repository="test_repo", index=123)
        assert endpoint == "/repos/test_owner/test_repo/issues/123"
        assert payload == {}

    def test_edit_issue_helper_with_params(self):
        """Test _edit_issue_helper with various parameters."""
        base_issue = BaseIssue()
        due_date = datetime(2023, 6, 15)
        endpoint, payload = base_issue._edit_issue_helper(
            owner="test_owner",
            repository="test_repo",
            index=123,
            assignee="user1",
            assignees=["user1", "user2"],
            body="Updated body",
            due_date=due_date,
            milestone=5,
            ref="main",
            state="closed",
            title="Updated Title",
            unset_due_date=True,
        )
        assert endpoint == "/repos/test_owner/test_repo/issues/123"
        expected_payload = {
            "assignee": "user1",
            "assignees": ["user1", "user2"],
            "body": "Updated body",
            "due_date": "2023-06-15T00:00:00",
            "milestone": 5,
            "ref": "main",
            "state": "closed",
            "title": "Updated Title",
            "unset_due_date": True,
        }
        assert payload == expected_payload
