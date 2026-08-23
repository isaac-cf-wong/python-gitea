"""Unit tests for response utility functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gitea.utils.response import (
    process_async_binary_response,
    process_async_response,
    process_async_text_response,
    process_binary_response,
    process_response,
    process_text_response,
)


class TestProcessResponse:
    """Test cases for process_response."""

    def test_process_response_success(self):
        """Test processing a successful response with JSON data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}

        result = process_response(mock_response)

        assert result == ({"key": "value"}, 200)
        mock_response.json.assert_called_once()

    def test_process_response_no_content(self):
        """Test processing a 204 No Content response."""
        mock_response = MagicMock()
        mock_response.status_code = 204

        result = process_response(mock_response, default={})

        assert result == ({}, 204)
        mock_response.json.assert_not_called()

    def test_process_response_error_status(self):
        """Test processing a response with error status code."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        result = process_response(mock_response, default={})

        assert result == ({}, 404)
        mock_response.json.assert_not_called()

    def test_process_response_empty_body(self):
        """Test processing a 2xx response with an empty body."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = b""

        result = process_response(mock_response, default={})

        assert result == ({}, 201)
        mock_response.json.assert_not_called()

    def test_process_response_invalid_json(self):
        """Test processing a response with invalid JSON."""
        value_error = ValueError("Invalid JSON")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = value_error

        with patch("gitea.utils.response.logger") as mock_logger:
            result = process_response(mock_response, default={})

        assert result == ({}, 200)
        mock_logger.error.assert_called_once_with("Failed to parse JSON response: %s", value_error)


class TestProcessAsyncResponse:
    """Test cases for process_async_response."""

    @pytest.mark.asyncio
    async def test_process_async_response_success(self):
        """Test processing a successful async response with JSON data."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b'{"key": "value"}')

        result = await process_async_response(mock_response)

        assert result == ({"key": "value"}, 200)
        mock_response.read.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_async_response_no_content(self):
        """Test processing a 204 No Content async response."""
        mock_response = MagicMock()
        mock_response.status = 204

        result = await process_async_response(mock_response, default={})

        assert result == ({}, 204)
        mock_response.read.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_async_response_empty_body(self):
        """Test processing a 2xx async response with an empty body."""
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.read = AsyncMock(return_value=b"")

        result = await process_async_response(mock_response, default={})

        assert result == ({}, 201)
        mock_response.read.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_async_response_error_status(self):
        """Test processing an async response with error status code."""
        mock_response = MagicMock()
        mock_response.status = 404

        result = await process_async_response(mock_response, default={})

        assert result == ({}, 404)
        mock_response.read.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_async_response_invalid_json(self):
        """Test processing an async response with invalid JSON."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"not json")

        with patch("gitea.utils.response.logger") as mock_logger:
            result = await process_async_response(mock_response, default={})

        assert result == ({}, 200)
        mock_logger.error.assert_called_once()
        args, _ = mock_logger.error.call_args
        assert args[0] == "Failed to parse JSON response: %s"
        assert isinstance(args[1], ValueError)


class TestProcessTextResponse:
    """Test cases for process_text_response, which reads a body that is not JSON."""

    def test_the_body_is_handed_back_as_text(self):
        """A successful response should be decoded, not parsed."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"::group::Run\nbuilding\n"

        assert process_text_response(mock_response) == ("::group::Run\nbuilding\n", 200)
        mock_response.json.assert_not_called()

    def test_the_body_is_decoded_as_utf8(self):
        """A non-ASCII body should arrive intact.

        `requests` guesses the encoding when the response declares none, so a
        log served as an opaque blob would be decoded by that guess and would
        reach the caller differently from the same bytes read by the
        asynchronous client. Both decode UTF-8 instead.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = "building…".encode()

        assert process_text_response(mock_response) == ("building…", 200)

    def test_an_undecodable_byte_is_replaced_rather_than_raising(self):
        """A malformed byte should not cost the caller the rest of the log."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"before \xff after"

        text, status_code = process_text_response(mock_response)

        assert status_code == 200
        assert text.startswith("before ")
        assert text.endswith(" after")

    def test_an_empty_body_answers_with_the_default(self):
        """A job that has produced no output yet answers with the default."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b""

        assert process_text_response(mock_response) == ("", 200)

    def test_a_response_without_a_body_answers_with_the_default(self):
        """A 204 carries nothing to decode."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.content = b""

        assert process_text_response(mock_response, default="none") == ("none", 204)

    def test_an_error_body_is_not_handed_back_as_the_payload(self):
        """A failure's body is the error, not the log, so it is not returned as one."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.content = b'{"message":"job does not exist"}'

        assert process_text_response(mock_response) == ("", 404)


class TestProcessAsyncTextResponse:
    """Test cases for process_async_text_response."""

    @pytest.mark.asyncio
    async def test_the_body_is_handed_back_as_text(self):
        """A successful response should be decoded, not parsed."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"::group::Run\nbuilding\n")

        assert await process_async_text_response(mock_response) == ("::group::Run\nbuilding\n", 200)

    @pytest.mark.asyncio
    async def test_the_body_is_decoded_as_utf8(self):
        """The asynchronous path decodes what the synchronous one decodes."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value="building…".encode())

        assert await process_async_text_response(mock_response) == ("building…", 200)

    @pytest.mark.asyncio
    async def test_an_undecodable_byte_is_replaced_rather_than_raising(self):
        """A malformed byte should not cost the caller the rest of the log."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"before \xff after")

        text, status_code = await process_async_text_response(mock_response)

        assert status_code == 200
        assert text.startswith("before ")
        assert text.endswith(" after")

    @pytest.mark.asyncio
    async def test_an_empty_body_answers_with_the_default(self):
        """A job that has produced no output yet answers with the default."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"")

        assert await process_async_text_response(mock_response) == ("", 200)

    @pytest.mark.asyncio
    async def test_a_response_without_a_body_is_not_read(self):
        """A 204 carries nothing to read, so the body is not asked for."""
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.read = AsyncMock(return_value=b"")

        assert await process_async_text_response(mock_response, default="none") == ("none", 204)

    @pytest.mark.asyncio
    async def test_an_error_body_is_not_handed_back_as_the_payload(self):
        """A failure's body is the error, not the log, so it is not read at all."""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.read = AsyncMock(return_value=b'{"message":"job does not exist"}')

        assert await process_async_text_response(mock_response) == ("", 404)
        mock_response.read.assert_not_called()


# A zip as Gitea sends one: the local file header, then bytes that no encoding
# would decode. They are the point of these tests - the text path would replace
# them, and an archive that has been through that no longer opens.
ARCHIVE = b"PK\x03\x04\xff\xfe not text \x00"


class TestProcessBinaryResponse:
    """Test cases for process_binary_response, which reads a body that is a file."""

    def test_the_bytes_are_handed_back_as_they_arrived(self):
        """A body is returned unchanged, byte for byte."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = ARCHIVE

        assert process_binary_response(mock_response) == (ARCHIVE, 200)

    def test_invalid_utf8_survives(self):
        """Bytes that are not valid UTF-8 are not replaced, where the text path replaces them.

        This is the whole reason the binary path exists beside the text one. The
        comparison is against `process_text_response` on the same bytes, so the
        two are seen to differ rather than asserted to in a comment.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = ARCHIVE

        binary, _ = process_binary_response(mock_response)
        text, _ = process_text_response(mock_response)

        assert binary == ARCHIVE
        assert text.encode() != ARCHIVE

    def test_an_empty_body_gives_the_default(self):
        """A response with no body answers with the default, which is the empty bytes.

        An expired artifact answers exactly this way, so the default has to be
        bytes: a caller writing the result to a file meets a `TypeError` otherwise.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b""

        assert process_binary_response(mock_response) == (b"", 200)

    def test_no_content_gives_the_default(self):
        """A 204 answers with the default rather than with an empty archive."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.content = b""

        assert process_binary_response(mock_response, default=b"none") == (b"none", 204)

    def test_an_error_status_gives_the_default(self):
        """A failure answers with the default and reports the status."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.content = b"not found"

        assert process_binary_response(mock_response) == (b"", 404)


class TestProcessAsyncBinaryResponse:
    """Test cases for process_async_binary_response."""

    @pytest.mark.asyncio
    async def test_the_bytes_are_handed_back_as_they_arrived(self):
        """A body is returned unchanged, byte for byte."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=ARCHIVE)

        assert await process_async_binary_response(mock_response) == (ARCHIVE, 200)

    @pytest.mark.asyncio
    async def test_both_clients_hand_back_the_same_archive(self):
        """The two paths should agree, so an artifact is the same file from either client."""
        synchronous = MagicMock()
        synchronous.status_code = 200
        synchronous.content = ARCHIVE

        asynchronous = MagicMock()
        asynchronous.status = 200
        asynchronous.read = AsyncMock(return_value=ARCHIVE)

        assert process_binary_response(synchronous)[0] == (await process_async_binary_response(asynchronous))[0]

    @pytest.mark.asyncio
    async def test_an_empty_body_gives_the_default(self):
        """A response with no body answers with the default."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"")

        assert await process_async_binary_response(mock_response) == (b"", 200)

    @pytest.mark.asyncio
    async def test_no_content_gives_the_default(self):
        """A 204 answers with the default and never reads the body."""
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.read = AsyncMock(return_value=b"")

        assert await process_async_binary_response(mock_response, default=b"none") == (b"none", 204)

    @pytest.mark.asyncio
    async def test_an_error_status_gives_the_default(self):
        """A failure answers with the default and reports the status."""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.read = AsyncMock(return_value=b"not found")

        assert await process_async_binary_response(mock_response) == (b"", 404)
