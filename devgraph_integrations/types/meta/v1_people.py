"""People meta entity types.

This module defines Person and Team meta entity types, which represent
human entities and organizational structures within the Devgraph system.

These types serve as base types for users, developers, operators, teams,
and organizational units across different providers.
"""
from typing import Optional, Literal
from enum import Enum

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class TeamType(str, Enum):
    """Types of teams."""

    ENGINEERING = "engineering"
    PRODUCT = "product"
    DESIGN = "design"
    QA = "qa"
    DEVOPS = "devops"
    SRE = "sre"
    SECURITY = "security"
    DATA = "data"
    PLATFORM = "platform"
    INFRASTRUCTURE = "infrastructure"
    MANAGEMENT = "management"
    ORGANIZATION = "organization"
    OTHER = "other"


class V1PersonEntitySpec(EntitySpec):
    """Specification for person entities.

    Defines common fields for any person/user that can be tracked
    in the Devgraph system. Relationships (manager, teams, etc.) and
    professional context (roles, title, department) should be inferred
    from graph relations rather than stored as attributes.

    Attributes:
        display_name: Full display name
        email: Primary email address
        username: Primary username/handle
        github_username: GitHub username
        slack_user_id: Slack user ID
    """

    # Core identification
    display_name: str
    email: Optional[str] = None
    username: Optional[str] = None

    # External identities
    github_username: Optional[str] = None
    slack_user_id: Optional[str] = None

    # Note: All relationships are managed through graph relations:
    # - manager/direct_reports -> PersonReportsToPersonRelation / PersonManagesPersonRelation
    # - teams -> PersonMemberOfTeamRelation
    # - roles, title, department -> Should be inferred from team membership and relations


class V1TeamEntitySpec(EntitySpec):
    """Specification for team entities.

    Defines common fields for any team/group that can be tracked
    in the Devgraph system. Relationships (members, parent teams, ownership)
    are managed through graph relations, not as spec fields.

    Attributes:
        display_name: Full display name of the team
        team_type: Type of team
        description: Team description/purpose
        email: Team email address
        slack_channel: Slack channel
        status: Current status
    """

    # Core identification
    display_name: str
    team_type: Optional[TeamType] = TeamType.OTHER
    description: Optional[str] = None
    email: Optional[str] = None
    slack_channel: Optional[str] = None
    status: Optional[Literal["active", "inactive", "disbanded"]] = "active"

    # Note: All relationships are managed through graph relations:
    # - parent_team/child_teams -> Use TeamPartOfTeamRelation (PART_OF)
    # - members -> Use PersonMemberOfTeamRelation (MEMBER_OF)
    # - leads -> Use PersonLeadsTeamRelation (LEADS)
    # - owned resources -> Use TeamOwnsEntityRelation (OWNS)


class V1PersonEntityDefinition(EntityDefinition[V1PersonEntitySpec]):
    """Entity definition for persons."""

    group: str = "entities.devgraph.ai"
    kind: str = "Person"
    list_kind: str = "PersonList"
    plural: str = "people"
    singular: str = "person"
    name: str = "v1"
    spec_class: type = V1PersonEntitySpec
    display_name: str = "Person"
    characteristics: list = ["individual", "human"]
    description: str = "Meta type for individuals including developers, users, maintainers, and stakeholders"


class V1TeamEntityDefinition(EntityDefinition[V1TeamEntitySpec]):
    """Entity definition for teams."""

    group: str = "entities.devgraph.ai"
    kind: str = "Team"
    list_kind: str = "TeamList"
    plural: str = "teams"
    singular: str = "team"
    name: str = "v1"
    spec_class: type = V1TeamEntitySpec
    display_name: str = "Team"
    characteristics: list = ["group", "organization", "human"]
    description: str = "Meta type for groups of people including development teams, organizations, and departments"


class V1PersonEntity(Entity):
    """Person entity."""

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "Person"
    spec: V1PersonEntitySpec  # type: ignore[assignment]

    @property
    def primary_contact(self) -> str:
        """Get primary contact method."""
        return self.spec.email or self.spec.username or self.metadata.name


class V1TeamEntity(Entity):
    """Team entity."""

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "Team"
    spec: V1TeamEntitySpec  # type: ignore[assignment]

    @property
    def full_identifier(self) -> str:
        """Return full identifier including provider context."""
        if self.spec.team_provider and self.spec.team_identifier:
            return f"{self.spec.team_provider}:{self.spec.team_identifier}"
        return f"team:{self.metadata.name}"

    @property
    def is_active(self) -> bool:
        """Check if team is currently active."""
        return self.spec.status == "active"

    # Note: These properties were removed as they relied on relationship fields
    # that are now managed as graph relations. To get member counts, lead counts,
    # or ownership information, query the graph for relations:
    # - MEMBER_OF relations to this team
    # - LEADS relations to this team
    # - OWNS relations from this team
