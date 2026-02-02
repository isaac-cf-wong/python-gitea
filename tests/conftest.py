"""Configuration and fixtures for pytest."""

from __future__ import annotations

import logging

import pytest


@pytest.fixture(autouse=True)
def setup_logger() -> None:
    """Ensure the gitea logger is properly configured for testing.

    This fixture ensures that:
    - The logger propagates messages to the root logger (for caplog capture)
    - The logger level allows all messages to be logged
    """
    logger = logging.getLogger("gitea")
    logger.propagate = True
    logger.setLevel(logging.DEBUG)

    # Clear any existing handlers to avoid interference
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
