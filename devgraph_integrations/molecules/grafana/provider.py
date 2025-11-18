"""Grafana provider for Devgraph molecule framework.

This module implements a provider that discovers and manages Grafana dashboards,
datasources, folders, and alerts as entities in the Devgraph system.
"""
import requests  # type: ignore
from loguru import logger
from typing import Any

from devgraph_integrations.core.entity import EntityDefinitionSpec
from devgraph_integrations.core.state import GraphMutations
from devgraph_integrations.types.entities import EntityMetadata, Entity
from devgraph_integrations.molecules.base.reconciliation import (
    ReconcilingMoleculeProvider,
    FullStateReconciliation,
)

from .config import GrafanaProviderConfig


class GrafanaProvider(ReconcilingMoleculeProvider):
    """Provider for discovering Grafana resources.

    This provider connects to the Grafana API to discover dashboards, datasources,
    folders, and alerts, creating corresponding entities in the Devgraph.

    Attributes:
        _config_cls: Configuration class for this provider
        config: Provider configuration instance
        session: HTTP session for API requests
    """

    _config_cls = GrafanaProviderConfig

    def __init__(self, name: str, every: int, config: GrafanaProviderConfig):
        """Initialize the Grafana provider.

        Args:
            name: Unique name for this provider instance
            every: Interval in seconds for reconciliation runs
            config: Grafana provider configuration
        """
        reconciliation_strategy = FullStateReconciliation()
        super().__init__(name, every, config, reconciliation_strategy)

        # Initialize HTTP session with auth headers
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            }
        )

        self.base_url = config.base_url.rstrip("/")
        logger.info(f"Initialized Grafana provider for {self.base_url}")

    def entity_definitions(self) -> list[EntityDefinitionSpec]:
        """Return entity definitions for Grafana resources.

        Returns:
            List of entity definition specifications
        """
        from .types.v1_grafana_instance import V1GrafanaInstanceEntityDefinition
        from .types.v1_grafana_dashboard import V1GrafanaDashboardEntityDefinition
        from .types.v1_grafana_datasource import V1GrafanaDatasourceEntityDefinition
        from .types.v1_grafana_folder import V1GrafanaFolderEntityDefinition

        definitions = [
            V1GrafanaInstanceEntityDefinition,
            V1GrafanaDashboardEntityDefinition,
            V1GrafanaDatasourceEntityDefinition,
            V1GrafanaFolderEntityDefinition,
        ]

        return definitions

    def _discover_current_entities(self) -> GraphMutations:
        """Discover all Grafana resources and return as GraphMutations.

        Returns:
            GraphMutations containing discovered entities and relationships
        """
        mutations = GraphMutations()

        try:
            # Create Grafana instance entity
            instance_entity = self._create_instance_entity()
            mutations.entities.append(instance_entity)

            # Discover folders (needed for dashboard relationships)
            folders = {}
            if self.config.discover_folders:
                folder_entities = self._discover_folders()
                for folder_entity in folder_entities:
                    mutations.entities.append(folder_entity)
                    # Create relationship: folder hosted_by instance
                    mutations.relations.append(
                        {
                            "from": folder_entity,
                            "to": instance_entity,
                            "relation": "hosted_by",
                        }
                    )
                    folders[folder_entity.spec.get("id")] = folder_entity

            # Discover datasources
            if self.config.discover_datasources:
                datasource_entities = self._discover_datasources()
                for datasource_entity in datasource_entities:
                    mutations.entities.append(datasource_entity)
                    # Create relationship: datasource hosted_by instance
                    mutations.relations.append(
                        {
                            "from": datasource_entity,
                            "to": instance_entity,
                            "relation": "hosted_by",
                        }
                    )

            # Discover dashboards
            if self.config.discover_dashboards:
                dashboard_entities = self._discover_dashboards()
                for dashboard_entity in dashboard_entities:
                    mutations.entities.append(dashboard_entity)
                    # Create relationship: dashboard hosted_by instance
                    mutations.relations.append(
                        {
                            "from": dashboard_entity,
                            "to": instance_entity,
                            "relation": "hosted_by",
                        }
                    )

                    # Create relationship: dashboard in_folder folder
                    folder_id = dashboard_entity.spec.get("folder_id")
                    if folder_id and folder_id in folders:
                        mutations.relations.append(
                            {
                                "from": dashboard_entity,
                                "to": folders[folder_id],
                                "relation": "in_folder",
                            }
                        )

        except Exception as e:
            logger.error(f"Error discovering Grafana entities: {e}", exc_info=True)

        return mutations

    def _create_instance_entity(self) -> Entity:
        """Create entity representing the Grafana instance.

        Returns:
            Entity representing the Grafana instance
        """
        from .types.v1_grafana_instance import V1GrafanaInstanceEntity

        # Get health/version info
        try:
            health = self.session.get(f"{self.base_url}/api/health").json()
            version = health.get("version", "unknown")
        except Exception as e:
            logger.warning(f"Could not fetch Grafana health: {e}")
            version = "unknown"

        entity = V1GrafanaInstanceEntity(
            metadata=EntityMetadata(
                name=self.base_url.split("//")[-1].replace(":", "-").replace("/", "-"),
                namespace=self.config.namespace,
                labels={"provider": "grafana"},
            ),
            spec={
                "url": self.base_url,
                "version": version,
                "org_id": self.config.org_id,
            },
        )

        return entity

    def _discover_folders(self) -> list[Entity]:
        """Discover Grafana folders.

        Returns:
            List of folder entities
        """
        from .types.v1_grafana_folder import V1GrafanaFolderEntity

        try:
            response = self.session.get(f"{self.base_url}/api/folders")
            response.raise_for_status()
            folders_data = response.json()

            entities = []
            for folder in folders_data:
                entity = V1GrafanaFolderEntity(
                    metadata=EntityMetadata(
                        name=f"folder-{folder['uid']}",
                        namespace=self.config.namespace,
                        labels={
                            "provider": "grafana",
                            "folder_uid": folder["uid"],
                        },
                    ),
                    spec={
                        "uid": folder["uid"],
                        "id": folder["id"],
                        "title": folder["title"],
                        "url": f"{self.base_url}{folder.get('url', '')}",
                    },
                )
                entities.append(entity)

            logger.info(f"Discovered {len(entities)} Grafana folders")
            return entities

        except Exception as e:
            logger.error(f"Error discovering Grafana folders: {e}")
            return []

    def _discover_datasources(self) -> list[Entity]:
        """Discover Grafana datasources.

        Returns:
            List of datasource entities
        """
        from .types.v1_grafana_datasource import V1GrafanaDatasourceEntity

        try:
            response = self.session.get(f"{self.base_url}/api/datasources")
            response.raise_for_status()
            datasources_data = response.json()

            entities = []
            for datasource in datasources_data:
                entity = V1GrafanaDatasourceEntity(
                    metadata=EntityMetadata(
                        name=f"datasource-{datasource['uid']}",
                        namespace=self.config.namespace,
                        labels={
                            "provider": "grafana",
                            "datasource_type": datasource.get("type", "unknown"),
                            "datasource_uid": datasource["uid"],
                        },
                    ),
                    spec={
                        "uid": datasource["uid"],
                        "id": datasource["id"],
                        "name": datasource["name"],
                        "type": datasource["type"],
                        "url": datasource.get("url"),
                        "is_default": datasource.get("isDefault", False),
                        "json_data": datasource.get("jsonData", {}),
                    },
                )
                entities.append(entity)

            logger.info(f"Discovered {len(entities)} Grafana datasources")
            return entities

        except Exception as e:
            logger.error(f"Error discovering Grafana datasources: {e}")
            return []

    def _discover_dashboards(self) -> list[Entity]:
        """Discover Grafana dashboards.

        Returns:
            List of dashboard entities
        """
        from .types.v1_grafana_dashboard import V1GrafanaDashboardEntity

        try:
            # Search for all dashboards
            response = self.session.get(
                f"{self.base_url}/api/search", params={"type": "dash-db"}
            )
            response.raise_for_status()
            dashboards_data = response.json()

            entities = []
            for dashboard in dashboards_data:
                # Apply selectors
                if not self._matches_selectors(dashboard):
                    continue

                entity = V1GrafanaDashboardEntity(
                    metadata=EntityMetadata(
                        name=f"dashboard-{dashboard['uid']}",
                        namespace=self.config.namespace,
                        labels={
                            "provider": "grafana",
                            "dashboard_uid": dashboard["uid"],
                            **{
                                f"tag_{tag}": "true"
                                for tag in dashboard.get("tags", [])
                            },
                        },
                    ),
                    spec={
                        "uid": dashboard["uid"],
                        "id": dashboard["id"],
                        "title": dashboard["title"],
                        "url": f"{self.base_url}{dashboard.get('url', '')}",
                        "folder_id": dashboard.get("folderId"),
                        "folder_uid": dashboard.get("folderUid"),
                        "folder_title": dashboard.get("folderTitle"),
                        "tags": dashboard.get("tags", []),
                        "is_starred": dashboard.get("isStarred", False),
                    },
                )
                entities.append(entity)

            logger.info(f"Discovered {len(entities)} Grafana dashboards")
            return entities

        except Exception as e:
            logger.error(f"Error discovering Grafana dashboards: {e}")
            return []

    def _matches_selectors(self, dashboard: dict[str, Any]) -> bool:
        """Check if a dashboard matches configured selectors.

        Args:
            dashboard: Dashboard data from Grafana API

        Returns:
            True if dashboard matches any selector, False otherwise
        """
        for selector in self.config.selectors:
            # Check dashboard UIDs filter
            if (
                selector.dashboard_uids
                and dashboard["uid"] not in selector.dashboard_uids
            ):
                continue

            # Check folder IDs filter
            if (
                selector.folder_ids
                and dashboard.get("folderId") not in selector.folder_ids
            ):
                continue

            # Check tags filter
            if selector.tags:
                dashboard_tags = set(dashboard.get("tags", []))
                if not any(tag in dashboard_tags for tag in selector.tags):
                    continue

            # If we get here, dashboard matches this selector
            return True

        # If no selectors or no matches
        return not self.config.selectors or len(self.config.selectors) == 0
