"""Unit tests for the AsyncLabel class."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gitea.label.async_label import AsyncLabel


class TestAsyncLabel:
    """Test cases for the AsyncLabel class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock AsyncGitea client."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value={"id": 1, "name": "bug", "color": "#e11d21"})
        mock_response.status = 200
        client._request = AsyncMock(return_value=mock_response)
        return client

    @pytest.fixture
    def async_label(self, mock_client):
        """Fixture to create an AsyncLabel instance."""
        return AsyncLabel(client=mock_client)

    @pytest.mark.asyncio
    async def test_list_labels(self, async_label, mock_client):
        """Test list_labels."""
        with patch("gitea.label.async_label.process_async_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "name": "bug"}], 200)
            result = await async_label.list_labels(owner="test_owner", repository="test_repo")
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/test_owner/test_repo/labels",
                params={},
            )
            assert result == ([{"id": 1, "name": "bug"}], {"status_code": 200})

    @pytest.mark.asyncio
    async def test_create_label(self, async_label, mock_client):
        """Test create_label."""
        with patch("gitea.label.async_label.process_async_response") as mock_process:
            mock_process.return_value = ({"id": 1, "name": "bug", "color": "#e11d21"}, 201)
            result = await async_label.create_label(
                owner="test_owner",
                repository="test_repo",
                name="bug",
                color="#e11d21",
            )
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/test_owner/test_repo/labels",
                json={"name": "bug", "color": "#e11d21"},
            )
            assert result == ({"id": 1, "name": "bug", "color": "#e11d21"}, {"status_code": 201})

    @pytest.mark.asyncio
    async def test_edit_label(self, async_label, mock_client):
        """Test edit_label."""
        with patch("gitea.label.async_label.process_async_response") as mock_process:
            mock_process.return_value = ({"id": 1, "name": "bug", "color": "#ffffff"}, 200)
            result = await async_label.edit_label(
                owner="test_owner", repository="test_repo", label_id=1, color="#ffffff"
            )
            mock_client._request.assert_called_once_with(
                method="PATCH",
                endpoint="/repos/test_owner/test_repo/labels/1",
                json={"color": "#ffffff"},
            )
            assert result == ({"id": 1, "name": "bug", "color": "#ffffff"}, {"status_code": 200})

    @pytest.mark.asyncio
    async def test_delete_label(self, async_label, mock_client):
        """Test delete_label."""
        with patch("gitea.label.async_label.process_async_response") as mock_process:
            mock_process.return_value = ({}, 204)
            result = await async_label.delete_label(owner="test_owner", repository="test_repo", label_id=1)
            mock_client._request.assert_called_once_with(
                method="DELETE",
                endpoint="/repos/test_owner/test_repo/labels/1",
            )
            assert result == ({}, {"status_code": 204})
