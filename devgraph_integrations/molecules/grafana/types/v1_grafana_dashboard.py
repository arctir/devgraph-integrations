"""Grafana Dashboard entity type definition."""

from devgraph_integrations.core.entity import EntityDefinitionSpec
from devgraph_integrations.types.entities import Entity, EntityMetadata

V1GrafanaDashboardEntityDefinition = EntityDefinitionSpec(
    group="observability.devgraph.ai",
    version="v1",
    kind="GrafanaDashboard",
    plural="grafanadashboards",
    spec_schema={
        "type": "object",
        "properties": {
            "uid": {
                "type": "string",
                "description": "Unique dashboard identifier",
            },
            "id": {
                "type": "integer",
                "description": "Numeric dashboard ID",
            },
            "title": {
                "type": "string",
                "description": "Dashboard title",
            },
            "url": {
                "type": "string",
                "description": "Full URL to the dashboard",
            },
            "folder_id": {
                "type": ["integer", "null"],
                "description": "ID of the folder containing this dashboard",
            },
            "folder_uid": {
                "type": ["string", "null"],
                "description": "UID of the folder containing this dashboard",
            },
            "folder_title": {
                "type": ["string", "null"],
                "description": "Title of the folder containing this dashboard",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Dashboard tags",
            },
            "is_starred": {
                "type": "boolean",
                "description": "Whether the dashboard is starred",
            },
        },
        "required": ["uid", "title"],
    },
)


class V1GrafanaDashboardEntity(Entity):
    """Entity representing a Grafana dashboard."""

    metadata: EntityMetadata
    spec: dict

    @property
    def apiVersion(self) -> str:
        return "observability.devgraph.ai/v1"

    @property
    def kind(self) -> str:
        return "GrafanaDashboard"
