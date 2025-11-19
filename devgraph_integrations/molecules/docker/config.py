"""Configuration models for Docker registry provider.

This module defines the configuration classes used to configure the Docker
registry provider, including selector patterns for registries and repositories.
"""

from typing import Optional

from pydantic import Field

from devgraph_integrations.config.base import SensitiveBaseModel

from ..base.config import HttpApiProviderWithSelectorsConfig, SelectorConfig


class DockerSelectorConfig(SelectorConfig):
    """Configuration for selecting Docker repositories.

    Defines criteria for selecting repositories within a Docker registry,
    including namespace patterns and repository name patterns.

    Attributes:
        namespace_pattern: Regex pattern for namespaces/organizations (defaults to match all)
        repository_pattern: Regex pattern for repository names (defaults to match all)
        include_tags: List of specific tags to include (optional)
        exclude_tags: List of tag patterns to exclude (optional)
        max_tags: Maximum number of tags to fetch per repository (default: 10)
    """

    namespace_pattern: str = Field(
        default=".*", description="Regex pattern for namespaces/organizations"
    )
    repository_pattern: str = Field(
        default=".*", description="Regex pattern for repository names"
    )
    include_tags: Optional[list[str]] = Field(
        default=None, description="List of specific tags to include"
    )
    exclude_tags: Optional[list[str]] = Field(
        default=None, description="List of tag patterns to exclude"
    )
    max_tags: int = Field(
        default=10, description="Maximum number of tags to fetch per repository"
    )


class DockerProviderConfig(HttpApiProviderWithSelectorsConfig, SensitiveBaseModel):
    """Main configuration for Docker registry provider.

    Contains all settings needed to connect to Docker registry API and configure
    repository and image discovery behavior.

    Attributes:
        api_url: Base URL for Docker registry API
        token: Docker registry authentication token
        username: Username for authentication (if using basic auth)
        password: Password for authentication (if using basic auth)
        namespace: Kubernetes-style namespace for created entities
        timeout: Request timeout in seconds
        registry_type: Type of registry (docker-hub, ecr, gcr, acr, private)
        selectors: List of repository selection criteria
        discover_vulnerabilities: Whether to discover vulnerability information
    """

    api_url: str = Field(
        default="https://registry-1.docker.io",
        description="Base URL for Docker registry API",
    )
    registry_type: str = Field(
        default="docker-hub",
        description="Type of registry (docker-hub, ecr, gcr, acr, private)",
    )
    username: Optional[str] = Field(
        default=None, description="Username for authentication"
    )
    password: Optional[str] = Field(
        default=None, description="Password for authentication"
    )
    token: Optional[str] = Field(
        default=None, description="Registry authentication token"
    )
    discover_vulnerabilities: bool = Field(
        default=False, description="Whether to discover vulnerability information"
    )
    selectors: list[DockerSelectorConfig] = Field(  # type: ignore[assignment]
        default_factory=lambda: [DockerSelectorConfig()],
        description="List of repository selection criteria",
    )
