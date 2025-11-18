"""Argo CD molecule for Devgraph.

This module provides Argo CD integration for discovering applications, projects,
and instances in GitOps deployments.
"""

from .provider import ArgoProvider

__version__ = "1.0.0"
__molecule_metadata__ = {
    "version": __version__,
    "name": "argo",
    "display_name": "Argo CD",
    "description": "Discover Argo CD applications, projects, and instances for GitOps tracking",
    "logo": {"reactIcons": "SiArgocd"},  # react-icons identifier (from react-icons/si)
    "homepage_url": "https://argo-cd.readthedocs.io",
    "docs_url": "https://argo-cd.readthedocs.io/en/stable/",
    "capabilities": [
        "discovery",
    ],
    "entity_types": [
        "ArgoApplication",
        "ArgoProject",
        "ArgoInstance",
    ],
    "relation_types": [
        "ArgoApplicationBelongsToProject",
        "ArgoApplicationDeployedOn",
    ],
    "requires_auth": True,
    "auth_types": ["api_token"],
    "min_framework_version": "0.1.0",
}

__all__ = ["ArgoProvider", "__version__", "__molecule_metadata__"]
