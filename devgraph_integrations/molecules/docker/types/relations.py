"""Docker registry relationships.

This module defines relationships between Docker registry entities.
"""

from devgraph_integrations.types.entities import EntityRelation


class DockerRepositoryBelongsToRegistryRelation(EntityRelation):
    """Relationship indicating a Docker repository belongs to a registry."""

    relation: str = "BELONGS_TO"


class DockerImageBelongsToRepositoryRelation(EntityRelation):
    """Relationship indicating a Docker image belongs to a repository."""

    relation: str = "BELONGS_TO"


class DockerImageUsesManifestRelation(EntityRelation):
    """Relationship indicating a Docker image uses a specific manifest."""

    relation: str = "USES"


class DockerManifestBelongsToRepositoryRelation(EntityRelation):
    """Relationship indicating a Docker manifest belongs to a repository."""

    relation: str = "BELONGS_TO"


class DockerRepositoryBuiltFromGithubRepositoryRelation(EntityRelation):
    """Relationship indicating a Docker repository was built from a GitHub source repository."""

    relation: str = "BUILT_FROM"


class GithubRepositoryBuildsDockerRepositoryRelation(EntityRelation):
    """Relationship indicating a GitHub source repository builds a Docker repository."""

    relation: str = "BUILDS"
