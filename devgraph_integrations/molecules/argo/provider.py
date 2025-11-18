"""Argo CD provider for Devgraph molecule framework.

This module implements a provider that discovers and manages Argo CD instances,
projects, and applications as entities in the Devgraph system. It integrates
with the Argo CD API to fetch application and project information and creates
corresponding entities and relationships.
"""
from loguru import logger

from devgraph_client.client import AuthenticatedClient
from devgraph_integrations.core.entity import EntityDefinitionSpec
from devgraph_integrations.core.state import GraphMutations

from ..base.provider import HttpApiMoleculeProvider

from .client import ArgoClient
from .config import ArgoProviderConfig
from .types import (
    V1ArgoApplicationEntityDefinition,
    V1ArgoInstanceEntityDefinition,
    V1ArgoProjectEntityDefinition,
    V1ArgoProjectEntitySpec,
    V1ArgoApplicationEntity,
    V1ArgoInstanceEntity,
    V1ArgoApplicationEntitySpec,
    V1ArgoInstanceEntitySpec,
    V1ArgoProjectEntity,
)
from .types.relations import (
    ApplicationBelongsToProjectRelation,
    ApplicationUsesRepositoryRelation,
    ProjectBelongsToInstanceRelation,
)


class ArgoProvider(HttpApiMoleculeProvider):
    """Provider for discovering Argo CD instances, projects, and applications.

    This provider connects to the Argo CD API to discover projects and applications
    within an Argo CD instance, creating corresponding entities and relationships
    in the Devgraph. It supports field-selected relations to link applications
    with their source repositories.
    """

    _config_cls = ArgoProviderConfig

    def _get_client_class(self):
        """Get the Argo CD client class.

        Returns:
            ArgoClient class for Argo CD API interactions
        """
        return ArgoClient

    def _init_client(self, config: ArgoProviderConfig) -> ArgoClient:
        """Initialize Argo CD client.

        Args:
            config: Argo CD provider configuration

        Returns:
            Initialized Argo CD client
        """
        return ArgoClient(
            base_url=config.api_url, token=config.token, timeout=config.timeout
        )

    def entity_definitions(self) -> list[EntityDefinitionSpec]:
        """Return entity definitions that this provider can create.

        Returns:
            List containing Argo CD instance, project, and application entity definitions
        """
        logger.debug("Fetching entity definitions from Argo provider")
        return [
            V1ArgoApplicationEntityDefinition(),
            V1ArgoInstanceEntityDefinition(),
            V1ArgoProjectEntityDefinition(),
        ]

    def _reconcile_entities(self, client: AuthenticatedClient) -> GraphMutations:
        """Perform Argo CD-specific entity reconciliation.

        Discovers Argo CD instances, projects, and applications, creating entities
        and relationships as needed. Creates field-selected relations between
        applications and their source repositories.

        Args:
            client: Authenticated Devgraph API client

        Returns:
            GraphMutations containing entities and relations to create/delete
        """
        create_entities = []
        create_relations = []

        argo_instance = self._create_entity(
            V1ArgoInstanceEntity,
            name="argo",
            spec=V1ArgoInstanceEntitySpec(api_url=self.config.api_url),
        )
        create_entities.append(argo_instance)

        projects = self.client.get_projects()
        for project in projects:
            project_name = project["metadata"]["name"]
            logger.debug(f"Processing project: {project_name}")

            project_entity = self._create_entity(
                V1ArgoProjectEntity,
                name=project_name,
                spec=V1ArgoProjectEntitySpec(name=project_name),
            )
            create_entities.append(project_entity)

            create_relations.append(
                ProjectBelongsToInstanceRelation(
                    namespace=self.config.namespace,
                    source=project_entity.reference,
                    target=argo_instance.reference,
                )
            )

            apps = self.client.get_apps(project_name)
            if not apps:
                logger.debug(f"No apps found in project '{project_name}', skipping")
                continue

            for app in apps:
                app_name = app["metadata"]["name"]
                logger.debug(f"Processing app: {app_name}")

                app_entity = self._create_entity(
                    V1ArgoApplicationEntity,
                    name=app_name,
                    spec=V1ArgoApplicationEntitySpec(name=app_name),
                )
                create_entities.append(app_entity)

                # Standard relation to project
                create_relations.append(
                    ApplicationBelongsToProjectRelation(
                        namespace=self.config.namespace,
                        source=app_entity.reference,
                        target=project_entity.reference,
                    )
                )

                # Field-selected relations to GitHub repositories
                sources = app.get("spec", {}).get("sources", [])
                for source in sources:
                    repo_url = source.get("repoURL")
                    if repo_url:
                        logger.debug(f"App '{app_name}' source - Repo: {repo_url}")

                        # Create field-selected relation to GitHub repository
                        repo_relation = self._create_repository_relation(
                            ApplicationUsesRepositoryRelation,
                            app_entity.reference,
                            repo_url,
                        )
                        create_relations.append(repo_relation)

        return self._create_mutations(
            create_entities=create_entities, create_relations=create_relations
        )
