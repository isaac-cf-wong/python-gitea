"""Unit tests for the messages the CLI builds for failed requests."""

from requests import ConnectionError as RequestsConnectionError
from requests.exceptions import InvalidURL

from gitea.cli.utils.errors import request_failed_message, unreachable_message

BASE_URL = "https://gitea.example.com"


def test_unreachable_message_names_the_base_url_when_it_is_known():
    """Should point at the instance that was tried and at what to check."""
    error = RequestsConnectionError("Failed to establish a new connection: [Errno 111] Connection refused")

    message = unreachable_message(error, BASE_URL)

    assert message.startswith(f"Could not reach the Gitea API at {BASE_URL}: ")
    assert str(error) in message
    assert "network allows the connection" in message


def test_unreachable_message_omits_the_host_when_it_is_unknown():
    """Should still read as a sentence when no base URL was passed."""
    message = unreachable_message(RequestsConnectionError("Connection refused"))

    assert message.startswith("Could not reach the Gitea API: ")
    assert "at None" not in message


def test_request_failed_message_names_the_error_type_and_the_base_url():
    """Should name the type, since there is no traceback left to read it from."""
    error = InvalidURL("Failed to parse: gitea.example.com:3000")

    message = request_failed_message(error, BASE_URL)

    assert message.startswith(f"Could not complete the request to the Gitea API at {BASE_URL}: InvalidURL: ")
    assert str(error) in message
    # The instance may well be up, so the message must not say otherwise.
    assert "Could not reach" not in message


def test_request_failed_message_omits_the_host_when_it_is_unknown():
    """Should still read as a sentence when no base URL was passed."""
    message = request_failed_message(InvalidURL("Failed to parse"))

    assert message.startswith("Could not complete the request to the Gitea API: InvalidURL: ")
    assert "at None" not in message
