"""GitHub repository entity definitions.

This module defines the entity types for representing GitHub repositories
in the Devgraph system, including specifications, definitions, and entity classes.
"""

from typing import Annotated, List, Optional

from pydantic import constr

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1GithubRepositoryEntitySpec(EntitySpec):
    """A GitHub repository specifies the details of a repository hosted on GitHub.
    GitHub provides a platform for version control and collaboration, allowing
    developers to manage and share their code.

    Attributes:
        owner: GitHub owner name (organization or user) (required)
        name: Repository name (required)
        url: Repository URL
        description: Repository description (optional)
        labels: List of labels/tags (optional)
        languages: Dictionary of languages used in the repository with byte counts (optional)
    """

    owner: Annotated[str, constr(min_length=1)]
    name: Annotated[str, constr(min_length=1)]
    url: str
    description: Optional[str] = None
    labels: Optional[List[str]] = None
    languages: Optional[dict[str, int]] = None


class V1GithubRepositoryEntityDefinition(
    EntityDefinition[V1GithubRepositoryEntitySpec]
):
    """Entity definition for GitHub repositories.

    Defines metadata about the GitHub repository entity type including
    API version, kind, and pluralization rules.
    """

    group: str = "entities.devgraph.ai"
    kind: str = "GithubRepository"
    list_kind: str = "GithubRepositoryList"
    plural: str = "githubrepositories"
    singular: str = "githubrepository"
    name: str = "v1"
    spec_class: type = V1GithubRepositoryEntitySpec
    display_name: str = "GitHub Repository"
    characteristics: list = ["source code", "git", "version control"]
    description: str = (
        "A GitHub repository containing source code, documentation, and project files"
    )


class V1GithubRepositoryEntity(Entity):
    """GitHub repository entity implementation.

    Represents a GitHub repository as a Devgraph entity with methods
    for accessing repository properties and metadata.
    """

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "GithubRepository"
    spec: V1GithubRepositoryEntitySpec  # type: ignore[assignment]

    @property
    def plural(self) -> str:
        """Return the plural form of the entity kind.

        Returns:
            The plural form 'githubrepositories'
        """
        """Return the plural form of the kind."""
        return "githubrepositories"

    @property
    def slug(self) -> str:
        """Return the repository slug.

        Returns:
            Repository slug in 'owner/name' format
        """
        return f"{self.spec.owner}/{self.spec.name}"
