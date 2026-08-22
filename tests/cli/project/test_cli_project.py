"""Unit tests for the project CLI commands."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from requests import ConnectionError as RequestsConnectionError
from requests import HTTPError, RequestException
from typer.testing import CliRunner

from gitea.cli.main import app
from gitea.cli.project.column.create import create_column_command
from gitea.cli.project.column.list import list_columns_command
from gitea.cli.project.create import create_command
from gitea.cli.project.delete import delete_command
from gitea.cli.project.edit import edit_command
from gitea.cli.project.get import get_command
from gitea.cli.project.issue.add import add_issue_command
from gitea.cli.project.issue.move import move_issue_command
from gitea.cli.project.issue.remove import remove_issue_command
from gitea.cli.project.list import list_command
from gitea.cli.utils.errors import CommandError
from tests.board import paged_columns
from tests.cli.rendering import unrendered
from tests.transport import NO_CONTENT, RecordedResponse, RoutedSession

runner = CliRunner()

# The three project issue commands, with the project call each one makes and
# the keyword arguments that call takes beyond the ones they all share.
ISSUE_COMMANDS = [
    pytest.param(add_issue_command, "add_issue_to_project_column", {"column_id": 5}, 201, id="add"),
    pytest.param(move_issue_command, "move_project_issue", {"column_id": 6, "sorting": None}, 204, id="move"),
    pytest.param(remove_issue_command, "remove_issue_from_project_column", {"column_id": 5}, 204, id="remove"),
]


def setattr_and_return(target, name, value):
    """Set an attribute mid-test and answer as the endpoint that set it does.

    For a client whose board stops being readable partway through a command: the
    move is answered normally and arranges for the read after it to fail, which
    a fixed side effect cannot express.

    Args:
        target: The mock to change.
        name: The attribute to set.
        value: The value to set it to.

    Returns:
        The empty payload and metadata a successful move answers with.

    """
    setattr(target, name, value)
    return {}, {"status_code": 204}


def make_ctx():
    """Create a mock context object."""
    return SimpleNamespace(obj={"config_path": "/tmp/config"})


# The column a card starts in, and the column the commands under test move it to.
# They are different so that a move within one column, which would pass whether
# or not it was made, is never what is asserted on.
CARDED_COLUMN = 5
TARGET_COLUMN = 6


class FakeBoard:
    """A project board whose cards a move really relocates - or really does not.

    `project issue move` now reads the target column back after moving, so a
    board that answers listings from a fixed table cannot serve it: the card has
    to be somewhere else after the move than before it, or the confirming read
    finds nothing and every successful move looks like a failure. This keeps the
    columns in a dictionary the mutations edit, so the two reads see the board
    before and after.

    `moves=False` is Gitea as this change exists because of: the move endpoint
    answers with a success and leaves the card where it was. A command that
    trusted the status code cannot tell that from a move.

    Removals are answered from the same table, and only ever take a card off the
    column the call names. A removal addressed to a column not holding the card
    is answered here with a success having removed nothing - which is the
    instance `project issue remove` reads the board back for, and not every
    instance: one tried by hand refused that call with a 404. The lenient answer
    is the one worth modelling, since it is the one a status code cannot be told
    apart from a removal that worked.
    """

    def __init__(self, cards, *, project_id=1, moves=True):
        """Lay out the board.

        Args:
            cards: Mapping of column ID to the global IDs of the cards in it.
                Every column a test moves to has to be one of them, empty or not,
                since a column absent from a board holds nothing.
            project_id: The project the columns belong to.
            moves: Whether a move relocates the card, or reports success and
                leaves the board alone as the endpoint under repair does.

        """
        self.cards = {column_id: list(issue_ids) for column_id, issue_ids in cards.items()}
        self.project_id = project_id
        self.moves = moves

    def attach(self, client):
        """Answer a mock client's board listings and card mutations from this board.

        Args:
            client: The mock client to attach to.

        Returns:
            This board, so a test can read it after the command ran.

        """
        client.project.list_project_columns.side_effect = paged_columns(
            {self.project_id: [[{"id": column_id} for column_id in self.cards]]}
        )
        client.project.list_project_column_issues.side_effect = lambda **kwargs: (
            [{"id": issue_id} for issue_id in self.cards.get(kwargs["column_id"], [])]
            if kwargs.get("page", 1) == 1
            else [],
            {"status_code": 200},
        )
        client.project.move_project_issue.side_effect = self._move
        client.project.add_issue_to_project_column.side_effect = self._add
        client.project.remove_issue_from_project_column.side_effect = self._remove
        return self

    def _move(self, **kwargs):
        """Relocate a card, as the move endpoint does when there is one to move.

        Args:
            **kwargs: The call's arguments, of which the issue and the target
                column are read.

        Returns:
            The empty payload and the metadata the endpoint answers with.

        """
        if self.moves:
            self._place(kwargs["issue_id"], kwargs["column_id"])
        return {}, {"status_code": 204}

    def _add(self, **kwargs):
        """Put a card in a column, as the add endpoint does.

        Args:
            **kwargs: The call's arguments, of which the issue and the column are
                read.

        Returns:
            The empty payload and the metadata the endpoint answers with.

        """
        self._place(kwargs["issue_id"], kwargs["column_id"])
        return {}, {"status_code": 201}

    def _remove(self, **kwargs):
        """Take a card off the column named, as the removal endpoint does.

        Only that column is touched, which is the whole point of it: the row
        relating the issue to the column it was given is what a removal removes,
        and a column that does not hold the card has no such row - so the card
        stays where it really is, and the call answers with a success rather than
        with the refusal an instance is also free to answer it with.

        Args:
            **kwargs: The call's arguments, of which the issue and the column are
                read.

        Returns:
            The empty payload and the metadata the endpoint answers with.

        """
        issue_ids = self.cards.get(kwargs["column_id"], [])
        if kwargs["issue_id"] in issue_ids:
            issue_ids.remove(kwargs["issue_id"])
        return {}, {"status_code": 204}

    def moving_removal(self, issue_id, column_id):
        """Build a removal side effect that moves the card just before answering.

        The race the confirming walk exists for, in the one place it can be
        expressed: the card leaves the column the board was walked for after the
        walk and before the removal, so the removal is addressed to a column that
        no longer holds it and answers with a success having removed nothing.

        Args:
            issue_id: The global ID of the issue whose card the edit moves.
            column_id: The column the card is moved to.

        Returns:
            The side effect to attach to the removal call.

        """

        def _side_effect(**kwargs):
            """Move the card, then answer the removal against the board as it now is.

            Args:
                **kwargs: The call's arguments, passed on to the removal.

            Returns:
                The empty payload and the metadata the endpoint answers with.

            """
            self._place(issue_id, column_id)
            return self._remove(**kwargs)

        return _side_effect

    def _place(self, issue_id, column_id):
        """Move a card to a column of the board, taking it off any other.

        Args:
            issue_id: The global ID of the issue whose card it is.
            column_id: The column the card belongs in afterwards.

        """
        for issue_ids in self.cards.values():
            if issue_id in issue_ids:
                issue_ids.remove(issue_id)
        self.cards.setdefault(column_id, []).append(issue_id)


class BoardSession(RoutedSession):
    """A routed session whose listings a `DELETE` really edits.

    `project issue remove` walks the board again after removing a card, so a
    session answering every listing from a fixed table reports the card as still
    on the board and turns a removal that worked into a failure. Here the
    column's listing loses the card its `DELETE` names, which is what the read
    after it has to see, and the `DELETE` is answered with the `204` and no body
    that the real endpoint answers with.
    """

    def __init__(self, cards_by_column, payload):
        """Lay out the board this session answers for.

        Args:
            cards_by_column: Mapping of column ID to the global IDs of the cards
                in it, in the order the columns are listed.
            payload: Body every request the board does not answer is given,
                which is the issue lookup.

        """
        self.listings = {
            column_id: [{"id": issue_id} for issue_id in issue_ids] for column_id, issue_ids in cards_by_column.items()
        }
        # The per-column listings first: the fragment of the columns listing is
        # part of every one of their URLs, and the first match answers.
        routes = [(f"/columns/{column_id}/issues", listing) for column_id, listing in self.listings.items()]
        routes.append(("/columns", [{"id": column_id} for column_id in self.listings]))
        super().__init__(routes, payload)

    def request(self, method, url, **kwargs):
        """Record a request, and let a `DELETE` take the card it names off the board.

        Args:
            method: HTTP method the client asked for.
            url: Full URL the client built.
            **kwargs: The headers, query parameters and JSON body, as recorded by
                the session this extends.

        Returns:
            The recorded response.

        """
        if method != "DELETE":
            return super().request(method, url, **kwargs)
        self._record(method, url, **kwargs)
        for column_id, listing in self.listings.items():
            prefix = f"/columns/{column_id}/issues/"
            if prefix in url:
                removed = url.rsplit("/", 1)[-1]
                listing[:] = [card for card in listing if str(card["id"]) != removed]
        return RecordedResponse(NO_CONTENT)


def board(client, cards, *, project_id=1, moves=True):
    """Attach a board with the given columns and cards to a mock client.

    Args:
        client: The mock client to attach the board to.
        cards: Mapping of column ID to the global IDs of the cards in it.
        project_id: The project the columns belong to.
        moves: Whether a move relocates the card on this board.

    Returns:
        The board, so a test can read it after the command ran.

    """
    return FakeBoard(cards, project_id=project_id, moves=moves).attach(client)


def carded(client, issue_id, *, project_id=1, moves=True):
    """Attach a board holding the issue's card in a column other than the target one.

    Args:
        client: The mock client to attach the board to.
        issue_id: The global ID of the issue whose card is on the board.
        project_id: The project holding the card.
        moves: Whether a move relocates the card on this board.

    Returns:
        The board, so a test can read it after the command ran.

    """
    return board(client, {CARDED_COLUMN: (issue_id,), TARGET_COLUMN: ()}, project_id=project_id, moves=moves)


def uncarded(client, *, project_id=1):
    """Attach a board with cards on it, none of them for the issue under test.

    Args:
        client: The mock client to attach the board to.
        project_id: The project the columns belong to.

    Returns:
        The board, so a test can read it after the command ran.

    """
    # `moves=False` because that is the truth of it: an issue with no card is an
    # issue the move endpoint has nothing to move, so it answers with a success
    # and leaves the board exactly as it was.
    return board(client, {CARDED_COLUMN: (1900,), TARGET_COLUMN: ()}, project_id=project_id, moves=False)


def make_http_error(status_code):
    """Create the error the client raises for an unsuccessful response.

    Args:
        status_code: The status code the response carries.

    Returns:
        The HTTP error.

    """
    response = MagicMock()
    response.status_code = status_code
    return HTTPError(f"{status_code} Client Error", response=response)


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_create_command(mock_gitea, mock_get_auth_params, mock_execute):
    """create_command should wire auth and call create_project."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.create_project.return_value = ({"id": 1, "title": "Board"}, {"status_code": 201})
    mock_gitea.return_value.__enter__.return_value = client

    create_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        title="Board",
        description="desc",
        template_type="basic_kanban",
        card_type="text_only",
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project create"

    result = call_kwargs["api_call"]()
    client.project.create_project.assert_called_once_with(
        owner="owner",
        repository="repo",
        title="Board",
        description="desc",
        template_type="basic_kanban",
        card_type="text_only",
    )
    assert result == ({"id": 1, "title": "Board"}, {"status_code": 201})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_command(mock_gitea, mock_get_auth_params, mock_execute):
    """list_command should wire auth and call list_projects."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.list_projects.return_value = ([{"id": 1}], {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        state="open",
        page=1,
        limit=10,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project list"

    result = call_kwargs["api_call"]()
    client.project.list_projects.assert_called_once_with(
        owner="owner", repository="repo", state="open", page=1, limit=10
    )
    assert result == ([{"id": 1}], {"status_code": 200})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_command_org(mock_gitea, mock_get_auth_params, mock_execute):
    """list_command should pass repository=None for organization projects."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.list_projects.return_value = ([{"id": 27}], {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_command(
        ctx=ctx,
        owner="org",
        repository=None,
        state=None,
        page=None,
        limit=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    result = mock_execute.call_args[1]["api_call"]()
    client.project.list_projects.assert_called_once_with(
        owner="org", repository=None, state=None, page=None, limit=None
    )
    assert result == ([{"id": 27}], {"status_code": 200})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_get_command(mock_gitea, mock_get_auth_params, mock_execute):
    """get_command should wire auth and call get_project."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.get_project.return_value = ({"id": 1}, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    get_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    result = call_kwargs["api_call"]()
    client.project.get_project.assert_called_once_with(owner="owner", repository="repo", project_id=1)
    assert result == ({"id": 1}, {"status_code": 200})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_edit_command(mock_gitea, mock_get_auth_params, mock_execute):
    """edit_command should wire auth and call edit_project."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.edit_project.return_value = ({"id": 1, "title": "Renamed"}, {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    edit_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        title="Renamed",
        description=None,
        card_type=None,
        state="closed",
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project edit"

    result = call_kwargs["api_call"]()
    client.project.edit_project.assert_called_once_with(
        owner="owner",
        repository="repo",
        project_id=1,
        title="Renamed",
        description=None,
        card_type=None,
        state="closed",
    )
    assert result == ({"id": 1, "title": "Renamed"}, {"status_code": 200})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_delete_command(mock_gitea, mock_get_auth_params, mock_execute):
    """delete_command should wire auth and call delete_project."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.delete_project.return_value = ({}, {"status_code": 204})
    mock_gitea.return_value.__enter__.return_value = client

    delete_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    result = call_kwargs["api_call"]()
    client.project.delete_project.assert_called_once_with(owner="owner", repository="repo", project_id=1)
    assert result == ({}, {"status_code": 204})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_create_column_command(mock_gitea, mock_get_auth_params, mock_execute):
    """create_column_command should wire auth and call create_project_column."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.create_project_column.return_value = ({"id": 5, "title": "Todo"}, {"status_code": 201})
    mock_gitea.return_value.__enter__.return_value = client

    create_column_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        title="Todo",
        color="#FF0000",
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project column create"

    result = call_kwargs["api_call"]()
    client.project.create_project_column.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, title="Todo", color="#FF0000"
    )
    assert result == ({"id": 5, "title": "Todo"}, {"status_code": 201})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_list_columns_command(mock_gitea, mock_get_auth_params, mock_execute):
    """list_columns_command should wire auth and call list_project_columns."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.list_project_columns.return_value = ([{"id": 5}], {"status_code": 200})
    mock_gitea.return_value.__enter__.return_value = client

    list_columns_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        page=None,
        limit=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project column list"

    result = call_kwargs["api_call"]()
    client.project.list_project_columns.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, page=None, limit=None
    )
    assert result == ([{"id": 5}], {"status_code": 200})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_add_issue_command(mock_gitea, mock_get_auth_params, mock_execute):
    """add_issue_command should wire auth and call add_issue_to_project_column."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    client.project.add_issue_to_project_column.return_value = ({}, {"status_code": 201})
    mock_gitea.return_value.__enter__.return_value = client

    add_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        column_id=5,
        issue_id=100,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project issue add"

    result = call_kwargs["api_call"]()
    client.issue.get_issue.assert_called_once_with(owner="owner", repository="repo", index=100)
    client.project.add_issue_to_project_column.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, column_id=5, issue_id=1854
    )
    assert result == ({}, {"status_code": 201, "resolved_issue_id": 1854})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command(mock_gitea, mock_get_auth_params, mock_execute):
    """move_issue_command should wire auth and call move_project_issue."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    carded(client, 1854)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=100,
        column_id=6,
        sorting=1,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project issue move"

    result = call_kwargs["api_call"]()
    client.issue.get_issue.assert_called_once_with(owner="owner", repository="repo", index=100)
    client.project.move_project_issue.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, issue_id=1854, column_id=6, sorting=1
    )
    assert result == ({}, {"status_code": 204, "resolved_issue_id": 1854})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_remove_issue_command(mock_gitea, mock_get_auth_params, mock_execute):
    """remove_issue_command should wire auth and call remove_issue_from_project_column."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    client.project.remove_issue_from_project_column.return_value = ({}, {"status_code": 204})
    mock_gitea.return_value.__enter__.return_value = client

    remove_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        column_id=5,
        issue_id=100,
        account_name="acct",
        token=None,
        base_url=None,
    )

    mock_execute.assert_called_once()
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["command_name"] == "gitea-cli project issue remove"

    result = call_kwargs["api_call"]()
    client.issue.get_issue.assert_called_once_with(owner="owner", repository="repo", index=100)
    client.project.remove_issue_from_project_column.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, column_id=5, issue_id=1854
    )
    assert result == ({}, {"status_code": 204, "resolved_issue_id": 1854})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_remove_issue_command_finds_the_column_holding_the_card(mock_gitea, mock_get_auth_params, mock_execute):
    """remove_issue_command should remove from the card's own column when none is given.

    The removal endpoint takes the column the card is in, which is not a column
    the caller is choosing but a fact about the board - so it is asked of the
    board rather than of the caller. The card is deliberately not in the first
    column of this one, and the column before it is not empty either, so a
    command reporting the first column, or the first column with any card in it,
    is not one this passes.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    # The board answers the removal, since the removal is read back against it:
    # a fixed answer would leave the card on the board and fail the confirmation.
    fake = board(client, {TARGET_COLUMN: (1900,), CARDED_COLUMN: (1854,)})
    mock_gitea.return_value.__enter__.return_value = client

    remove_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        column_id=None,
        issue_id=100,
        account_name="acct",
        token=None,
        base_url=None,
    )

    result = mock_execute.call_args[1]["api_call"]()
    client.project.remove_issue_from_project_column.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, column_id=CARDED_COLUMN, issue_id=1854
    )
    # The column the card came off is reported, since it was this command's
    # answer rather than the caller's: a removal that says nothing about where
    # the card was leaves the caller unable to put it back.
    assert result == (
        {},
        {"status_code": 204, "resolved_issue_id": 1854, "resolved_column_id": CARDED_COLUMN},
    )
    # Exiting normally is a claim about the board, so the board is what it is
    # checked against: no column of it holds a card for the issue afterwards, and
    # the card that was not this issue's is still there.
    assert fake.cards == {TARGET_COLUMN: [1900], CARDED_COLUMN: []}


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_remove_issue_command_reports_an_issue_with_no_card(mock_gitea, mock_get_auth_params, mock_execute):
    """remove_issue_command should refuse an issue the board has no card for, rather than guess a column."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    uncarded(client)
    client.project.remove_issue_from_project_column.return_value = ({}, {"status_code": 204})
    mock_gitea.return_value.__enter__.return_value = client

    remove_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        column_id=None,
        issue_id=100,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError) as error:
        mock_execute.call_args[1]["api_call"]()

    message = str(error.value)
    # The issue as the user addressed it, what was looked for, and why: an issue
    # with no card is not a removal that can be addressed to any column.
    assert "no card to remove" in message
    assert "#100 of owner/repo" in message
    assert "global ID 1854" in message
    assert "--column-id" in message
    client.project.remove_issue_from_project_column.assert_not_called()


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_remove_issue_command_keeps_the_column_it_was_given(mock_gitea, mock_get_auth_params, mock_execute):
    """A --column-id that was passed should be used as it stands, with no board read at all.

    The column is given here for a card that is somewhere else, which is a
    removal with nothing to remove - and whatever the instance answers it with is
    the caller's to see. Looking the card up and quietly removing it from the
    column it is really in would carry out something other than what was asked.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    carded(client, 1854)
    client.project.remove_issue_from_project_column.return_value = ({}, {"status_code": 204})
    mock_gitea.return_value.__enter__.return_value = client

    remove_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        column_id=TARGET_COLUMN,
        issue_id=100,
        account_name="acct",
        token=None,
        base_url=None,
    )

    result = mock_execute.call_args[1]["api_call"]()
    client.project.remove_issue_from_project_column.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, column_id=TARGET_COLUMN, issue_id=1854
    )
    client.project.list_project_columns.assert_not_called()
    client.project.list_project_column_issues.assert_not_called()
    # No resolved column comes back: the column was the caller's, and reporting
    # it as resolved would claim a lookup that was never made.
    assert result == ({}, {"status_code": 204, "resolved_issue_id": 1854})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_remove_issue_command_reports_a_card_moved_before_the_removal(mock_gitea, mock_get_auth_params, mock_execute):
    """A card moved between the column lookup and the removal should be reported, not called removed.

    The column a removal is addressed to is the one the board was walked for, and
    the walk and the removal are separate requests: a card moved in between
    leaves the removal naming a column that no longer holds it, which Gitea
    answers with a success having removed nothing - the lenient answer of the two
    an instance may give, and the one a caller cannot tell from a removal that
    worked. The card is still on the board, and only a walk of the whole board
    says so: the column the removal named is empty whether the removal took the
    card off it or the card had already left.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    fake = carded(client, 1854)
    # The board is edited between the walk that finds the card and the removal
    # addressed to what it found.
    client.project.remove_issue_from_project_column.side_effect = fake.moving_removal(1854, TARGET_COLUMN)
    mock_gitea.return_value.__enter__.return_value = client

    remove_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        column_id=None,
        issue_id=100,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError) as error:
        mock_execute.call_args[1]["api_call"]()

    message = str(error.value)
    # Which column was removed from, which one holds the card now, and that the
    # issue is still on the board - the thing a zero exit status would have
    # denied.
    assert f"from column {CARDED_COLUMN} of project 1 as a success" in message
    assert f"column {TARGET_COLUMN} of it holds a card" in message
    assert "still on the board" in message
    assert "#100 of owner/repo" in message
    assert "global ID 1854" in message
    # The removal really was made, and made against the column the walk found:
    # this is its answer being distrusted, not the call being skipped.
    client.project.remove_issue_from_project_column.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, column_id=CARDED_COLUMN, issue_id=1854
    )
    assert fake.cards[TARGET_COLUMN] == [1854]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        pytest.param(make_http_error(403), "Gitea returned HTTP 403", id="refused"),
        pytest.param(
            RequestsConnectionError("Failed to establish a new connection: [Errno 111] Connection refused"),
            "could not be reached",
            id="unreachable",
        ),
        pytest.param(RequestException("Invalid URL 'columns'"), "the request did not complete", id="incomplete"),
    ],
)
@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_remove_issue_command_reports_a_removal_it_could_not_confirm(
    mock_gitea, mock_get_auth_params, mock_execute, error, expected
):
    """A removal that could not be confirmed should be reported as unconfirmed, not as failed.

    The removal was made and answered; what the failed walk leaves unknown is
    whether it did anything, so reporting it as a failure would be as wrong as
    reporting it as a success.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.base_url = "https://gitea.example.com"
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    carded(client, 1854)
    # The board is readable up to the removal and unreadable after it.
    client.project.remove_issue_from_project_column.side_effect = lambda **kwargs: setattr_and_return(
        client.project.list_project_columns, "side_effect", error
    )
    mock_gitea.return_value.__enter__.return_value = client

    remove_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        column_id=None,
        issue_id=100,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError) as raised:
        mock_execute.call_args[1]["api_call"]()

    message = str(raised.value)
    assert expected in message
    assert "was made and reported success" in message
    assert "not known to be wrong" in message
    assert f"from column {CARDED_COLUMN} of project 1" in message
    assert "project issues" in message


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_remove_issue_command_reports_a_board_it_could_not_read(mock_gitea, mock_get_auth_params, mock_execute):
    """A board that could not be read should stop a removal that needed it to name a column.

    The lookup failing says nothing about whether the issue has a card, so
    neither reporting it as uncarded nor removing it from a column of guesswork
    is available: the failure is what is reported, and it says why the board was
    being read.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.base_url = "https://gitea.example.com"
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    client.project.list_project_columns.side_effect = make_http_error(403)
    client.project.remove_issue_from_project_column.return_value = ({}, {"status_code": 204})
    mock_gitea.return_value.__enter__.return_value = client

    remove_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        column_id=None,
        issue_id=100,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError) as error:
        mock_execute.call_args[1]["api_call"]()

    message = str(error.value)
    assert "Could not tell which column of project 1 holds" in message
    assert "HTTP 403" in message
    # Why the board was read at all, which is not the reason the move reads it.
    assert "--column-id was not passed" in message
    assert "no card to move" not in message
    client.project.remove_issue_from_project_column.assert_not_called()


@patch("gitea.client.gitea.requests.Session")
def test_remove_issue_deletes_the_card_of_the_column_holding_it(mock_session):
    """The CLI should accept a removal naming no column and delete the card from the column holding it.

    The assertions above are made against a client, which is reached with
    `--column-id` already resolved to None by the caller; this one goes through
    the command line, so what is pinned is that the option really is optional
    there and that the request built for it addresses the card's own column.
    """
    session = BoardSession(
        # The card of another issue is in the column listed first.
        {TARGET_COLUMN: (1900,), CARDED_COLUMN: (1854,)},
        # What the issue lookup is answered with: the global ID of `#100`.
        payload={"id": 1854, "number": 100},
    )
    mock_session.return_value = session

    result = runner.invoke(
        app,
        [
            "project",
            "issue",
            "remove",
            "--owner",
            "owner",
            "--repository",
            "repo",
            "--project-id",
            "1",
            "--issue-id",
            "100",
            "--token",
            "tok",
            "--base-url",
            "https://gitea.invalid",
        ],
    )

    assert result.exit_code == 0, result.stdout
    deleted = [url for method, url in session.requests if method == "DELETE"]
    assert deleted == [f"https://gitea.invalid/api/v1/repos/owner/repo/projects/1/columns/{CARDED_COLUMN}/issues/1854"]
    # And the board is walked again afterwards, which is what the zero exit
    # status rests on: the columns and their cards are read after the DELETE, not
    # only before it.
    methods = [method for method, _ in session.requests]
    after = session.requests[methods.index("DELETE") + 1 :]
    assert [url for method, url in after if method == "GET"] != []
    assert all("/columns" in url for _, url in after)


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_org(mock_gitea, mock_get_auth_params, mock_execute):
    """move_issue_command should pass --issue-id through unresolved for organization projects."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    carded(client, 1854)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="org",
        repository=None,
        project_id=1,
        issue_id=1854,
        column_id=6,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    result = mock_execute.call_args[1]["api_call"]()
    client.issue.get_issue.assert_not_called()
    client.project.move_project_issue.assert_called_once_with(
        owner="org", repository=None, project_id=1, issue_id=1854, column_id=6, sorting=None
    )
    assert result == ({}, {"status_code": 204})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_add_issue_command_org(mock_gitea, mock_get_auth_params, mock_execute):
    """add_issue_command should pass --issue-id through unresolved for organization projects."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.add_issue_to_project_column.return_value = ({}, {"status_code": 201})
    mock_gitea.return_value.__enter__.return_value = client

    add_issue_command(
        ctx=ctx,
        owner="org",
        repository=None,
        project_id=1,
        column_id=5,
        issue_id=1854,
        account_name="acct",
        token=None,
        base_url=None,
    )

    result = mock_execute.call_args[1]["api_call"]()
    client.issue.get_issue.assert_not_called()
    client.project.add_issue_to_project_column.assert_called_once_with(
        owner="org", repository=None, project_id=1, column_id=5, issue_id=1854
    )
    assert result == ({}, {"status_code": 201})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_unknown_issue_number(mock_gitea, mock_get_auth_params, mock_execute):
    """move_issue_command should fail loudly when the issue number does not exist."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.side_effect = make_http_error(404)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=9999,
        column_id=6,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError, match="owner/repo"):
        mock_execute.call_args[1]["api_call"]()
    client.project.move_project_issue.assert_not_called()


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_api_failure(mock_gitea, mock_get_auth_params, mock_execute):
    """move_issue_command should surface a failing API status instead of an empty envelope."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 15}, {"status_code": 200})
    carded(client, 1854)
    # After the board, whose own answer to a move this replaces.
    client.project.move_project_issue.side_effect = make_http_error(404)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=15,
        column_id=6,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError, match="HTTP 404"):
        mock_execute.call_args[1]["api_call"]()


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_remove_issue_command_api_failure(mock_gitea, mock_get_auth_params, mock_execute):
    """remove_issue_command should surface a failing API status instead of an empty envelope."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.project.remove_issue_from_project_column.side_effect = make_http_error(403)
    mock_gitea.return_value.__enter__.return_value = client

    remove_issue_command(
        ctx=ctx,
        owner="org",
        repository=None,
        project_id=1,
        column_id=5,
        issue_id=1854,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError, match="HTTP 403"):
        mock_execute.call_args[1]["api_call"]()


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_add_issue_command_api_failure(mock_gitea, mock_get_auth_params, mock_execute):
    """add_issue_command should surface a failing API status instead of an empty envelope."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 15}, {"status_code": 200})
    client.project.add_issue_to_project_column.side_effect = make_http_error(404)
    mock_gitea.return_value.__enter__.return_value = client

    add_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        column_id=5,
        issue_id=15,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError, match="HTTP 404"):
        mock_execute.call_args[1]["api_call"]()


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_org_with_issue_repository(mock_gitea, mock_get_auth_params, mock_execute):
    """move_issue_command should resolve the number against --issue-repository on an organization project."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1877, "number": 38}, {"status_code": 200})
    carded(client, 1877)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="org",
        repository=None,
        issue_repository="repo",
        project_id=1,
        issue_id=38,
        column_id=6,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    result = mock_execute.call_args[1]["api_call"]()
    client.issue.get_issue.assert_called_once_with(owner="org", repository="repo", index=38)
    client.project.move_project_issue.assert_called_once_with(
        owner="org", repository=None, project_id=1, issue_id=1877, column_id=6, sorting=None
    )
    assert result == ({}, {"status_code": 204, "resolved_issue_id": 1877})


@pytest.mark.parametrize(("command", "method", "call_kwargs", "status_code"), ISSUE_COMMANDS)
@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_issue_command_issue_repository_overrides_repository(
    mock_gitea, mock_get_auth_params, mock_execute, command, method, call_kwargs, status_code
):
    """Each issue command should resolve against --issue-repository when it differs from --repository."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1877, "number": 38}, {"status_code": 200})
    # `remove` is answered here; `add` and `move` are answered by the board,
    # which reports the same status codes the table declares for them.
    getattr(client.project, method).return_value = ({}, {"status_code": status_code})
    carded(client, 1877)
    mock_gitea.return_value.__enter__.return_value = client

    command(
        ctx=ctx,
        owner="owner",
        repository="board-repo",
        issue_repository="other-repo",
        project_id=1,
        issue_id=38,
        account_name="acct",
        token=None,
        base_url=None,
        **call_kwargs,
    )

    result = mock_execute.call_args[1]["api_call"]()
    # The number is looked up in the repository holding the issue, while the
    # project call keeps the repository holding the board.
    client.issue.get_issue.assert_called_once_with(owner="owner", repository="other-repo", index=38)
    getattr(client.project, method).assert_called_once_with(
        owner="owner", repository="board-repo", project_id=1, issue_id=1877, **call_kwargs
    )
    assert result == ({}, {"status_code": status_code, "resolved_issue_id": 1877})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_org_failure_suggests_issue_repository(mock_gitea, mock_get_auth_params, mock_execute):
    """move_issue_command should point at --issue-repository when a global ID is refused."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    carded(client, 38)
    client.project.move_project_issue.side_effect = make_http_error(404)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="org",
        repository=None,
        project_id=1,
        issue_id=38,
        column_id=6,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError, match="--issue-repository REPOSITORY"):
        mock_execute.call_args[1]["api_call"]()
    client.issue.get_issue.assert_not_called()


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        pytest.param(make_http_error(404), ("The issue was found in", "owner/repo"), id="refused"),
        pytest.param(
            RequestsConnectionError("Failed to establish a new connection: [Errno 111] Connection refused"),
            ("Could not reach the Gitea API", "https://gitea.example.com"),
            id="unreachable",
        ),
    ],
)
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_reports_failures_without_a_traceback(
    mock_gitea, mock_get_auth_params, monkeypatch, tmp_path, error, expected
):
    """The command should exit 1 with the message alone, through the real logging handler."""
    # Keep the message on one line so the layout stays the simple one, whichever
    # width the terminal running the tests reports.
    monkeypatch.setenv("COLUMNS", "300")
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.base_url = "https://gitea.example.com"
    client.issue.get_issue.return_value = ({"id": 1877, "number": 38}, {"status_code": 200})
    carded(client, 1877)
    client.project.move_project_issue.side_effect = error
    mock_gitea.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        [
            # Point at a path of its own so a regression cannot read the
            # developer's own configuration instead.
            "--config-path",
            str(tmp_path / "config.yaml"),
            "project",
            "issue",
            "move",
            "--owner",
            "owner",
            "--repository",
            "repo",
            "--project-id",
            "1",
            "--issue-id",
            "38",
            "--column-id",
            "6",
        ],
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    # `RichHandler` renders the record for whatever terminal it believes it is
    # writing to: it styles the URL inside the message, pads the message column
    # and appends the emitting frame. Assert on the wording each part of the
    # message contributes, over the unstyled text, so none of those decisions
    # can turn a correct message into a failure.
    message = unrendered(result.stderr)
    for fragment in expected:
        assert unrendered(fragment) in message
    # The message is the whole error: no traceback, and none of the wording the
    # unhandled-exception path would add.
    assert "Traceback" not in result.stderr
    assert unrendered("Error executing") not in message


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_reports_an_issue_with_no_card(mock_gitea, mock_get_auth_params, mock_execute):
    """move_issue_command should refuse to move an issue that has no card on the project.

    Gitea's move endpoint moves the row relating the issue to the project, and
    an issue that is not on the project has none: the call comes back `200` with
    an empty body having moved nothing, so a caller reading the status believes a
    card is on a board that has none. The move is therefore not attempted at all.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    # The board has cards on it, none of them this issue's, and it answers a move
    # the way Gitea does: a success that moves nothing. So a command that went
    # ahead and moved anyway would be seen to have reported success for nothing,
    # rather than merely meeting an unstubbed call.
    uncarded(client)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=100,
        column_id=6,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError) as error:
        mock_execute.call_args[1]["api_call"]()

    message = str(error.value)
    # The issue as the user addressed it, and the two ways out: the command that
    # puts an issue on a board, and the option that has this one do it.
    assert "#100 of owner/repo" in message
    assert "global ID 1854" in message
    assert "project issue add" in message
    assert "--add-if-missing" in message
    client.project.move_project_issue.assert_not_called()
    client.project.add_issue_to_project_column.assert_not_called()


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_adds_the_issue_when_it_has_no_card(mock_gitea, mock_get_auth_params, mock_execute):
    """--add-if-missing should put an uncarded issue in the target column instead of failing."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    uncarded(client)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=100,
        column_id=6,
        sorting=None,
        add_if_missing=True,
        account_name="acct",
        token=None,
        base_url=None,
    )

    result = mock_execute.call_args[1]["api_call"]()
    # The column the move was to, which is where the card has to end up: adding
    # it to the column it came from would be the no-op under another name.
    client.project.add_issue_to_project_column.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, column_id=6, issue_id=1854
    )
    client.project.move_project_issue.assert_not_called()
    assert result == ({}, {"status_code": 201, "resolved_issue_id": 1854})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_moves_a_carded_issue_with_add_if_missing(mock_gitea, mock_get_auth_params, mock_execute):
    """--add-if-missing should not change what happens to an issue that does have a card."""
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    carded(client, 1854)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=100,
        column_id=6,
        sorting=2,
        add_if_missing=True,
        account_name="acct",
        token=None,
        base_url=None,
    )

    result = mock_execute.call_args[1]["api_call"]()
    client.project.move_project_issue.assert_called_once_with(
        owner="owner", repository="repo", project_id=1, issue_id=1854, column_id=6, sorting=2
    )
    client.project.add_issue_to_project_column.assert_not_called()
    assert result == ({}, {"status_code": 204, "resolved_issue_id": 1854})


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_refuses_a_sorting_the_add_cannot_carry(mock_gitea, mock_get_auth_params, mock_execute):
    """--sorting should be refused rather than dropped when there is no card and one is added.

    `--sorting` positions a card among the cards already in a column, and the
    endpoint that puts a card on a board takes no position. Accepting the option
    and adding the card anyway would report a request carried out that was not.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    uncarded(client)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=100,
        column_id=6,
        sorting=3,
        add_if_missing=True,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError, match="--sorting"):
        mock_execute.call_args[1]["api_call"]()
    client.project.add_issue_to_project_column.assert_not_called()
    client.project.move_project_issue.assert_not_called()


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        pytest.param(make_http_error(403), "Gitea returned HTTP 403", id="refused"),
        pytest.param(
            RequestsConnectionError("Failed to establish a new connection: [Errno 111] Connection refused"),
            "Could not reach the Gitea API",
            id="unreachable",
        ),
        pytest.param(
            RequestException("Invalid URL 'columns': No scheme supplied"),
            "Could not complete the request to the Gitea API",
            id="incomplete",
        ),
    ],
)
@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_reports_a_board_it_could_not_read(
    mock_gitea, mock_get_auth_params, mock_execute, error, expected
):
    """A board that could not be read should be reported as such, and stop the move.

    The two answers have to stay apart: a lookup that failed says nothing about
    whether the issue has a card, so reporting it as uncarded would be a claim
    the failure does not support, and moving anyway would be the silent no-op the
    lookup is there to prevent.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.base_url = "https://gitea.example.com"
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    client.project.move_project_issue.return_value = ({}, {"status_code": 200})
    client.project.list_project_columns.side_effect = error
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=100,
        column_id=6,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError) as raised:
        mock_execute.call_args[1]["api_call"]()

    message = str(raised.value)
    assert expected in message
    assert "project issue add" not in message
    client.project.move_project_issue.assert_not_called()
    client.project.add_issue_to_project_column.assert_not_called()


@patch("gitea.client.gitea.requests.Session")
def test_move_issue_sends_no_move_request_for_an_issue_with_no_card(mock_session):
    """No request should reach the move endpoint for an issue the board has no card for.

    The assertions above are made against a client; this one is made against the
    session the real client builds its requests on, so what is pinned is that the
    request Gitea would have answered with a success and a no-op is never sent.
    """
    session = RoutedSession(
        routes=(
            # A column of the board, holding a card - for another issue.
            (f"/columns/{CARDED_COLUMN}/issues", [{"id": 1900}]),
            ("/columns", [{"id": CARDED_COLUMN}]),
        ),
        # What the issue lookup is answered with: the global ID of `#100`.
        payload={"id": 1854, "number": 100},
    )
    mock_session.return_value = session

    result = runner.invoke(
        app,
        [
            "project",
            "issue",
            "move",
            "--owner",
            "owner",
            "--repository",
            "repo",
            "--project-id",
            "1",
            "--column-id",
            "6",
            "--issue-id",
            "100",
            "--token",
            "tok",
            "--base-url",
            "https://gitea.invalid",
        ],
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert not [url for url in session.urls if url.endswith("/move")], session.urls


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_reports_a_move_that_moved_nothing(mock_gitea, mock_get_auth_params, mock_execute):
    """A move reported as a success should be rejected when the card is not in the target column.

    The card is on the board here, so the check made before the move passes and
    the move is made - and answers with a success having changed nothing, which
    is what this endpoint does whenever there was nothing for it to do. A status
    code is therefore not evidence that the card went anywhere; the target column
    is read back, and that is.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    # Carded, so the move goes ahead - on a board whose move endpoint reports
    # success and leaves every card where it was.
    fake = carded(client, 1854, moves=False)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=100,
        column_id=TARGET_COLUMN,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError) as error:
        mock_execute.call_args[1]["api_call"]()

    message = str(error.value)
    assert f"column {TARGET_COLUMN} holds no card for it" in message
    assert "project column list" in message
    # The move really was attempted: this is the answer being distrusted, not the
    # call being skipped.
    client.project.move_project_issue.assert_called_once()
    assert fake.cards[CARDED_COLUMN] == [1854]
    assert fake.cards[TARGET_COLUMN] == []


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        pytest.param(make_http_error(403), "Gitea returned HTTP 403", id="refused"),
        pytest.param(
            RequestsConnectionError("Failed to establish a new connection: [Errno 111] Connection refused"),
            "could not be reached",
            id="unreachable",
        ),
        pytest.param(RequestException("Invalid URL 'columns'"), "the request did not complete", id="incomplete"),
    ],
)
@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_reports_a_move_it_could_not_confirm(
    mock_gitea, mock_get_auth_params, mock_execute, error, expected
):
    """A move that could not be confirmed should be reported as unconfirmed, not as failed.

    The move was made and answered; what the failed read leaves unknown is
    whether it did anything. Reporting it as a failure would be as wrong as
    reporting it as a success, so the message has to say which of the two it is.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.base_url = "https://gitea.example.com"
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    carded(client, 1854)
    # The board is readable up to the move and unreadable after it.
    client.project.move_project_issue.side_effect = lambda **kwargs: setattr_and_return(
        client.project.list_project_column_issues, "side_effect", error
    )
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="repo",
        project_id=1,
        issue_id=100,
        column_id=TARGET_COLUMN,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError) as raised:
        mock_execute.call_args[1]["api_call"]()

    message = str(raised.value)
    assert expected in message
    assert "was made and reported success" in message
    assert "not known to be wrong" in message
    assert "project column issues" in message


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_names_a_global_id_it_cannot_number(mock_gitea, mock_get_auth_params, mock_execute):
    """An issue addressed by global ID should be named as one in the missing-card message.

    With no repository holding the issue named, `--issue-id` was never a number
    of anything, so the message cannot print it as `#N of owner/repo` - and the
    `project issue add` it suggests must not carry an `--issue-repository` that
    was never given.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    uncarded(client)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="org",
        repository=None,
        project_id=1,
        issue_id=1854,
        column_id=TARGET_COLUMN,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError) as error:
        mock_execute.call_args[1]["api_call"]()

    message = str(error.value)
    assert "issue 1854" in message
    assert "#1854" not in message
    assert "--issue-repository" not in message
    assert "--repository" not in message
    assert "gitea-cli project issue add --owner org --project-id 1" in message
    client.issue.get_issue.assert_not_called()


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_recovery_commands_name_the_board_repository(mock_gitea, mock_get_auth_params, mock_execute):
    """A repository project's recovery commands should be scoped to that repository.

    `project list --owner OWNER` lists the owner's own projects, not a
    repository's, so a recovery command missing `--repository` sends the user to a
    listing that cannot contain the project the message just named.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.base_url = "https://gitea.example.com"
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    client.project.list_project_columns.side_effect = make_http_error(403)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="board-repo",
        issue_repository="other-repo",
        project_id=1,
        issue_id=100,
        column_id=TARGET_COLUMN,
        sorting=None,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError) as error:
        mock_execute.call_args[1]["api_call"]()

    assert "gitea-cli project list --owner owner --repository board-repo" in str(error.value)


@patch("gitea.cli.utils.api.execute_api_command")
@patch("gitea.cli.utils.auth.get_auth_params")
@patch("gitea.client.gitea.Gitea")
def test_move_issue_command_sorting_refusal_keeps_both_repositories(mock_gitea, mock_get_auth_params, mock_execute):
    """The add suggested in place of a sorting move should address the same issue and board.

    The board and the issue can live in different repositories, and the suggested
    command has to name both: without `--issue-repository` it would read
    `--issue-id` as a global ID, which is a different issue.
    """
    ctx = make_ctx()
    mock_get_auth_params.return_value = ("tok", "https://gitea.example.com")

    client = MagicMock()
    client.issue.get_issue.return_value = ({"id": 1854, "number": 100}, {"status_code": 200})
    uncarded(client)
    mock_gitea.return_value.__enter__.return_value = client

    move_issue_command(
        ctx=ctx,
        owner="owner",
        repository="board-repo",
        issue_repository="other-repo",
        project_id=1,
        issue_id=100,
        column_id=TARGET_COLUMN,
        sorting=3,
        add_if_missing=True,
        account_name="acct",
        token=None,
        base_url=None,
    )

    with pytest.raises(CommandError) as error:
        mock_execute.call_args[1]["api_call"]()

    message = str(error.value)
    assert (
        f"gitea-cli project issue add --owner owner --repository board-repo --project-id 1 "
        f"--column-id {TARGET_COLUMN} --issue-id 100 --issue-repository other-repo" in message
    )
    # The issue is named as it was addressed, not as a bare number.
    assert "#100 of owner/other-repo" in message
