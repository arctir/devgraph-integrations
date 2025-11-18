"""Configuration models for Vercel provider.

This module defines the configuration classes used to configure the Vercel
provider, including selector patterns for teams and projects.
"""
from pydantic import Field

from ..base.config import HttpApiProviderWithSelectorsConfig, SelectorConfig


class VercelSelectorConfig(SelectorConfig):
    """Configuration for selecting Vercel projects.

    Defines criteria for selecting projects within Vercel teams,
    including team IDs and project name patterns.

    Attributes:
        team_id: Vercel team ID to scan (optional, defaults to provider-level team_id)
        project_name_pattern: Regex pattern for project names (defaults to match all)
    """

    team_id: str | None = Field(
        default=None,
        description="Vercel team ID to scan (optional, defaults to provider-level team_id)",
    )
    project_name_pattern: str = Field(
        default=".*", description="Regex pattern for project names"
    )


class VercelProviderConfig(HttpApiProviderWithSelectorsConfig):
    """Main configuration for Vercel provider.

    Contains all settings needed to connect to Vercel API and configure
    project and deployment discovery behavior.

    Attributes:
        api_url: Base URL for Vercel API (inherited)
        token: Vercel authentication token (inherited)
        namespace: Kubernetes-style namespace for created entities (inherited)
        timeout: Request timeout in seconds (inherited)
        team_id: Default Vercel team ID that the token has access to
        selectors: List of project selection criteria (inherited)
    """

    api_url: str = Field(
        default="https://api.vercel.com", description="Base URL for Vercel API"
    )
    team_id: str = Field(..., description="Vercel team ID that the token has access to")
    selectors: list[VercelSelectorConfig] = Field(  # type: ignore[assignment]
        default_factory=lambda: [VercelSelectorConfig()],
        description="List of project selection criteria",
    )
