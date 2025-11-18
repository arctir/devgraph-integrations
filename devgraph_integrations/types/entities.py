from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid

import inflect
from pydantic import BaseModel, computed_field, Field


class EntityReference(BaseModel):
    apiVersion: str
    kind: str
    name: str
    namespace: str = "default"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def id(self) -> str:
        """Return a unique identifier for the entity."""
        return f"{self.apiVersion}/{self.kind}/{self.namespace}/{self.name}"


class EntityRelation(BaseModel):
    namespace: str = "default"
    relation: str
    source: EntityReference
    target: EntityReference

    def to_dict(self) -> dict:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class EntityTypeSelector(BaseModel):
    """Specifies entity type constraints for field selection."""

    api_version: Optional[str] = None  # e.g., "github.providers.devgraph.ai/v1"
    kind: Optional[str] = None  # e.g., "GitHubRepository"

    def matches(self, entity_ref: EntityReference) -> bool:
        """Check if an entity reference matches this type selector."""
        if self.api_version and entity_ref.apiVersion != self.api_version:
            return False
        if self.kind and entity_ref.kind != self.kind:
            return False
        return True


class FieldSelector(BaseModel):
    """Represents a field selector for querying entities with type constraints."""

    field: str
    value: str
    entity_type: Optional[EntityTypeSelector] = None

    @classmethod
    def from_string(
        cls, selector: str, api_version: Optional[str] = None, kind: Optional[str] = None
    ) -> "FieldSelector":
        """Create a FieldSelector from a string like 'spec.owner=team-a' with optional entity type."""
        if "=" not in selector:
            raise ValueError(
                f"Invalid selector format: {selector}. Expected 'field=value'"
            )
        field, value = selector.split("=", 1)
        entity_type = None
        if api_version or kind:
            entity_type = EntityTypeSelector(api_version=api_version, kind=kind)
        return cls(field=field.strip(), value=value.strip(), entity_type=entity_type)

    def to_string(self) -> str:
        """Convert back to string format."""
        return f"{self.field}={self.value}"


class FieldSelectedEntityRelation(BaseModel):
    """A relation that uses field selectors to dynamically find source/target entities."""

    namespace: str = "default"
    relation: str
    source_selector: Optional[FieldSelector] = None
    target_selector: Optional[FieldSelector] = None
    source: Optional[EntityReference] = None
    target: Optional[EntityReference] = None
    properties: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def with_source_selector(
        cls,
        relation: str,
        source_selector: str,
        target: EntityReference,
        namespace: str = "default",
        properties: Optional[Dict[str, Any]] = None,
        source_api_version: Optional[str] = None,
        source_kind: Optional[str] = None,
    ) -> "FieldSelectedEntityRelation":
        """Create a relation with a source selector and explicit target."""
        return cls(
            namespace=namespace,
            relation=relation,
            source_selector=FieldSelector.from_string(
                source_selector, api_version=source_api_version, kind=source_kind
            ),
            target=target,
            properties=properties or {},
        )

    @classmethod
    def with_target_selector(
        cls,
        relation: str,
        source: EntityReference,
        target_selector: str,
        namespace: str = "default",
        properties: Optional[Dict[str, Any]] = None,
        target_api_version: Optional[str] = None,
        target_kind: Optional[str] = None,
    ) -> "FieldSelectedEntityRelation":
        """Create a relation with explicit source and a target selector."""
        return cls(
            namespace=namespace,
            relation=relation,
            source=source,
            target_selector=FieldSelector.from_string(
                target_selector, api_version=target_api_version, kind=target_kind
            ),
            properties=properties or {},
        )

    @classmethod
    def with_both_selectors(
        cls,
        relation: str,
        source_selector: str,
        target_selector: str,
        namespace: str = "default",
        properties: Optional[Dict[str, Any]] = None,
        source_api_version: Optional[str] = None,
        source_kind: Optional[str] = None,
        target_api_version: Optional[str] = None,
        target_kind: Optional[str] = None,
    ) -> "FieldSelectedEntityRelation":
        """Create a relation with both source and target selectors."""
        return cls(
            namespace=namespace,
            relation=relation,
            source_selector=FieldSelector.from_string(
                source_selector, api_version=source_api_version, kind=source_kind
            ),
            target_selector=FieldSelector.from_string(
                target_selector, api_version=target_api_version, kind=target_kind
            ),
            properties=properties or {},
        )

    def to_dict(self) -> dict:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class EntitySpec(BaseModel):
    def to_dict(self) -> dict:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)

    def get_relation_fields(self) -> List[str]:
        """
        Returns a list of field names in the class whose type annotations are for EntityRelation.

        Returns:
            List[str]: A list of field names whose type annotations match the specified type.
        """
        return [
            field_name
            for field_name, field_info in type(self).model_fields.items()
            if field_info.annotation == EntityRelation
            or field_info.annotation == List[EntityRelation]
        ]


class EntityStatus(BaseModel):
    """Status information for an entity including lifecycle tracking."""

    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the entity was last updated",
    )
    is_orphan: bool = Field(
        default=False,
        description="Whether this entity is orphaned (definition no longer exists)",
    )
    last_seen: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the entity was last seen during discovery",
    )
    discovery_source: Optional[str] = Field(
        default=None,
        description="Name of the provider that last discovered/updated this entity",
    )
    generation: int = Field(
        default=1, description="Generation number, incremented on each update"
    )

    def mark_updated(self, source: Optional[str] = None) -> None:
        """Mark the entity as updated with current timestamp."""
        now = datetime.now(timezone.utc)
        self.last_updated = now
        self.last_seen = now
        self.generation += 1
        if source:
            self.discovery_source = source
        self.is_orphan = False  # Reset orphan status when updated

    def mark_orphan(self) -> None:
        """Mark the entity as orphaned."""
        self.is_orphan = True
        self.last_updated = datetime.now(timezone.utc)


class EntityMetadata(BaseModel):
    name: str
    namespace: str
    uid: str = Field(default_factory=lambda: str(uuid.uuid4()))  # Auto-generated UUID
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)


class Entity(BaseModel):
    apiVersion: str
    kind: str
    metadata: EntityMetadata
    spec: Dict[str, Any] = Field(default_factory=dict)
    status: EntityStatus = Field(default_factory=EntityStatus)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def id(self) -> str:
        """Return a unique identifier for the entity."""
        return f"{self.apiVersion}/{self.kind}/{self.metadata.namespace}/{self.metadata.name}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def plural(self) -> str:
        """Return the plural form of the kind."""
        p = inflect.engine()
        return p.plural(self.kind.lower())

    @computed_field  # type: ignore[prop-decorator]
    @property
    def group(self) -> str:
        """Return the group part of the apiVersion."""
        return self.apiVersion.split("/")[0] if "/" in self.apiVersion else ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def version(self) -> str:
        """Return the version part of the apiVersion."""
        return self.apiVersion.split("/")[1] if "/" in self.apiVersion else ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def name(self) -> str:
        """Return the name of the resource."""
        return self.metadata.name

    @computed_field  # type: ignore[prop-decorator]
    @property
    def namespace(self) -> str:
        """Return the namespace of the resource."""
        return self.metadata.namespace

    def mark_updated(self, source: Optional[str] = None) -> None:
        """Mark the entity as updated."""
        self.status.mark_updated(source)

    def mark_orphan(self) -> None:
        """Mark the entity as orphaned."""
        self.status.mark_orphan()

    def is_stale(self, max_age_hours: int = 24) -> bool:
        """Check if entity is stale based on last_seen timestamp."""
        if not self.status.last_seen:
            return True
        age = datetime.now(timezone.utc) - self.status.last_seen
        return age.total_seconds() > (max_age_hours * 3600)

    @property
    def is_orphan(self) -> bool:
        """Check if entity is orphaned."""
        return self.status.is_orphan

    @property
    def reference(self) -> EntityReference:
        """Return an entity reference."""
        return EntityReference(
            apiVersion=self.apiVersion,
            kind=self.kind,
            name=self.name,
            namespace=self.namespace,
        )

    def to_dict(self) -> dict:
        """Convert the entity to a dictionary."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class EntityResponse(Entity):
    # reference: "EntityReferenceResponse" = None
    pass


class EntityRelationCreateRequest(EntityRelation):
    pass


class EntityReferenceResponse(EntityReference):
    pass


class EntityRelationResponse(BaseModel):
    namespace: str = "default"
    relation: str
    source: EntityReferenceResponse
    target: EntityReferenceResponse

    def to_dict(self) -> dict:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class EntityWithRelationsResponse(BaseModel):
    """Response for a single entity with its related entities and relations."""

    entity: EntityResponse
    related_entities: List[EntityResponse] = []
    relations: List[EntityRelationResponse] = []


class EntityResultSetResponse(BaseModel):
    """Response for a set of entities with their relations (used for queries returning multiple entities)."""

    primary_entities: List[EntityResponse] = []
    related_entities: List[EntityResponse] = []
    relations: List[EntityRelationResponse] = []


class BulkEntityRelationCreateRequest(BaseModel):
    """Request model for creating multiple entity relations in bulk."""

    namespace: str = "default"
    relations: List[EntityRelation] = Field(
        ..., description="List of entity relations to create"
    )


class BulkEntityRelationResponse(BaseModel):
    """Response model for bulk entity relation creation."""

    namespace: str = "default"
    created_relations: List[EntityRelationResponse] = Field(
        default_factory=list, description="Successfully created relations"
    )
    failed_relations: List[dict] = Field(
        default_factory=list,
        description="Relations that failed to create with error details",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_requested(self) -> int:
        """Total number of relations requested for creation."""
        return len(self.created_relations) + len(self.failed_relations)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def success_count(self) -> int:
        """Number of successfully created relations."""
        return len(self.created_relations)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def failure_count(self) -> int:
        """Number of failed relation creations."""
        return len(self.failed_relations)
