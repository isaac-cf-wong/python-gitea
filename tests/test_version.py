"""Unit tests for version module.

Reloading `gitea.version` is how both branches of its metadata lookup are reached:
the module resolves the version once, at import, so the only way to see the
fallback is to import it again with the lookup patched. A reload leaves the *live*
module carrying whatever the patch produced, and `gitea-cli --version` reads that
attribute when it runs rather than a value captured earlier - so a stale
`0+unknown` left here made that command's test fail in any run that reached it
after this module. Under `pytest` the collection order hid that; the mutation
runner orders tests its own way, and its clean baseline failed on it.

The fixture below reloads the module unpatched once each test is done, so these
tests cannot decide what a later one reads.
"""

import importlib
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

import pytest

import gitea.version


@pytest.fixture(autouse=True)
def restore_version_module():
    """Reload `gitea.version` unpatched after each test in this module.

    Yields:
        None, once per test, which runs against the module as it stands.

    """
    yield
    importlib.reload(gitea.version)


class TestVersion:
    """Test cases for version module."""

    def test_version_installed(self):
        """Test version when package is installed."""
        with patch("importlib.metadata.version", return_value="1.0.0"):
            # Reimport to get the patched version
            importlib.reload(gitea.version)

            assert gitea.version.__version__ == "1.0.0"

    def test_version_not_installed(self):
        """Test version fallback when package is not installed."""
        with patch("importlib.metadata.version", side_effect=PackageNotFoundError("python-gitea")):
            importlib.reload(gitea.version)

            assert gitea.version.__version__ == "0+unknown"

    def test_version_not_none(self):
        """Test that version is always defined and not None."""
        assert gitea.version.__version__ is not None
        assert isinstance(gitea.version.__version__, str)
        assert len(gitea.version.__version__) > 0

    def test_a_patched_lookup_is_not_left_behind(self):
        """The module a later test reads should be the one the environment gives.

        The two tests above reload the module with the lookup patched, and what they
        leave in it is what any test after them sees - which is how
        `gitea-cli --version` came to print `0+unknown` in a run that reached it
        after this module. Asserting the environment's own version here, rather than
        only that some string is set, is what makes such a leak fail a test.
        """
        from importlib.metadata import version

        assert gitea.version.__version__ == version("python-gitea")
