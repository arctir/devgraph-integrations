"""Grafana molecule for Devgraph.

This module provides discovery and management of Grafana resources including
dashboards, datasources, folders, and alerts.
"""

from .config import GrafanaProviderConfig
from .provider import GrafanaProvider

__version__ = "1.0.0"
__molecule_metadata__ = {
    "version": __version__,
    "name": "grafana",
    "display_name": "Grafana",
    "description": "Discover Grafana dashboards, datasources, folders, and instances",
    "logo": {"reactIcons": "SiGrafana"},  # react-icons identifier (from react-icons/si)
    "homepage_url": "https://grafana.com",
    "docs_url": "https://grafana.com/docs/grafana/latest/",
    "capabilities": [
        "discovery",
    ],
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

__all__ = [
    "GrafanaProvider",
    "GrafanaProviderConfig",
    "__version__",
    "__molecule_metadata__",
]
