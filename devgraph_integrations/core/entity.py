import re
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, PrivateAttr, field_validator, model_validator
from pydantic import ConfigDict


class EntityMetadata(BaseModel):
    name: str = Field(..., description="Resource name, must follow DNS-1123 subdomain")
    namespace: str = Field(default="default", description="Kubernetes namespace")
    labels: Optional[Dict[str, str]] = Field(
        default=None, description="Key-value pairs for labels"
    )
    annotations: Optional[Dict[str, str]] = Field(
        default=None, description="Key-value pairs for annotations"
    )

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        """Ensure name follows DNS-1123 subdomain (Kubernetes naming convention)."""
        pattern = r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$"
        if not re.match(pattern, v) or len(v) > 253:
            raise ValueError(
                "Name must be a valid DNS-1123 subdomain (lowercase, max 253 chars)"
            )
        return v

    @field_validator("namespace")
    def validate_namespace(cls, v: str) -> str:
        """Ensure namespace follows DNS-1123 subdomain."""
        pattern = r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$"
        if not re.match(pattern, v) or len(v) > 63:
            raise ValueError(
                "Namespace must be a valid DNS-1123 subdomain (lowercase, max 63 chars)"
            )
        return v


class EntityResource(BaseModel):
    _plural: Optional[str] = PrivateAttr(default=None)
    _subtype: Optional[str] = PrivateAttr(default=None)

    apiVersion: str = Field(
        default="v1", description="API version, e.g., 'v1' or 'apps/v1'"
    )
    kind: str = Field(..., description="Resource kind, e.g., 'Pod', 'Deployment'")
    metadata: EntityMetadata = Field(
        default_factory=EntityMetadata, description="Resource metadata"  # type: ignore[arg-type]
    )
    spec: Optional[Dict] = Field(default=None, description="Resource specification")

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("apiVersion")
    def validate_api_version(cls, v: str) -> str:
        """Ensure apiVersion follows Kubernetes group/version format."""
        pattern = r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(/[a-z0-9]+)?$"
        if not re.match(pattern, v):
            raise ValueError(
                "apiVersion must be in the format 'group/version' or 'version' (e.g., 'v1', 'apps/v1')"
            )
        return v

    @field_validator("kind")
    def validate_kind(cls, v: str) -> str:
        """Ensure kind is a valid Kubernetes resource type."""
        if not v or not v[0].isupper():
            raise ValueError(
                "Kind must be non-empty and start with an uppercase letter"
            )
        return v

    @model_validator(mode="after")
    def validate_metadata(self) -> "EntityResource":
        """Validate metadata for the resource."""
        if self._subtype:
            if self.metadata.annotations is None:
                self.metadata.annotations = {"devgraph.ai/subtype": self._subtype}
            else:
                self.metadata.annotations["devgraph.ai/subtype"] = self._subtype
        return self

    @property
    def plural(self) -> Optional[str]:
        """Return the plural form of the resource kind."""
        return self._plural

    @property
    def subtype(self) -> Optional[str]:
        """Return the subtype of the resource, if defined."""
        return self._subtype

    @property
    def group(self) -> str:
        """Return the group part of the apiVersion."""
        return self.apiVersion.split("/")[0] if "/" in self.apiVersion else ""

    @property
    def version(self) -> str:
        """Return the version part of the apiVersion."""
        return self.apiVersion.split("/")[1] if "/" in self.apiVersion else ""

    @property
    def gvk(self) -> str:
        """Return the GroupVersionKind string."""
        return f"{self.group}/{self.version}/{self.kind}"

    @property
    def namespace(self) -> str:
        """Return the namespace of the resource."""
        return self.metadata.namespace if self.metadata else "default"


class EntityDefinitionVersion(BaseModel):
    name: str = Field(..., description="Version name (e.g., v1, v2alpha1)")
    version_schema: Dict = Field(
        ...,
        description="OpenAPI schema for the entity definition version",
        alias="schema",
    )

    model_config = ConfigDict(
        validate_by_name=True,
        arbitrary_types_allowed=True,
    )


class EntityDefinitionSpec(BaseModel):
    group: str = Field(..., description="API group (e.g., myapi.example.com)")
    versions: List[EntityDefinitionVersion] = []


class EntityDefinition(EntityResource):
    _plural: str = "entitydefinitions"
    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "EntityDefinition"
    spec: EntityDefinitionSpec = Field(  # type: ignore[assignment]
        description="Specification for the entity definition",
    )


# class EntityDefinitionResource(BaseModel):
#     _plural: str = PrivateAttr(default=None)
#     _subtype: str = PrivateAttr(default=None)

#     apiVersion: str = Field(
#         default="v1", description="API version, e.g., 'v1' or 'apps/v1'"
#     )
#     kind: str = Field(..., description="Resource kind, e.g., 'Pod', 'Deployment'")
#     metadata: EntityMetadata = Field(
#         default_factory=EntityMetadata, description="Resource metadata"
#     )
#     spec: Optional[Dict] = Field(default=None, description="Resource specification")
