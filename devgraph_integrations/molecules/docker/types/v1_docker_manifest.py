"""V1 Docker Manifest Entity Definition.

This module defines the entity type for Docker image manifests.
"""

from typing import List, Optional

from pydantic import Field

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1DockerManifestEntitySpec(EntitySpec):
    """Specification for Docker Manifest entities.

    Attributes:
        repository: Repository name this manifest belongs to
        digest: Manifest digest/SHA256 hash
        media_type: Manifest media type
        schema_version: Manifest schema version
        architecture: Target architecture
        os: Target operating system
        size: Total size of the image
        config_digest: Configuration blob digest
        layer_digests: List of layer digests
        created: Creation timestamp
        registry_url: URL of the parent registry
    """

    repository: str = Field(..., description="Repository name this manifest belongs to")
    digest: str = Field(..., description="Manifest digest/SHA256 hash")
    media_type: str = Field(..., description="Manifest media type")
    schema_version: int = Field(..., description="Manifest schema version")
    architecture: Optional[str] = Field(default=None, description="Target architecture")
    os: Optional[str] = Field(default=None, description="Target operating system")
    size: Optional[int] = Field(default=None, description="Total size of the image")
    config_digest: Optional[str] = Field(
        default=None, description="Configuration blob digest"
    )
    layer_digests: List[str] = Field(
        default_factory=list, description="List of layer digests"
    )
    created: Optional[str] = Field(default=None, description="Creation timestamp")
    registry_url: str = Field(..., description="URL of the parent registry")


class V1DockerManifestEntity(Entity):
    """Docker Manifest entity.

    Represents the manifest/metadata for a container image.
    """

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "DockerManifest"
    spec: V1DockerManifestEntitySpec  # type: ignore[assignment]

    @property
    def id(self) -> str:
        """Generate unique identifier for this manifest."""
        return f"{self.apiVersion}/{self.kind}/{self.metadata.namespace}/{self.metadata.name}"


class V1DockerManifestEntityDefinition(EntityDefinition[V1DockerManifestEntitySpec]):
    """Entity definition for Docker manifests."""

    group: str = "entities.devgraph.ai"
    kind: str = "DockerManifest"
    list_kind: str = "DockerManifestList"
    plural: str = "dockermanifests"
    singular: str = "dockermanifest"
    name: str = "v1"
    spec_class: type = V1DockerManifestEntitySpec
    display_name: str = "Docker Manifest"
    characteristics: list = ["container", "metadata", "multi-platform"]
    description: str = "Manifest metadata for a container image"
