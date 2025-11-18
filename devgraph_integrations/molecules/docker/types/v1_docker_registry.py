"""V1 Docker Registry Entity Definition.

This module defines the entity type for Docker registry instances.
"""

from typing import Optional
from pydantic import Field

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1DockerRegistryEntitySpec(EntitySpec):
    """Specification for Docker Registry entities.

    Attributes:
        name: Human-readable name of the registry
        registry_type: Type of registry (docker-hub, ecr, gcr, acr, private)
        url: Registry base URL
        description: Optional description of the registry
        version: Registry API version if available
        public: Whether this is a public registry
    """

    name: str = Field(..., description="Human-readable name of the registry")
    registry_type: str = Field(..., description="Type of registry")
    url: str = Field(..., description="Registry base URL")
    description: Optional[str] = Field(default=None, description="Registry description")
    version: Optional[str] = Field(default=None, description="Registry API version")
    public: bool = Field(default=True, description="Whether this is a public registry")


class V1DockerRegistryEntity(Entity):
    """Docker Registry entity.

    Represents a Docker registry instance that hosts container images.
    """

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "DockerRegistry"
    spec: V1DockerRegistryEntitySpec  # type: ignore[assignment]

    @property
    def id(self) -> str:
        """Generate unique identifier for this registry."""
        return f"{self.apiVersion}/{self.kind}/{self.metadata.namespace}/{self.metadata.name}"


class V1DockerRegistryEntityDefinition(EntityDefinition[V1DockerRegistryEntitySpec]):
    """Entity definition for Docker registries."""

    group: str = "entities.devgraph.ai"
    kind: str = "DockerRegistry"
    list_kind: str = "DockerRegistryList"
    plural: str = "dockerregistries"
    singular: str = "dockerregistry"
    name: str = "v1"
    spec_class: type = V1DockerRegistryEntitySpec
    display_name: str = "Docker Registry"
    characteristics: list = ["infrastructure", "container registry", "storage"]
    description: str = "A Docker registry that hosts container images"
