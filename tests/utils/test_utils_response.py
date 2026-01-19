"""Unit tests for response utility functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gitea.utils.response import process_async_response, process_response


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

        result = process_response(mock_response)

        assert result == ({}, 204)
        mock_response.json.assert_not_called()

    def test_process_response_error_status(self):
        """Test processing a response with error status code."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        result = process_response(mock_response)

        assert result == ({}, 404)
        mock_response.json.assert_not_called()

    def test_process_response_invalid_json(self):
        """Test processing a response with invalid JSON."""
        value_error = ValueError("Invalid JSON")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = value_error

        with patch("gitea.utils.response.logger") as mock_logger:
            result = process_response(mock_response)

        assert result == ({}, 200)
        mock_logger.error.assert_called_once_with("Failed to parse JSON response: %s", value_error)


class TestProcessAsyncResponse:
    """Test cases for process_async_response."""

    @pytest.mark.asyncio
    async def test_process_async_response_success(self):
        """Test processing a successful async response with JSON data."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"key": "value"})

        result = await process_async_response(mock_response)

        assert result == ({"key": "value"}, 200)
        mock_response.json.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_async_response_no_content(self):
        """Test processing a 204 No Content async response."""
        mock_response = MagicMock()
        mock_response.status = 204

        result = await process_async_response(mock_response)

        assert result == ({}, 204)
        mock_response.json.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_async_response_error_status(self):
        """Test processing an async response with error status code."""
        mock_response = MagicMock()
        mock_response.status = 404

        result = await process_async_response(mock_response)

        assert result == ({}, 404)
        mock_response.json.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_async_response_invalid_json(self):
        """Test processing an async response with invalid JSON."""
        value_error = ValueError("Invalid JSON")
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(side_effect=value_error)

        with patch("gitea.utils.response.logger") as mock_logger:
            result = await process_async_response(mock_response)

        assert result == ({}, 200)
        mock_logger.error.assert_called_once_with("Failed to parse JSON response: %s", value_error)
