"""Docker molecule facade."""

from typing import Any, Dict, Optional, Type

from devgraph_integrations.core.molecule import Molecule


class DockerMolecule(Molecule):
    """Docker molecule providing discovery capabilities."""

    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "name": "docker",
            "display_name": "Docker",
            "description": "Discover Docker registries, repositories, images, and manifests",
            "logo": {"reactIcons": "SiDocker"},
            "homepage_url": "https://www.docker.com",
            "docs_url": "https://docs.docker.com",
            "capabilities": ["discovery"],
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

    @staticmethod
    def get_discovery_provider() -> Optional[Type[Any]]:
        from .provider import DockerProvider

        return DockerProvider
