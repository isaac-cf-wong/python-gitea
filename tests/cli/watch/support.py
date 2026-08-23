"""The stubbed instance the `watch` command tests are run against.

`watch list` and `watch advance` walk the same listings and read the same fields
out of them, so they are answered by one fake here rather than by one each. A
second copy would drift, and the two commands agreeing about what a scope holds
is exactly what these tests are for.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from gitea.cli.main import app

runner = CliRunner()

AUTH = ["--token", "tok", "--base-url", "https://gitea.invalid"]

ISSUE = {
    "id": 1854,
    "number": 15,
    "title": "Fix the docs",
    "updated_at": "2026-08-02T10:00:00Z",
    "assignees": [{"login": "alice"}],
    "labels": [{"name": "bug"}],
    "repository": {"owner": "my-org", "name": "my-repo"},
}

OTHER_ISSUE = {
    "id": 1900,
    "number": 16,
    "title": "Ship the release",
    "updated_at": "2026-08-02T11:00:00Z",
    "assignees": [],
    "labels": [],
    "repository": {"owner": "my-org", "name": "my-repo"},
}

COMMENT = {
    "id": 7,
    "body": "Looks right to me",
    "user": {"id": 3, "login": "alice"},
    "created_at": "2026-08-01T09:00:00Z",
    "updated_at": "2026-08-01T09:00:00Z",
}


def paged(*pages: list[dict[str, Any]]):
    """Build a side effect serving one page of a listing per requested page number.

    Args:
        *pages: The items of each page, in order.

    Returns:
        A side effect returning the requested page, or an empty page beyond the last one.

    """

    def _side_effect(**kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        page = kwargs.get("page", 1)
        return (list(pages[page - 1]) if page <= len(pages) else [], {"status_code": 200})

    return _side_effect


def paged_by(key: str, pages_by_value: dict[Any, list[list[dict[str, Any]]]]):
    """Build a side effect serving the pages recorded for one value of an argument.

    Args:
        key: The keyword argument selecting which listing is being paged.
        pages_by_value: Mapping of that argument's value to that listing's pages.

    Returns:
        A side effect returning the requested page, or an empty page beyond the last one.

    """

    def _side_effect(**kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        pages = pages_by_value.get(kwargs[key], [])
        page = kwargs.get("page", 1)
        return (list(pages[page - 1]) if page <= len(pages) else [], {"status_code": 200})

    return _side_effect


def make_client(
    issues: list[dict[str, Any]] | None = None,
    comments: dict[int, list[dict[str, Any]]] | None = None,
    columns: list[dict[str, Any]] | None = None,
    column_issues: dict[int, list[dict[str, Any]]] | None = None,
) -> MagicMock:
    """Build a client answering the listings a watch run walks.

    Args:
        issues: The open issues of every repository.
        comments: The comments of each issue, keyed by issue number.
        columns: The columns of every project.
        column_issues: The issues of each column, keyed by column ID.

    Returns:
        The client.

    """
    client = MagicMock()
    client.issue.list_issues.side_effect = paged(issues or [])
    client.comment.list_comments.side_effect = paged_by(
        "index", {number: [page] for number, page in (comments or {}).items()}
    )
    client.project.list_project_columns.side_effect = paged(columns or [])
    client.project.list_project_column_issues.side_effect = paged_by(
        "column_id", {column_id: [page] for column_id, page in (column_issues or {}).items()}
    )
    return client


def run(*arguments: str, client: MagicMock | None = None):
    """Invoke the CLI against a stubbed client.

    Args:
        *arguments: The arguments to invoke with.
        client: The client every command in this invocation talks to.

    Returns:
        The result of the invocation.

    """
    with patch("gitea.client.gitea.Gitea") as gitea:
        gitea.return_value.__enter__.return_value = client if client is not None else make_client()
        return runner.invoke(app, list(arguments))


def logged_error(logger: MagicMock) -> str:
    """Read the message of the single error a failed run logged.

    Asserting on the rendered stderr would make the assertion depend on the
    terminal, since `RichHandler` lays a record out as a table and appends the
    emitting frame to it; the record itself is what the CLI wrote.

    Args:
        logger: The patched logger of the module reporting the failure.

    Returns:
        The logged message with its arguments interpolated.

    """
    template, *arguments = logger.error.call_args.args
    return str(template) % tuple(arguments)
