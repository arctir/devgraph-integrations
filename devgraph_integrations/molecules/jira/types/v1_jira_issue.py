"""Jira issue entity definitions.

This module defines the entity types for representing Jira issues
in the Devgraph system.
"""

from typing import Annotated, List, Optional

from pydantic import constr

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1JiraIssueEntitySpec(EntitySpec):
    """A Jira issue represents a work item tracked in Jira.

    Attributes:
        key: Issue key (e.g., "PROJ-123") (required)
        project_key: Project key the issue belongs to (required)
        summary: Issue summary/title (required)
        issue_type: Type of issue (Task, Bug, Story, Epic, etc.)
        status: Current status of the issue
        priority: Issue priority
        assignee: Username assigned to the issue (optional)
        reporter: Username who created the issue (optional)
        description: Issue description (optional)
        labels: List of labels (optional)
        url: Direct URL to the issue
        created: ISO timestamp when issue was created
        updated: ISO timestamp when issue was last updated
    """

    key: Annotated[str, constr(min_length=1)]
    project_key: Annotated[str, constr(min_length=1)]
    summary: Annotated[str, constr(min_length=1)]
    issue_type: str
    status: str
    priority: Optional[str] = None
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    description: Optional[str] = None
    labels: Optional[List[str]] = None
    url: str
    created: str
    updated: str


class V1JiraIssueEntityDefinition(EntityDefinition[V1JiraIssueEntitySpec]):
    """Entity definition for Jira issues."""

    group: str = "entities.devgraph.ai"
    kind: str = "JiraIssue"
    list_kind: str = "JiraIssueList"
    plural: str = "jiraissues"
    singular: str = "jiraissue"
    name: str = "v1"
    spec_class: type = V1JiraIssueEntitySpec
    display_name: str = "Jira Issue"
    characteristics: list = ["work item", "task tracking", "issue tracking"]
    description: str = "A Jira issue representing a work item, bug, task, or story"


class V1JiraIssueEntity(Entity):
    """Jira issue entity implementation."""

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "JiraIssue"
    spec: V1JiraIssueEntitySpec  # type: ignore[assignment]

    @property
    def plural(self) -> str:
        """Return the plural form of the entity kind."""
        return "jiraissues"
