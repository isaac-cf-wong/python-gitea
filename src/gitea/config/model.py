"""Configuration model for GitHub accounts."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class AccountConfig(BaseModel):
    """Configuration for a GitHub account."""

    name: str = Field(..., description="Label of the Gitea account (e.g., 'my_account').")
    """Label of the Gitea account (e.g., 'my_account')."""
    token: str = Field(..., description="Authentication token for Gitea.")
    """Authentication token for the account."""
    base_url: str = Field(default="https://gitea.com", description="Base URL for Gitea.")
    """Base URL for the GitHub platform."""

    def __repr__(self) -> str:
        """Return a string representation of the AccountConfig.

        Returns:
            A string representation of the AccountConfig.

        """
        return f"AccountConfig(name={self.name}, base_url={self.base_url})"

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate and normalize the base_url field.

        Args:
            v: The base URL to validate.

        Returns:
            The normalized base URL.

        """
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")

        return v.rstrip("/")


class Config(BaseModel):
    """Main configuration model for gitea."""

    accounts: dict[str, AccountConfig] = Field(
        default_factory=dict,
        description="Dictionary of account configurations.",
    )
    """Dictionary of account configurations."""

    default_account: str | None = Field(
        default=None,
        description="Name of the default account to use.",
    )
    """Name of the default account to use."""
