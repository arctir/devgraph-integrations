"""Grafana Datasource entity type definition."""

from devgraph_integrations.core.entity import EntityDefinitionSpec
from devgraph_integrations.types.entities import EntityMetadata, Entity


V1GrafanaDatasourceEntityDefinition = EntityDefinitionSpec(
    group="observability.devgraph.ai",
    version="v1",
    kind="GrafanaDatasource",
    plural="grafanadatasources",
    spec_schema={
        "type": "object",
        "properties": {
            "uid": {
                "type": "string",
                "description": "Unique datasource identifier",
            },
            "id": {
                "type": "integer",
                "description": "Numeric datasource ID",
            },
            "name": {
                "type": "string",
                "description": "Datasource name",
            },
            "type": {
                "type": "string",
                "description": "Datasource type (e.g., prometheus, loki, elasticsearch)",
            },
            "url": {
                "type": ["string", "null"],
                "description": "Datasource URL",
            },
            "is_default": {
                "type": "boolean",
                "description": "Whether this is the default datasource",
            },
            "json_data": {
                "type": "object",
                "description": "Additional datasource configuration",
            },
        },
        "required": ["uid", "name", "type"],
    },
)


class V1GrafanaDatasourceEntity(Entity):
    """Entity representing a Grafana datasource."""

    metadata: EntityMetadata
    spec: dict

    @property
    def apiVersion(self) -> str:
        return "observability.devgraph.ai/v1"

    @property
    def kind(self) -> str:
        return "GrafanaDatasource"
