"""Relation definitions for GitLab entities."""

from devgraph_integrations.types.entities import EntityRelation


class GitlabProjectHostedByRelation(EntityRelation):
    """Relation indicating a GitLab project is hosted by a GitLab hosting service."""

    relation: str = "HOSTED_BY"
