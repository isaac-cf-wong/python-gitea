"""Unit tests for version module."""

import importlib
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

import gitea.version


class TestVersion:
    """Test cases for version module."""

    def test_version_installed(self):
        """Test version when package is installed."""
        with patch("importlib.metadata.version", return_value="1.0.0"):
            # Reimport to get the patched version

            importlib.reload(gitea.version)
            from gitea.version import __version__  # noqa: PLC0415

            assert __version__ == "1.0.0"

    def test_version_not_installed(self):
        """Test version fallback when package is not installed."""
        with patch("importlib.metadata.version", side_effect=PackageNotFoundError("python-gitea")):
            importlib.reload(gitea.version)
            from gitea.version import __version__  # noqa: PLC0415

            assert __version__ == "0+unknown"

    def test_version_not_none(self):
        """Test that version is always defined and not None."""
        from gitea.version import __version__  # noqa: PLC0415

        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0
