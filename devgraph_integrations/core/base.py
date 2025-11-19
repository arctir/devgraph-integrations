from typing import Annotated, Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel, constr


class EntityDefinitionSpec(BaseModel):
    group: Annotated[str, constr(min_length=1)]
    kind: Annotated[str, constr(min_length=1)]
    list_kind: Annotated[str, constr(min_length=1)]
    plural: Annotated[str, constr(min_length=1)]
    singular: Annotated[str, constr(min_length=1)]
    name: Annotated[str, constr(min_length=1)] = "v1"  # Default version name
    spec_class: Type[BaseModel]
    description: Annotated[
        str, constr(min_length=1)
    ]  # Description of what this entity type represents
    display_name: Optional[str] = (
        None  # Human-readable display name (e.g., "GitHub Repository")
    )
    characteristics: Optional[List[str]] = (
        None  # Optional list of characteristics (e.g., ["source_code", "git"])
    )

    def to_dict(self) -> dict:
        result = {
            "group": self.group,
            "kind": self.kind,
            "list_kind": self.list_kind,
            "plural": self.plural,
            "singular": self.singular,
            "name": self.name,
            "spec": self.spec_class.model_json_schema(),
            "description": self.description,
        }
        if self.display_name:
            result["display_name"] = self.display_name
        if self.characteristics:
            result["characteristics"] = self.characteristics
        return result


class EntityVersionSpec(BaseModel):
    name: Annotated[str, constr(min_length=1)]
    spec_class: Type[BaseModel]

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "spec": self.spec_class.model_json_schema()}


T = TypeVar("T", bound=BaseModel)


class EntityDefinition(EntityDefinitionSpec, Generic[T]):
    spec_class: Type[T]


class EntityVersion(EntityVersionSpec):
    pass
