"""Unit tests for __main__.py."""

from unittest.mock import patch


class TestMain:
    """Test cases for __main__.py."""

    @patch("gitea.utils.log.setup_logger")
    def test_main_calls_setup_logger(self, mock_setup_logger):
        """Test that running __main__.py calls setup_logger with print_version=True."""
        # Execute the __main__.py code as if run as main
        exec(open("src/gitea/__main__.py").read(), {"__name__": "__main__"})  # noqa: SIM115

        # Verify setup_logger was called with print_version=True
        mock_setup_logger.assert_called_once_with(print_version=True)

    @patch("gitea.utils.log.setup_logger")
    def test_main_not_called_on_import(self, mock_setup_logger):
        """Test that importing __main__.py does not call setup_logger."""
        # Import the module (this sets __name__ to 'gitea.__main__')
        import gitea.__main__  # noqa: F401, PLC0415

        # Verify setup_logger was not called
        mock_setup_logger.assert_not_called()
