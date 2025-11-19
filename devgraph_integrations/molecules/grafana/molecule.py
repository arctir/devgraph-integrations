"""Grafana molecule facade."""

from typing import Any, Dict, Optional, Type

from devgraph_integrations.core.molecule import Molecule


class GrafanaMolecule(Molecule):
    """Grafana molecule providing discovery capabilities."""

    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "name": "grafana",
            "display_name": "Grafana",
            "description": "Discover Grafana dashboards, datasources, folders, and instances",
            "logo": {"reactIcons": "SiGrafana"},
            "homepage_url": "https://grafana.com",
            "docs_url": "https://grafana.com/docs/grafana/latest/",
            "capabilities": ["discovery"],
            "entity_types": [
                "GrafanaInstance",
                "GrafanaDashboard",
                "GrafanaDatasource",
                "GrafanaFolder",
            ],
            "relation_types": [
                "GrafanaDashboardBelongsToFolder",
                "GrafanaDatasourceBelongsToInstance",
            ],
            "requires_auth": True,
            "auth_types": ["api_token", "basic_auth"],
            "min_framework_version": "0.1.0",
        }

    @staticmethod
    def get_discovery_provider() -> Optional[Type[Any]]:
        from .provider import GrafanaProvider

        return GrafanaProvider
