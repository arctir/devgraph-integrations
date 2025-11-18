"""Grafana Instance entity type definition."""

from devgraph_integrations.core.entity import EntityDefinitionSpec
from devgraph_integrations.types.entities import EntityMetadata, Entity


V1GrafanaInstanceEntityDefinition = EntityDefinitionSpec(
    group="observability.devgraph.ai",
    version="v1",
    kind="GrafanaInstance",
    plural="grafanainstances",
    spec_schema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Base URL of the Grafana instance",
            },
            "version": {
                "type": "string",
                "description": "Grafana version",
            },
            "org_id": {
                "type": "integer",
                "description": "Organization ID",
            },
        },
        "required": ["url"],
    },
)


class V1GrafanaInstanceEntity(Entity):
    """Entity representing a Grafana instance."""

    metadata: EntityMetadata
    spec: dict

    @property
    def apiVersion(self) -> str:
        return "observability.devgraph.ai/v1"

    @property
    def kind(self) -> str:
        return "GrafanaInstance"
