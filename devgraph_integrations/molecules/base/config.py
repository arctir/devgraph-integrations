"""Base configuration models for molecule providers.

This module provides common configuration patterns used across multiple
molecule providers to reduce duplication and ensure consistency.
"""

from typing import List

from pydantic import BaseModel, ConfigDict, Field

from devgraph_integrations.config.base import SensitiveBaseModel


class MoleculeProviderConfig(BaseModel):
    """Base configuration for molecule providers.

    Provides common configuration fields that most providers need,
    including namespace and authentication settings.

    Attributes:
        namespace: Kubernetes-style namespace for created entities
    """

    namespace: str = Field(
        default="default", description="Kubernetes-style namespace for created entities"
    )

    model_config = ConfigDict(extra="allow")


class TokenAuthConfig(MoleculeProviderConfig, SensitiveBaseModel):
    """Base configuration for token-authenticated providers.

    Extends base configuration with token authentication support.

    Attributes:
        token: Authentication token for API access
    """

    token: str = Field(..., description="Authentication token for API access")


class HttpApiProviderConfig(TokenAuthConfig):
    """Base configuration for HTTP API-based providers.

    Extends token auth configuration with API URL settings.

    Attributes:
        api_url: Base URL for API endpoints
        timeout: Request timeout in seconds
    """

    api_url: str = Field(..., description="Base URL for API endpoints")
    timeout: int = Field(default=30, description="Request timeout in seconds", gt=0)


class SelectorConfig(BaseModel):
    """Base configuration for resource selectors.

    Provides common pattern for selecting resources from external systems.
    """

    pass


class HttpApiProviderWithSelectorsConfig(HttpApiProviderConfig):
    """Base configuration for HTTP API providers with selectors.

    Combines HTTP API configuration with selector support.

    Attributes:
        selectors: List of resource selection criteria
    """

    selectors: List[SelectorConfig] = Field(
        default_factory=list, description="List of resource selection criteria"
    )
