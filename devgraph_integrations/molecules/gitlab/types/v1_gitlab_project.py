"""GitLab project entity definitions.

This module defines the entity types for representing GitLab projects
in the Devgraph system, including specifications, definitions, and entity classes.
"""

from typing import Annotated, List, Optional

from pydantic import constr

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1GitlabProjectEntitySpec(EntitySpec):
    """Specification for GitLab project ent

    Attributes:
        group: GitLab group/namespace path (required)
        name: Project name (required)
        project_id: Project identifier in 'group/project_name' format (required)
        url: Project URL
        description: Project description (optional)
        labels: List of labels/tags (optional)
        languages: Dictionary of languages used in the project with byte counts (optional)
        visibility: Project visibility level (private, internal, public)
    """

    group: Annotated[str, constr(min_length=1)]
    name: Annotated[str, constr(min_length=1)]
    project_id: Annotated[str, constr(min_length=1)]
    url: str
    description: Optional[str] = None
    labels: Optional[List[str]] = None
    languages: Optional[dict[str, float]] = None
    visibility: Optional[str] = None


class V1GitlabProjectEntityDefinition(EntityDefinition[V1GitlabProjectEntitySpec]):
    """Entity definition for GitLab projects.

    Defines metadata about the GitLab project entity type including
    API version, kind, and pluralization rules.
    """

    group: str = "entities.devgraph.ai"
    kind: str = "GitlabProject"
    list_kind: str = "GitlabProjectList"
    plural: str = "gitlabprojects"
    singular: str = "gitlabproject"
    name: str = "v1"
    spec_class: type = V1GitlabProjectEntitySpec
    display_name: str = "GitLab Project"
    characteristics: list = ["source code", "git", "version control", "ci/cd"]
    description: str = (
        "A GitLab project containing source code, documentation, and CI/CD pipelines"
    )


class V1GitlabProjectEntity(Entity):
    """GitLab project entity implementation.

    Represents a GitLab project as a Devgraph entity with methods
    for accessing project properties and metadata.
    """

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "GitlabProject"
    spec: V1GitlabProjectEntitySpec  # type: ignore[assignment]

    @property
    def plural(self) -> str:
        """Return the plural form of the entity kind.

        Returns:
            The plural form 'gitlabprojects'
        """
        return "gitlabprojects"

    @property
    def full_name(self) -> str:
        """Return the full project name.

        Returns:
            Full project name in 'group/name' format
        """
        return f"{self.spec.group}/{self.spec.name}"
