from devgraph_integrations.types.entities import EntityRelation, FieldSelectedEntityRelation


class ProjectBelongsToInstanceRelation(EntityRelation):
    """Relation linking Argo projects to their parent Argo instance."""

    relation: str = "BELONGS_TO"


class ApplicationBelongsToProjectRelation(EntityRelation):
    """Relation linking Argo applications to their parent Argo project."""

    relation: str = "BELONGS_TO"


class ApplicationUsesRepositoryRelation(FieldSelectedEntityRelation):
    """Relation linking Argo applications to GitHub repositories using field selectors."""

    relation: str = "USES"
