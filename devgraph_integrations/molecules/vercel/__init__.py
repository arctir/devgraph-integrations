"""Vercel molecule for Devgraph.

This module provides Vercel integration for discovering deployments, projects,
and teams on the Vercel platform.
"""

from .config import VercelProviderConfig
from .provider import VercelProvider

__version__ = "1.0.0"
__molecule_metadata__ = {
    "version": __version__,
    "name": "vercel",
    "display_name": "Vercel",
    "description": "Discover Vercel deployments, projects, and teams",
    "logo": {"reactIcons": "SiVercel"},  # react-icons identifier (from react-icons/si)
    "homepage_url": "https://vercel.com",
    "docs_url": "https://vercel.com/docs",
    "capabilities": [
        "discovery",
    ],
    "entity_types": [
        "VercelDeployment",
        "VercelProject",
        "VercelTeam",
    ],
    "relation_types": [
        "VercelDeploymentBelongsToProject",
        "VercelProjectBelongsToTeam",
    ],
    "requires_auth": True,
    "auth_types": ["api_token"],
    "min_framework_version": "0.1.0",
}

__all__ = [
    "VercelProvider",
    "VercelProviderConfig",
    "__version__",
    "__molecule_metadata__",
]
