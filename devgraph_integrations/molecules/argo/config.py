"""Configuration models for Argo CD provider.

This module defines the configuration class used to configure the Argo CD
provider, including API connection settings and authentication.
"""

from ..base.config import HttpApiProviderConfig


class ArgoProviderConfig(HttpApiProviderConfig):
    """Configuration for Argo CD provider.

    Contains all settings needed to connect to Argo CD API and configure
    entity discovery behavior.

    Attributes:
        api_url: Base URL for Argo CD API endpoints (inherited)
        token: Authentication token for Argo CD API access (inherited)
        namespace: Kubernetes-style namespace for created entities (inherited)
        timeout: Request timeout in seconds (inherited)
    """

    pass  # All required configuration is inherited from base class
