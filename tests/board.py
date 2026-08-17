"""Helpers for describing a project board to the tests that resolve columns."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

ISSUE_ID = 1854

ORGANIZATION_PROJECT = {"id": 29, "title": "Board", "repo_id": 0, "type": "organization"}
REPOSITORY_PROJECT = {"id": 31, "title": "Repo board", "repo_id": 4, "type": "repository"}


def paged_columns(pages_by_project):
    """Build a side effect serving one page of columns per project and requested page.

    Args:
        pages_by_project: Mapping of project ID to that project's pages of columns.

    Returns:
        A side effect returning the requested page, or an empty page beyond the last one.

    """

    def _side_effect(**kwargs):
        pages = pages_by_project[kwargs["project_id"]]
        page = kwargs.get("page", 1)
        return (list(pages[page - 1]) if page <= len(pages) else [], {"status_code": 200})

    return _side_effect


def paged_issues(pages_by_column):
    """Build a side effect serving one page of issues per column and requested page.

    Args:
        pages_by_column: Mapping of column ID to that column's pages of issues.

    Returns:
        A side effect returning the requested page, or an empty page beyond the last one.

    """

    def _side_effect(**kwargs):
        pages = pages_by_column[kwargs["column_id"]]
        page = kwargs.get("page", 1)
        return (list(pages[page - 1]) if page <= len(pages) else [], {"status_code": 200})

    return _side_effect


def make_client(columns_by_project, issues_by_column):
    """Build a client whose board is described by the given columns and issues.

    Args:
        columns_by_project: Mapping of project ID to that project's pages of columns.
        issues_by_column: Mapping of column ID to that column's pages of issues.

    Returns:
        The mock client.

    """
    client = MagicMock()
    client.project.list_project_columns.side_effect = paged_columns(columns_by_project)
    client.project.list_project_column_issues.side_effect = paged_issues(issues_by_column)
    return client


def make_async_client(columns_by_project, issues_by_column):
    """Build an asynchronous client whose board is described by the given columns and issues.

    Args:
        columns_by_project: Mapping of project ID to that project's pages of columns.
        issues_by_column: Mapping of column ID to that column's pages of issues.

    Returns:
        The mock client.

    """
    client = MagicMock()
    client.project.list_project_columns = AsyncMock(side_effect=paged_columns(columns_by_project))
    client.project.list_project_column_issues = AsyncMock(side_effect=paged_issues(issues_by_column))
    return client


def make_issue(*projects):
    """Build an issue payload listing the given projects.

    Args:
        *projects: The projects the issue is on.

    Returns:
        The issue payload, shaped like the one the API returns.

    """
    return make_issue_with_projects([dict(p) for p in projects])


def make_issue_with_projects(projects):
    """Build an issue payload whose projects field holds the given entries verbatim.

    Args:
        projects: The entries of the issue's projects field, which need not be
            project objects.

    Returns:
        The issue payload, shaped like the one the API returns.

    """
    return {"id": ISSUE_ID, "number": 15, "title": "Board card", "projects": list(projects)}


def column_ids(issue):
    """Extract the resolved column of every project of an issue.

    Args:
        issue: The resolved issue payload.

    Returns:
        A list of the projects' column IDs, in order.

    """
    return [project["column_id"] for project in issue["projects"]]
