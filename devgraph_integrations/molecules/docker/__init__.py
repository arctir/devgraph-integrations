"""Docker registry molecule for Devgraph.

This module provides integration with Docker registries to discover and manage
container images, repositories, and registry metadata as entities in Devgraph.
"""

from .config import DockerProviderConfig
from .provider import DockerProvider

__version__ = "1.0.0"
__molecule_metadata__ = {
    "version": __version__,
    "name": "docker",
    "display_name": "Docker",
    "description": "Discover Docker registries, repositories, images, and manifests",
    "logo": {"reactIcons": "SiDocker"},  # react-icons identifier (from react-icons/si)
    "homepage_url": "https://www.docker.com",
    "docs_url": "https://docs.docker.com",
    "capabilities": [
        "discovery",
    ],
    "entity_types": [
        "DockerRegistry",
        "DockerRepository",
        "DockerImage",
        "DockerManifest",
    ],
    "relation_types": [
        "DockerRepositoryHostedOn",
        "DockerImageBelongsToRepository",
    ],
    "requires_auth": True,
    "auth_types": ["basic_auth", "api_token"],
    "min_framework_version": "0.1.0",
}

__all__ = [
    "DockerProvider",
    "DockerProviderConfig",
    "__version__",
    "__molecule_metadata__",
]
