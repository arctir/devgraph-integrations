"""V1 Docker Repository Entity Definition.

This module defines the entity type for Docker repositories within registries.
"""

from typing import Optional
from pydantic import Field

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1DockerRepositoryEntitySpec(EntitySpec):
    """Specification for Docker Repository entities.

    Attributes:
        name: Repository name (e.g., 'nginx', 'library/ubuntu')
        full_name: Full repository name including namespace
        namespace: Repository namespace/organization
        description: Optional repository description
        official: Whether this is an official repository
        automated: Whether builds are automated
        star_count: Number of stars (if available)
        pull_count: Number of pulls (if available)
        last_updated: Last update timestamp
        registry_url: URL of the parent registry
        source_repository: URL of the source code repository (from OCI labels)
    """

    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full repository name including namespace")
    namespace: Optional[str] = Field(default=None, description="Repository namespace")
    description: Optional[str] = Field(
        default=None, description="Repository description"
    )
    official: bool = Field(
        default=False, description="Whether this is an official repository"
    )
    automated: bool = Field(default=False, description="Whether builds are automated")
    star_count: Optional[int] = Field(default=None, description="Number of stars")
    pull_count: Optional[int] = Field(default=None, description="Number of pulls")
    last_updated: Optional[str] = Field(
        default=None, description="Last update timestamp"
    )
    registry_url: str = Field(..., description="URL of the parent registry")
    source_repository: Optional[str] = Field(
        default=None, description="URL of the source code repository"
    )


class V1DockerRepositoryEntity(Entity):
    """Docker Repository entity.

    Represents a container image repository within a Docker registry.
    """

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "DockerRepository"
    spec: V1DockerRepositoryEntitySpec  # type: ignore[assignment]

    @property
    def id(self) -> str:
        """Generate unique identifier for this repository."""
        return f"{self.apiVersion}/{self.kind}/{self.metadata.namespace}/{self.metadata.name}"


class V1DockerRepositoryEntityDefinition(
    EntityDefinition[V1DockerRepositoryEntitySpec]
):
    """Entity definition for Docker repositories."""

    group: str = "entities.devgraph.ai"
    kind: str = "DockerRepository"
    list_kind: str = "DockerRepositoryList"
    plural: str = "dockerrepositories"
    singular: str = "dockerrepository"
    name: str = "v1"
    spec_class: type = V1DockerRepositoryEntitySpec
    display_name: str = "Docker Repository"
    characteristics: list = ["container", "artifact collection"]
    description: str = "A container image repository within a Docker registry"
