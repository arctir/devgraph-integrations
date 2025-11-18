"""Configuration models for GitHub provider.

This module defines the configuration classes used to configure the GitHub
provider, including selector patterns for organizations and repositories.
"""
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field

from devgraph_integrations.config.base import SensitiveBaseModel
from devgraph_integrations.molecules.base.config import MoleculeProviderConfig


class GithubSelectorConfig(BaseModel):
    """Configuration for selecting GitHub repositories.

    Defines criteria for selecting repositories within a GitHub organization,
    including name patterns and graph file locations.

    Attributes:
        organization: GitHub organization name to scan
        repo_name: Regex pattern for repository names (defaults to match all)
        graph_files: List of file paths to read for graph definitions (entities and relationships)
    """

    organization: str = Field(
        title="Organization", description="GitHub organization name to scan"
    )
    repo_name: str | None = Field(
        default=".*",
        title="Repository Name Pattern",
        description="Regex pattern for repository names (defaults to match all)",
    )
    graph_files: list[str] = Field(
        default=[".devgraph.yaml"],
        title="Graph Files",
        description="List of file paths to read for graph definitions",
    )


class GithubPATAuth(BaseModel):
    """GitHub Personal Access Token authentication."""

    type: Literal["pat"] = Field(
        default="pat",
        title="Authentication Type",
        description="Personal Access Token authentication",
    )
    token: str = Field(
        title="Personal Access Token",
        description="GitHub personal access token for authentication",
    )


class GithubAppAuth(BaseModel):
    """GitHub App authentication (higher rate limits)."""

    type: Literal["app"] = Field(
        default="app",
        title="Authentication Type",
        description="GitHub App authentication",
    )
    app_id: int = Field(title="App ID", description="GitHub App ID")
    app_private_key: str = Field(
        title="App Private Key", description="GitHub App private key (PEM format)"
    )
    installation_id: int = Field(
        title="Installation ID", description="GitHub App installation ID"
    )


class GithubProviderConfig(MoleculeProviderConfig, SensitiveBaseModel):
    """Main configuration for GitHub provider.

    Contains all settings needed to connect to GitHub API and configure
    repository discovery behavior.

    Note:
        namespace field is inherited from MoleculeProviderConfig base class
    """

    base_url: str = Field(
        default="https://github.com",
        title="Base URL",
        description="Base URL for GitHub web interface",
    )
    api_url: str = Field(
        default="https://api.github.com",
        title="API URL",
        description="GitHub API base URL",
    )

    # Authentication - either PAT or App (discriminated union)
    authentication: Annotated[
        Union[GithubPATAuth, GithubAppAuth],
        Field(
            discriminator="type",
            title="Authentication",
            description="GitHub authentication configuration",
        ),
    ]

    selectors: list[GithubSelectorConfig] = Field(  # type: ignore[assignment]
        default=[],
        title="Repository Selectors",
        description="List of repository selection criteria",
    )

    # Helper properties for backward compatibility
    @property
    def token(self) -> str | None:
        """Get PAT token if using PAT auth."""
        if isinstance(self.authentication, GithubPATAuth):
            return self.authentication.token
        return None

    @property
    def app_id(self) -> int | None:
        """Get App ID if using App auth."""
        if isinstance(self.authentication, GithubAppAuth):
            return self.authentication.app_id
        return None

    @property
    def app_private_key(self) -> str | None:
        """Get App private key if using App auth."""
        if isinstance(self.authentication, GithubAppAuth):
            return self.authentication.app_private_key
        return None

    @property
    def installation_id(self) -> int | None:
        """Get installation ID if using App auth."""
        if isinstance(self.authentication, GithubAppAuth):
            return self.authentication.installation_id
        return None
