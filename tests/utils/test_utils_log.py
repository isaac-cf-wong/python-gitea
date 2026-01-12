"""Unit tests for logging utilities."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from gitea.utils.log import get_version_information, setup_logger


class TestGetVersionInformation:
    """Test cases for get_version_information function."""

    @patch("gitea.utils.log.__version__", "1.0.0")
    def test_get_version_information(self):
        """Test getting version information."""
        version = get_version_information()
        assert version == "1.0.0"


class TestSetupLogger:
    """Test cases for setup_logger function."""

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock the logger."""
        with patch("logging.getLogger", return_value=MagicMock()) as mock_get_logger:
            mock_logger = mock_get_logger.return_value
            yield mock_logger

    def test_setup_logger_default(self, mock_logger):
        """Test setup_logger with default parameters."""
        setup_logger()

        mock_logger.setLevel.assert_called_with(20)  # INFO level
        # Verify addHandler was called for stream handler
        assert mock_logger.addHandler.call_count >= 1

    def test_setup_logger_with_label(self, mock_logger):
        """Test setup_logger with label for file logging."""
        with patch("gitea.utils.log.Path") as mock_path:
            mock_outdir = MagicMock()
            mock_path.return_value = mock_outdir
            mock_outdir.mkdir = MagicMock()
            mock_file = MagicMock()
            mock_outdir.__truediv__ = MagicMock(return_value=mock_file)

            with patch("gitea.utils.log.logging.FileHandler"):
                setup_logger(outdir="/tmp", label="test")

                mock_path.assert_called_with("/tmp")
                mock_outdir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
                # Verify both stream and file handlers were added
                assert mock_logger.addHandler.call_count >= 2  # noqa: PLR2004

    def test_setup_logger_log_level_string(self, mock_logger):
        """Test setup_logger with string log level."""
        setup_logger(log_level="DEBUG")

        mock_logger.setLevel.assert_called_with(10)  # DEBUG level

    def test_setup_logger_log_level_int(self, mock_logger):
        """Test setup_logger with integer log level."""
        setup_logger(log_level=30)  # WARNING

        mock_logger.setLevel.assert_called_with(30)

    def test_setup_logger_invalid_log_level(self):
        """Test setup_logger with invalid log level."""
        with pytest.raises(ValueError, match="log_level INVALID not understood"):
            setup_logger(log_level="INVALID")

    @patch("gitea.utils.log.get_version_information", return_value="1.0.0")
    def test_setup_logger_print_version(self, mock_get_version, mock_logger):
        """Test setup_logger with print_version=True."""
        setup_logger(print_version=True)

        mock_logger.info.assert_called_once_with("Running python-gitea version: %s", "1.0.0")

    def test_setup_logger_no_duplicate_handlers(self):
        """Test that handlers are not added if they already exist."""
        # Create a fresh mock logger with existing handlers
        mock_logger = MagicMock()
        mock_stream_handler = MagicMock(spec=logging.StreamHandler)
        mock_stream_handler.__class__ = logging.StreamHandler
        mock_stream_handler.__class__.__name__ = "StreamHandler"
        mock_file_handler = MagicMock(spec=logging.FileHandler)
        mock_file_handler.__class__ = logging.FileHandler
        mock_file_handler.__class__.__name__ = "FileHandler"
        mock_logger.handlers = [mock_stream_handler, mock_file_handler]

        with patch("logging.getLogger", return_value=mock_logger):
            setup_logger(label="test")

        # No new handlers should be added since they already exist
        mock_logger.addHandler.assert_not_called()

    def test_setup_logger_updates_handler_levels(self, mock_logger):
        """Test that existing handler levels are updated."""
        mock_handler = MagicMock()
        mock_logger.handlers = [mock_handler]

        setup_logger(log_level="ERROR")

        mock_handler.setLevel.assert_called_with(40)  # ERROR level
