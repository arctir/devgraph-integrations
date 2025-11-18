"""Jira project entity definitions.

This module defines the entity types for representing Jira projects
in the Devgraph system.
"""

from typing import Annotated, Optional

from pydantic import constr

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1JiraProjectEntitySpec(EntitySpec):
    """A Jira project represents a collection of issues organized together.

    Attributes:
        key: Project key (e.g., "PROJ") (required)
        name: Project name (required)
        description: Project description (optional)
        lead: Project lead username (optional)
        url: Direct URL to the project
        jira_instance: Base URL of the Jira instance
    """

    key: Annotated[str, constr(min_length=1)]
    name: Annotated[str, constr(min_length=1)]
    description: Optional[str] = None
    lead: Optional[str] = None
    url: str
    jira_instance: str


class V1JiraProjectEntityDefinition(EntityDefinition[V1JiraProjectEntitySpec]):
    """Entity definition for Jira projects."""

    group: str = "entities.devgraph.ai"
    kind: str = "JiraProject"
    list_kind: str = "JiraProjectList"
    plural: str = "jiraprojects"
    singular: str = "jiraproject"
    name: str = "v1"
    spec_class: type = V1JiraProjectEntitySpec
    display_name: str = "Jira Project"
    characteristics: list = ["project management", "issue tracking"]
    description: str = "A Jira project containing issues and work items"


class V1JiraProjectEntity(Entity):
    """Jira project entity implementation."""

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "JiraProject"
    spec: V1JiraProjectEntitySpec  # type: ignore[assignment]

    @property
    def plural(self) -> str:
        """Return the plural form of the entity kind."""
        return "jiraprojects"
