"""Unit tests for the Label class."""

from unittest.mock import MagicMock, patch

import pytest

from gitea.label.label import Label


class TestLabel:
    """Test cases for the Label class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock Gitea client."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "name": "bug", "color": "#e11d21"}
        mock_response.status_code = 200
        client._request.return_value = mock_response
        return client

    @pytest.fixture
    def label(self, mock_client):
        """Fixture to create a Label instance."""
        return Label(client=mock_client)

    def test_list_labels(self, label, mock_client):
        """Test list_labels."""
        with patch("gitea.label.label.process_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "name": "bug"}], 200)
            result = label.list_labels(owner="test_owner", repository="test_repo")
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/test_owner/test_repo/labels",
                params={},
            )
            assert result == ([{"id": 1, "name": "bug"}], {"status_code": 200})

    def test_create_label(self, label, mock_client):
        """Test create_label."""
        with patch("gitea.label.label.process_response") as mock_process:
            mock_process.return_value = ({"id": 1, "name": "bug", "color": "#e11d21"}, 201)
            result = label.create_label(
                owner="test_owner",
                repository="test_repo",
                name="bug",
                color="#e11d21",
                description="A bug",
            )
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/test_owner/test_repo/labels",
                json={"name": "bug", "color": "#e11d21", "description": "A bug"},
            )
            assert result == ({"id": 1, "name": "bug", "color": "#e11d21"}, {"status_code": 201})

    def test_edit_label(self, label, mock_client):
        """Test edit_label."""
        with patch("gitea.label.label.process_response") as mock_process:
            mock_process.return_value = ({"id": 1, "name": "bug", "color": "#e11d21"}, 200)
            result = label.edit_label(owner="test_owner", repository="test_repo", label_id=1, color="#ffffff")
            mock_client._request.assert_called_once_with(
                method="PATCH",
                endpoint="/repos/test_owner/test_repo/labels/1",
                json={"color": "#ffffff"},
            )
            assert result == ({"id": 1, "name": "bug", "color": "#e11d21"}, {"status_code": 200})

    def test_delete_label(self, label, mock_client):
        """Test delete_label."""
        with patch("gitea.label.label.process_response") as mock_process:
            mock_process.return_value = ({}, 204)
            result = label.delete_label(owner="test_owner", repository="test_repo", label_id=1)
            mock_client._request.assert_called_once_with(
                method="DELETE",
                endpoint="/repos/test_owner/test_repo/labels/1",
            )
            assert result == ({}, {"status_code": 204})
