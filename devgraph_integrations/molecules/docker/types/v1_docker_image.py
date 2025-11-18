"""V1 Docker Image Entity Definition.

This module defines the entity type for Docker images/tags within repositories.
"""

from typing import Optional, Dict, Any
from pydantic import Field

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1DockerImageEntitySpec(EntitySpec):
    """Specification for Docker Image entities.

    Attributes:
        repository: Repository name this image belongs to
        tag: Image tag (e.g., 'latest', 'v1.0.0')
        digest: Image digest/SHA256 hash
        size: Image size in bytes
        architecture: Target architecture (e.g., 'amd64', 'arm64')
        os: Target operating system (e.g., 'linux', 'windows')
        created: Creation timestamp
        last_updated: Last update timestamp
        labels: Image labels/metadata
        layers: Number of layers
        vulnerabilities: Vulnerability scan results (if available)
        registry_url: URL of the parent registry
    """

    repository: str = Field(..., description="Repository name this image belongs to")
    tag: str = Field(..., description="Image tag")
    digest: Optional[str] = Field(default=None, description="Image digest/SHA256 hash")
    size: Optional[int] = Field(default=None, description="Image size in bytes")
    architecture: Optional[str] = Field(default=None, description="Target architecture")
    os: Optional[str] = Field(default=None, description="Target operating system")
    created: Optional[str] = Field(default=None, description="Creation timestamp")
    last_updated: Optional[str] = Field(
        default=None, description="Last update timestamp"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict, description="Image labels/metadata"
    )
    layers: Optional[int] = Field(default=None, description="Number of layers")
    vulnerabilities: Optional[Dict[str, Any]] = Field(
        default=None, description="Vulnerability scan results"
    )
    registry_url: str = Field(..., description="URL of the parent registry")


class V1DockerImageEntity(Entity):
    """Docker Image entity.

    Represents a specific tagged version of a container image.
    """

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "DockerImage"
    spec: V1DockerImageEntitySpec  # type: ignore[assignment]

    @property
    def id(self) -> str:
        """Generate unique identifier for this image."""
        return f"{self.apiVersion}/{self.kind}/{self.metadata.namespace}/{self.metadata.name}"


class V1DockerImageEntityDefinition(EntityDefinition[V1DockerImageEntitySpec]):
    """Entity definition for Docker images."""

    group: str = "entities.devgraph.ai"
    kind: str = "DockerImage"
    list_kind: str = "DockerImageList"
    plural: str = "dockerimages"
    singular: str = "dockerimage"
    name: str = "v1"
    spec_class: type = V1DockerImageEntitySpec
    display_name: str = "Docker Image"
    characteristics: list = ["container", "artifact", "deployable"]
    description: str = "A specific tagged version of a container image"
