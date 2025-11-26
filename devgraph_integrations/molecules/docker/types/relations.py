"""Docker registry relationships.

This module defines relationships between Docker registry entities.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
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


class BuiltFromSpec(BaseModel):
    """Spec for BUILT_FROM relations between Docker and source repositories."""

    dockerfile_path: Optional[str] = Field(None, description="Path to the Dockerfile in the source repository")
    build_context: Optional[str] = Field(None, description="Build context directory path")
    build_args: Optional[Dict[str, str]] = Field(default_factory=dict, description="Build arguments used during image build")
    workflow_file: Optional[str] = Field(None, description="CI/CD workflow file that builds the image (e.g., .github/workflows/docker-build.yml)")
    source_commit: Optional[str] = Field(None, description="Git commit SHA that the Docker image was built from")
    source_branch: Optional[str] = Field(None, description="Git branch that the Docker image was built from")


class BuildsSpec(BaseModel):
    """Spec for BUILDS relations from source repositories to Docker repositories."""

    dockerfile_path: Optional[str] = Field(None, description="Path to the Dockerfile in the source repository")
    build_context: Optional[str] = Field(None, description="Build context directory path")
    build_args: Optional[Dict[str, str]] = Field(default_factory=dict, description="Build arguments used during image build")
    workflow_file: Optional[str] = Field(None, description="CI/CD workflow file that builds the image")
    target_tags: Optional[list[str]] = Field(default_factory=list, description="Docker image tags produced by this build")
    build_on_push: Optional[bool] = Field(None, description="Whether the image is built on every push")


class DockerRepositoryBuiltFromGithubRepositoryRelation(EntityRelation):
    """Relationship indicating a Docker repository was built from a GitHub source repository.

    Example usage:
        relation = DockerRepositoryBuiltFromGithubRepositoryRelation(
            source=docker_repo.reference,
            target=github_repo.reference,
            spec=BuiltFromSpec(
                dockerfile_path="Dockerfile",
                build_context=".",
                workflow_file=".github/workflows/docker-build.yml"
            )
        )
    """

    relation: str = "BUILT_FROM"
    spec: BuiltFromSpec = Field(default_factory=BuiltFromSpec)

    def __init__(self, **data):
        # Convert dict spec to typed BuiltFromSpec
        if 'spec' in data and not isinstance(data['spec'], BuiltFromSpec):
            if isinstance(data['spec'], dict):
                data['spec'] = BuiltFromSpec(**data['spec'])
        super().__init__(**data)


class GithubRepositoryBuildsDockerRepositoryRelation(EntityRelation):
    """Relationship indicating a GitHub source repository builds a Docker repository.

    Example usage:
        relation = GithubRepositoryBuildsDockerRepositoryRelation(
            source=github_repo.reference,
            target=docker_repo.reference,
            spec=BuildsSpec(
                dockerfile_path="Dockerfile",
                workflow_file=".github/workflows/docker-build.yml",
                target_tags=["latest", "v1.0.0"]
            )
        )
    """

    relation: str = "BUILDS"
    spec: BuildsSpec = Field(default_factory=BuildsSpec)

    def __init__(self, **data):
        # Convert dict spec to typed BuildsSpec
        if 'spec' in data and not isinstance(data['spec'], dict):
            if isinstance(data['spec'], BuildsSpec):
                # Already typed, pass through
                pass
        elif 'spec' in data and isinstance(data['spec'], dict):
            data['spec'] = BuildsSpec(**data['spec'])
        super().__init__(**data)
