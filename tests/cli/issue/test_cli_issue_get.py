"""Unit tests for the issue get command."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gitea.cli.issue.get import get_command
from tests.board import ISSUE_ID, ORGANIZATION_PROJECT, REPOSITORY_PROJECT, make_client, make_issue


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_get_command_calls_execute_and_delegates(mock_gitea, mock_get_auth_params, mock_execute):
    """get_command should lookup auth and pass an api_call that calls get_issue with correct params."""
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 10}, {"meta": 2})
    mock_gitea.return_value.__enter__.return_value = client

    get_command(ctx=ctx, owner="owner", repository="repo", issue_id=5, account_name="acct", token=None, base_url=None)

    mock_get_auth_params.assert_called_once_with(
        config_path="/tmp/config", account_name="acct", token=None, base_url=None
    )
    mock_execute.assert_called_once()

    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli issue get"

    result = call_kwargs["api_call"]()
    assert result == ({"id": 10}, {"meta": 2})
    client.issue.get_issue.assert_called_once_with(owner="owner", repository="repo", index=5)


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_get_command_emits_the_comment_count_as_the_api_names_it(mock_gitea, mock_get_auth_params, mock_execute):
    """get_command should pass the API's `comments` count through under its own name.

    This command used to rename the field to `comment_count`, alone among the
    commands that emit an issue. The rename is gone, so the count arrives under
    one name whichever command fetched the issue.
    """
    ctx = make_ctx()

    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 10, "comments": 3, "title": "Bug"}, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    get_command(ctx=ctx, owner="owner", repository="repo", issue_id=5, account_name="acct", token=None, base_url=None)

    data, metadata = mock_execute.call_args[1]["api_call"]()
    assert data == {"id": 10, "comments": 3, "title": "Bug"}
    assert "comment_count" not in data
    assert metadata == {"status_code": 200}


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_get_command_reports_the_column_of_every_project_the_issue_is_on(
    mock_gitea, mock_get_auth_params, mock_execute
):
    """Each project of the issue should carry the column its card sits in."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = make_client(
        {29: [[{"id": 107}, {"id": 109}]], 31: [[{"id": 5}, {"id": 6}]]},
        {107: [[{"id": 1857}]], 109: [[{"id": ISSUE_ID}]], 5: [[]], 6: [[{"id": ISSUE_ID}]]},
    )
    client.issue.get_issue.return_value = (
        make_issue(ORGANIZATION_PROJECT, REPOSITORY_PROJECT),
        {"status_code": 200},
    )
    mock_gitea.return_value.__enter__.return_value = client

    get_command(
        ctx=ctx,
        owner="example-org",
        repository="example-repo",
        issue_id=15,
        account_name="acct",
        token=None,
        base_url=None,
    )

    data, metadata = mock_execute.call_args[1]["api_call"]()

    assert [project["column_id"] for project in data["projects"]] == [109, 6]
    assert metadata == {"status_code": 200}


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_get_command_reports_a_null_column_for_a_project_without_a_card(mock_gitea, mock_get_auth_params, mock_execute):
    """A project the issue has no card on should be reported with a null column."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = make_client({29: [[{"id": 107}, {"id": 109}]]}, {107: [[{"id": 1857}]], 109: [[{"id": 1856}]]})
    client.issue.get_issue.return_value = (make_issue(ORGANIZATION_PROJECT), {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    get_command(
        ctx=ctx,
        owner="example-org",
        repository="example-repo",
        issue_id=15,
        account_name="acct",
        token=None,
        base_url=None,
    )

    data, _ = mock_execute.call_args[1]["api_call"]()

    assert [project["column_id"] for project in data["projects"]] == [None]


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_get_command_leaves_an_issue_without_projects_alone(mock_gitea, mock_get_auth_params, mock_execute):
    """An issue on no project should cost no board requests."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = make_client({}, {})
    client.issue.get_issue.return_value = ({"id": 10, "comments": 3, "projects": []}, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    get_command(
        ctx=ctx,
        owner="example-org",
        repository="example-repo",
        issue_id=15,
        account_name="acct",
        token=None,
        base_url=None,
    )

    data, _ = mock_execute.call_args[1]["api_call"]()

    assert data == {"id": 10, "comments": 3, "projects": []}
    client.project.list_project_columns.assert_not_called()


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_get_command_reports_a_column_on_every_project_of_an_issue_without_a_global_id(
    mock_gitea, mock_get_auth_params, mock_execute
):
    """Every project the command emits carries column_id, whatever the issue payload lacks.

    An instance that omits the global ID leaves nothing to match a card by, but
    the field must still be there: a consumer indexing `column_id` must never
    meet a KeyError because of what the issue happened to be missing.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = make_client({}, {})
    client.issue.get_issue.return_value = (
        {"number": 15, "projects": [dict(ORGANIZATION_PROJECT), dict(REPOSITORY_PROJECT)]},
        {"status_code": 200},
    )
    mock_gitea.return_value.__enter__.return_value = client

    get_command(
        ctx=ctx,
        owner="example-org",
        repository="example-repo",
        issue_id=15,
        account_name="acct",
        token=None,
        base_url=None,
    )

    data, _ = mock_execute.call_args[1]["api_call"]()

    assert [project["column_id"] for project in data["projects"]] == [None, None]
    client.project.list_project_columns.assert_not_called()
