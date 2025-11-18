"""Configuration models for Grafana provider.

This module defines the configuration classes used to configure the Grafana
provider for discovering dashboards, datasources, and other resources.
"""
from pydantic import BaseModel, Field

from devgraph_integrations.config.base import SensitiveBaseModel
from devgraph_integrations.molecules.base.config import MoleculeProviderConfig


class GrafanaSelectorConfig(BaseModel):
    """Configuration for selecting Grafana resources.

    Defines criteria for filtering dashboards and other resources.

    Attributes:
        tags: List of dashboard tags to filter by (optional)
        folder_ids: List of folder IDs to include (optional, empty = all folders)
        dashboard_uids: List of specific dashboard UIDs to discover (optional)
    """

    tags: list[str] = Field(default_factory=list)
    folder_ids: list[int] = Field(default_factory=list)
    dashboard_uids: list[str] = Field(default_factory=list)


class GrafanaProviderConfig(MoleculeProviderConfig, SensitiveBaseModel):
    """Main configuration for Grafana provider.

    Contains all settings needed to connect to Grafana API and configure
    resource discovery behavior.

    Attributes:
        base_url: Base URL for Grafana instance (e.g., https://grafana.example.com)
        api_key: Grafana API key or service account token for authentication
        org_id: Grafana organization ID (defaults to 1 for default org)
        discover_dashboards: Enable dashboard discovery
        discover_datasources: Enable datasource discovery
        discover_folders: Enable folder discovery
        discover_alerts: Enable alert rule discovery
        selectors: List of resource selection criteria

    Note:
        namespace field is inherited from MoleculeProviderConfig base class
    """

    base_url: str
    api_key: str
    org_id: int = 1

    # Feature flags for what to discover
    discover_dashboards: bool = True
    discover_datasources: bool = True
    discover_folders: bool = True
    discover_alerts: bool = True

    selectors: list[GrafanaSelectorConfig] = Field(  # type: ignore[assignment]
        default_factory=lambda: [GrafanaSelectorConfig()]
    )
