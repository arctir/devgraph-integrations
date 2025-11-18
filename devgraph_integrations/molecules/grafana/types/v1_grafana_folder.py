"""Grafana Folder entity type definition."""

from devgraph_integrations.core.entity import EntityDefinitionSpec
from devgraph_integrations.types.entities import EntityMetadata, Entity


V1GrafanaFolderEntityDefinition = EntityDefinitionSpec(
    group="observability.devgraph.ai",
    version="v1",
    kind="GrafanaFolder",
    plural="grafanafolders",
    spec_schema={
        "type": "object",
        "properties": {
            "uid": {
                "type": "string",
                "description": "Unique folder identifier",
            },
            "id": {
                "type": "integer",
                "description": "Numeric folder ID",
            },
            "title": {
                "type": "string",
                "description": "Folder title",
            },
            "url": {
                "type": "string",
                "description": "Full URL to the folder",
            },
        },
        "required": ["uid", "title"],
    },
)


class V1GrafanaFolderEntity(Entity):
    """Entity representing a Grafana folder."""

    metadata: EntityMetadata
    spec: dict

    @property
    def apiVersion(self) -> str:
        return "observability.devgraph.ai/v1"

    @property
    def kind(self) -> str:
        return "GrafanaFolder"
