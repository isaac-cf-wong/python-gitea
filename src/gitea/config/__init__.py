"""Initialization of the configuration module for gitea."""

from __future__ import annotations

from gitea.config.manager import ConfigManager
from gitea.config.model import AccountConfig, Config

__all__ = ["AccountConfig", "Config", "ConfigManager"]
