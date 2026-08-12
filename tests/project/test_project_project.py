"""Unit tests for the Project class."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gitea.project.async_project import AsyncProject
from gitea.project.project import Project


class TestProject:
    """Test cases for the Project class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock Gitea client."""
        return MagicMock()

    @pytest.fixture
    def project(self, mock_client):
        """Fixture to create a Project instance."""
        return Project(client=mock_client)

    def test_list_projects(self, project, mock_client):
        """Test list_projects."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "title": "Board"}], 200)
            result = project.list_projects(owner="o", repository="r", state="open")
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/o/r/projects",
                params={"state": "open"},
            )
            assert result == ([{"id": 1, "title": "Board"}], {"status_code": 200})

    def test_list_projects_org(self, project, mock_client):
        """Test list_projects for an organization (repository=None)."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ([{"id": 27, "title": "Org Board"}], 200)
            result = project.list_projects(owner="org", repository=None, state="open")
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/orgs/org/projects",
                params={"state": "open"},
            )
            assert result == ([{"id": 27, "title": "Org Board"}], {"status_code": 200})

    def test_get_project(self, project, mock_client):
        """Test get_project."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ({"id": 1, "title": "Board"}, 200)
            result = project.get_project(owner="o", repository="r", project_id=1)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/o/r/projects/1",
                params={},
            )
            assert result == ({"id": 1, "title": "Board"}, {"status_code": 200})

    def test_create_project(self, project, mock_client):
        """Test create_project."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ({"id": 1, "title": "New Board"}, 201)
            result = project.create_project(
                owner="o",
                repository="r",
                title="New Board",
                description="desc",
                template_type="basic_kanban",
                card_type="text_only",
            )
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/o/r/projects",
                json={
                    "title": "New Board",
                    "description": "desc",
                    "template_type": "basic_kanban",
                    "card_type": "text_only",
                },
            )
            assert result == ({"id": 1, "title": "New Board"}, {"status_code": 201})

    def test_edit_project(self, project, mock_client):
        """Test edit_project."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ({"id": 1, "title": "Renamed"}, 200)
            result = project.edit_project(owner="o", repository="r", project_id=1, title="Renamed", state="closed")
            mock_client._request.assert_called_once_with(
                method="PATCH",
                endpoint="/repos/o/r/projects/1",
                json={"title": "Renamed", "state": "closed"},
            )
            assert result == ({"id": 1, "title": "Renamed"}, {"status_code": 200})

    def test_delete_project(self, project, mock_client):
        """Test delete_project."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ({}, 204)
            result = project.delete_project(owner="o", repository="r", project_id=1)
            mock_client._request.assert_called_once_with(
                method="DELETE",
                endpoint="/repos/o/r/projects/1",
                params={},
            )
            assert result == ({}, {"status_code": 204})

    def test_list_project_columns(self, project, mock_client):
        """Test list_project_columns."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ([{"id": 5, "title": "Todo"}], 200)
            result = project.list_project_columns(owner="o", repository="r", project_id=1)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/o/r/projects/1/columns",
                params={},
            )
            assert result == ([{"id": 5, "title": "Todo"}], {"status_code": 200})

    def test_create_project_column(self, project, mock_client):
        """Test create_project_column."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ({"id": 5, "title": "Todo"}, 201)
            result = project.create_project_column(
                owner="o", repository="r", project_id=1, title="Todo", color="#FF0000"
            )
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/o/r/projects/1/columns",
                json={"title": "Todo", "color": "#FF0000"},
            )
            assert result == ({"id": 5, "title": "Todo"}, {"status_code": 201})

    def test_get_project_column(self, project, mock_client):
        """Test get_project_column."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ({"id": 5, "title": "Todo"}, 200)
            result = project.get_project_column(owner="o", repository="r", project_id=1, column_id=5)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/o/r/projects/1/columns/5",
                params={},
            )
            assert result == ({"id": 5, "title": "Todo"}, {"status_code": 200})

    def test_edit_project_column(self, project, mock_client):
        """Test edit_project_column."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ({"id": 5, "title": "In Progress"}, 200)
            result = project.edit_project_column(
                owner="o", repository="r", project_id=1, column_id=5, title="In Progress", sorting=2
            )
            mock_client._request.assert_called_once_with(
                method="PATCH",
                endpoint="/repos/o/r/projects/1/columns/5",
                json={"title": "In Progress", "sorting": 2},
            )
            assert result == ({"id": 5, "title": "In Progress"}, {"status_code": 200})

    def test_delete_project_column(self, project, mock_client):
        """Test delete_project_column."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ({}, 204)
            result = project.delete_project_column(owner="o", repository="r", project_id=1, column_id=5)
            mock_client._request.assert_called_once_with(
                method="DELETE",
                endpoint="/repos/o/r/projects/1/columns/5",
                params={},
            )
            assert result == ({}, {"status_code": 204})

    def test_set_default_project_column(self, project, mock_client):
        """Test set_default_project_column."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ({}, 204)
            result = project.set_default_project_column(owner="o", repository="r", project_id=1, column_id=5)
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/o/r/projects/1/columns/5/default",
                params={},
            )
            assert result == ({}, {"status_code": 204})

    def test_move_project_columns(self, project, mock_client):
        """Test move_project_columns."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ({}, 204)
            result = project.move_project_columns(owner="o", repository="r", project_id=1, column_ids=[5, 6])
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/o/r/projects/1/columns/move",
                json={"column_ids": [5, 6]},
            )
            assert result == ({}, {"status_code": 204})

    def test_list_project_column_issues(self, project, mock_client):
        """Test list_project_column_issues."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ([{"id": 100}], 200)
            result = project.list_project_column_issues(owner="o", repository="r", project_id=1, column_id=5)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/o/r/projects/1/columns/5/issues",
                params={},
            )
            assert result == ([{"id": 100}], {"status_code": 200})

    def test_add_issue_to_project_column(self, project, mock_client):
        """Test add_issue_to_project_column."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ({}, 201)
            result = project.add_issue_to_project_column(
                owner="o", repository="r", project_id=1, column_id=5, issue_id=100
            )
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/o/r/projects/1/columns/5/issues/100",
                params={},
            )
            assert result == ({}, {"status_code": 201})

    def test_remove_issue_from_project_column(self, project, mock_client):
        """Test remove_issue_from_project_column."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ({}, 204)
            result = project.remove_issue_from_project_column(
                owner="o", repository="r", project_id=1, column_id=5, issue_id=100
            )
            mock_client._request.assert_called_once_with(
                method="DELETE",
                endpoint="/repos/o/r/projects/1/columns/5/issues/100",
                params={},
            )
            assert result == ({}, {"status_code": 204})

    def test_move_project_issue(self, project, mock_client):
        """Test move_project_issue."""
        with patch("gitea.project.project.process_response") as mock_process:
            mock_process.return_value = ({}, 204)
            result = project.move_project_issue(
                owner="o", repository="r", project_id=1, issue_id=100, column_id=6, sorting=1
            )
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/o/r/projects/1/issues/100/move",
                json={"column_id": 6, "sorting": 1},
            )
            assert result == ({}, {"status_code": 204})


class TestAsyncProject:
    """Test cases for the AsyncProject class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture to create a mock AsyncGitea client."""
        client = MagicMock()
        client._request = AsyncMock(return_value=MagicMock())
        return client

    @pytest.fixture
    def project(self, mock_client):
        """Fixture to create an AsyncProject instance."""
        return AsyncProject(client=mock_client)

    @pytest.mark.asyncio
    async def test_list_projects(self, project, mock_client):
        """Test list_projects (async)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ([{"id": 1, "title": "Board"}], 200)
            result = await project.list_projects(owner="o", repository="r", state="open")
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/o/r/projects",
                params={"state": "open"},
            )
            assert result == ([{"id": 1, "title": "Board"}], {"status_code": 200})

    @pytest.mark.asyncio
    async def test_list_projects_org(self, project, mock_client):
        """Test list_projects for an organization (async, repository=None)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ([{"id": 27, "title": "Org Board"}], 200)
            result = await project.list_projects(owner="org", repository=None, state="open")
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/orgs/org/projects",
                params={"state": "open"},
            )
            assert result == ([{"id": 27, "title": "Org Board"}], {"status_code": 200})

    @pytest.mark.asyncio
    async def test_create_project(self, project, mock_client):
        """Test create_project (async)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ({"id": 1, "title": "Board"}, 201)
            result = await project.create_project(owner="o", repository="r", title="Board")
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/o/r/projects",
                json={"title": "Board"},
            )
            assert result == ({"id": 1, "title": "Board"}, {"status_code": 201})

    @pytest.mark.asyncio
    async def test_create_project_column(self, project, mock_client):
        """Test create_project_column (async)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ({"id": 5, "title": "Todo"}, 201)
            result = await project.create_project_column(owner="o", repository="r", project_id=1, title="Todo")
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/o/r/projects/1/columns",
                json={"title": "Todo"},
            )
            assert result == ({"id": 5, "title": "Todo"}, {"status_code": 201})

    @pytest.mark.asyncio
    async def test_add_issue_to_project_column(self, project, mock_client):
        """Test add_issue_to_project_column (async)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ({}, 201)
            result = await project.add_issue_to_project_column(
                owner="o", repository="r", project_id=1, column_id=5, issue_id=100
            )
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/o/r/projects/1/columns/5/issues/100",
                params={},
            )
            assert result == ({}, {"status_code": 201})

    @pytest.mark.asyncio
    async def test_move_project_issue(self, project, mock_client):
        """Test move_project_issue (async)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ({}, 204)
            result = await project.move_project_issue(
                owner="o", repository="r", project_id=1, issue_id=100, column_id=6
            )
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/o/r/projects/1/issues/100/move",
                json={"column_id": 6},
            )
            assert result == ({}, {"status_code": 204})

    @pytest.mark.asyncio
    async def test_get_project(self, project, mock_client):
        """Test get_project (async)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ({"id": 1, "title": "Board"}, 200)
            result = await project.get_project(owner="o", repository="r", project_id=1)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/o/r/projects/1",
                params={},
            )
            assert result == ({"id": 1, "title": "Board"}, {"status_code": 200})

    @pytest.mark.asyncio
    async def test_edit_project(self, project, mock_client):
        """Test edit_project (async)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ({"id": 1, "title": "Renamed"}, 200)
            result = await project.edit_project(
                owner="o", repository="r", project_id=1, title="Renamed", state="closed"
            )
            mock_client._request.assert_called_once_with(
                method="PATCH",
                endpoint="/repos/o/r/projects/1",
                json={"title": "Renamed", "state": "closed"},
            )
            assert result == ({"id": 1, "title": "Renamed"}, {"status_code": 200})

    @pytest.mark.asyncio
    async def test_delete_project(self, project, mock_client):
        """Test delete_project (async)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ({}, 204)
            result = await project.delete_project(owner="o", repository="r", project_id=1)
            mock_client._request.assert_called_once_with(
                method="DELETE",
                endpoint="/repos/o/r/projects/1",
                params={},
            )
            assert result == ({}, {"status_code": 204})

    @pytest.mark.asyncio
    async def test_list_project_columns(self, project, mock_client):
        """Test list_project_columns (async)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ([{"id": 5, "title": "Todo"}], 200)
            result = await project.list_project_columns(owner="o", repository="r", project_id=1)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/o/r/projects/1/columns",
                params={},
            )
            assert result == ([{"id": 5, "title": "Todo"}], {"status_code": 200})

    @pytest.mark.asyncio
    async def test_get_project_column(self, project, mock_client):
        """Test get_project_column (async)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ({"id": 5, "title": "Todo"}, 200)
            result = await project.get_project_column(owner="o", repository="r", project_id=1, column_id=5)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/o/r/projects/1/columns/5",
                params={},
            )
            assert result == ({"id": 5, "title": "Todo"}, {"status_code": 200})

    @pytest.mark.asyncio
    async def test_edit_project_column(self, project, mock_client):
        """Test edit_project_column (async)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ({"id": 5, "title": "In Progress"}, 200)
            result = await project.edit_project_column(
                owner="o", repository="r", project_id=1, column_id=5, title="In Progress", sorting=2
            )
            mock_client._request.assert_called_once_with(
                method="PATCH",
                endpoint="/repos/o/r/projects/1/columns/5",
                json={"title": "In Progress", "sorting": 2},
            )
            assert result == ({"id": 5, "title": "In Progress"}, {"status_code": 200})

    @pytest.mark.asyncio
    async def test_delete_project_column(self, project, mock_client):
        """Test delete_project_column (async)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ({}, 204)
            result = await project.delete_project_column(owner="o", repository="r", project_id=1, column_id=5)
            mock_client._request.assert_called_once_with(
                method="DELETE",
                endpoint="/repos/o/r/projects/1/columns/5",
                params={},
            )
            assert result == ({}, {"status_code": 204})

    @pytest.mark.asyncio
    async def test_set_default_project_column(self, project, mock_client):
        """Test set_default_project_column (async)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ({}, 204)
            result = await project.set_default_project_column(owner="o", repository="r", project_id=1, column_id=5)
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/o/r/projects/1/columns/5/default",
                params={},
            )
            assert result == ({}, {"status_code": 204})

    @pytest.mark.asyncio
    async def test_move_project_columns(self, project, mock_client):
        """Test move_project_columns (async)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ({}, 204)
            result = await project.move_project_columns(owner="o", repository="r", project_id=1, column_ids=[5, 6])
            mock_client._request.assert_called_once_with(
                method="POST",
                endpoint="/repos/o/r/projects/1/columns/move",
                json={"column_ids": [5, 6]},
            )
            assert result == ({}, {"status_code": 204})

    @pytest.mark.asyncio
    async def test_list_project_column_issues(self, project, mock_client):
        """Test list_project_column_issues (async)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ([{"id": 100}], 200)
            result = await project.list_project_column_issues(owner="o", repository="r", project_id=1, column_id=5)
            mock_client._request.assert_called_once_with(
                method="GET",
                endpoint="/repos/o/r/projects/1/columns/5/issues",
                params={},
            )
            assert result == ([{"id": 100}], {"status_code": 200})

    @pytest.mark.asyncio
    async def test_remove_issue_from_project_column(self, project, mock_client):
        """Test remove_issue_from_project_column (async)."""
        with patch("gitea.project.async_project.process_async_response") as mock_process:
            mock_process.return_value = ({}, 204)
            result = await project.remove_issue_from_project_column(
                owner="o", repository="r", project_id=1, column_id=5, issue_id=100
            )
            mock_client._request.assert_called_once_with(
                method="DELETE",
                endpoint="/repos/o/r/projects/1/columns/5/issues/100",
                params={},
            )
            assert result == ({}, {"status_code": 204})
