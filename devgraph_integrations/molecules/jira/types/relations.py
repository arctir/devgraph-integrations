"""Jira relationship definitions.

This module defines the relationships between Jira entities.
"""

from devgraph_integrations.types.entities import Relation


class JiraIssueInProjectRelation(Relation):
    """Relationship: Jira Issue belongs to Jira Project.

    Represents the containment relationship where an issue belongs to a project.
    """

    relation_type: str = "in_project"
    from_entity_kind: str = "JiraIssue"
    to_entity_kind: str = "JiraProject"
    display_name: str = "In Project"
    description: str = "Issue belongs to a Jira project"


class JiraIssueAssignedToRelation(Relation):
    """Relationship: Jira Issue assigned to User.

    Represents the assignment relationship where an issue is assigned to a user.
    """

    relation_type: str = "assigned_to"
    from_entity_kind: str = "JiraIssue"
    to_entity_kind: str = "User"
    display_name: str = "Assigned To"
    description: str = "Issue is assigned to a user"


class JiraIssueBlocksRelation(Relation):
    """Relationship: Jira Issue blocks another Issue.

    Represents the blocking relationship between issues.
    """

    relation_type: str = "blocks"
    from_entity_kind: str = "JiraIssue"
    to_entity_kind: str = "JiraIssue"
    display_name: str = "Blocks"
    description: str = "Issue blocks another issue from being completed"


class JiraIssueRelatedToRelation(Relation):
    """Relationship: Jira Issue related to another entity.

    Generic relationship for linking issues to other entities like repositories, services, etc.
    """

    relation_type: str = "related_to"
    from_entity_kind: str = "JiraIssue"
    to_entity_kind: str = "*"  # Can relate to any entity type
    display_name: str = "Related To"
    description: str = "Issue is related to another entity"
