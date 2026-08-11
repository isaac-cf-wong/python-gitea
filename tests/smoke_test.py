"""Smoke tests before publishing to verify the wheel and source distribution."""

from __future__ import annotations

import subprocess
import sys

import gitea


def test_basic_import() -> None:
    """Test basic import."""
    print(f"Python version: {sys.version}")
    print(f"Package version: {gitea.__version__}")

    # Ensure it's not importing the local folder
    if "site-packages" not in gitea.__file__ and "dist" not in gitea.__file__:
        print(f"Warning: Package imported from unexpected location: {gitea.__file__}")


def test_cli_help() -> None:
    """Test CLI help."""
    # Ensure the 'gitea-cli' command was registered and runs
    result = subprocess.run(["gitea-cli", "--help"], capture_output=True, text=True, check=False)  # noqa: S607
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


if __name__ == "__main__":
    test_basic_import()
    print("Smoke test passed: Package is importable.")

    test_cli_help()
    print("Smoke test passed: The CLI is executable.")
