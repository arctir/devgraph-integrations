"""Meta entity relationship types.

This module defines relationship types for Person and Team meta entities,
representing organizational structure, team membership, reporting lines,
and ownership relationships.
"""

from devgraph_integrations.types.entities import EntityRelation


class PersonMemberOfTeamRelation(EntityRelation):
    """Relationship indicating a Person is a member of a Team.

    Source: Person entity
    Target: Team entity
    """

    relation: str = "MEMBER_OF"


class PersonLeadsTeamRelation(EntityRelation):
    """Relationship indicating a Person leads/manages a Team.

    Source: Person entity
    Target: Team entity
    """

    relation: str = "LEADS"


class PersonReportsToPersonRelation(EntityRelation):
    """Relationship indicating a Person reports to another Person.

    Source: Person entity (direct report)
    Target: Person entity (manager)
    """

    relation: str = "REPORTS_TO"


class PersonManagesPersonRelation(EntityRelation):
    """Relationship indicating a Person manages another Person.

    Source: Person entity (manager)
    Target: Person entity (direct report)

    This is the inverse of REPORTS_TO.
    """

    relation: str = "MANAGES"


class TeamPartOfTeamRelation(EntityRelation):
    """Relationship indicating a Team is part of a parent Team.

    Source: Team entity (child)
    Target: Team entity (parent)
    """

    relation: str = "PART_OF"


class TeamOwnsEntityRelation(EntityRelation):
    """Relationship indicating a Team owns an entity.

    Source: Team entity
    Target: Any entity (SoftwareComponent, Infrastructure, etc.)

    This is a generic ownership relation that can be used for any
    entity type that a team is responsible for.
    """

    relation: str = "OWNS"
