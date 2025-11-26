"""Vercel provider for Devgraph molecule framework.

This module implements a provider that discovers and manages Vercel teams,
projects, and deployments as entities in the Devgraph system. It integrates
with the Vercel API to fetch project and deployment information and creates
corresponding entities and relationships.
"""

import re

from loguru import logger

from devgraph_integrations.core.base import EntityDefinitionSpec
from devgraph_integrations.molecules.base.reconciliation import (
    FullStateReconciliation,
    ReconcilingMoleculeProvider,
)
from devgraph_integrations.types.entities import Entity

from .client import VercelClient
from .config import VercelProviderConfig
from .types import (
    V1VercelDeploymentEntity,
    V1VercelDeploymentEntityDefinition,
    V1VercelDeploymentEntitySpec,
    V1VercelProjectEntity,
    V1VercelProjectEntityDefinition,
    V1VercelProjectEntitySpec,
    V1VercelTeamEntity,
    V1VercelTeamEntityDefinition,
    V1VercelTeamEntitySpec,
)
from .types.relations import (
    VercelDeploymentBelongsToProjectRelation,
    VercelProjectBelongsToTeamRelation,
    VercelProjectUsesRepositoryRelation,
)


class VercelProvider(ReconcilingMoleculeProvider):
    """Provider for discovering Vercel teams, projects, and deployments.

    This provider connects to the Vercel API to discover teams, projects, and
    deployments within specified selectors, creating corresponding entities and
    relationships in the Devgraph. It supports field-selected relations to link
    projects with their source repositories.
    """

    _config_cls = VercelProviderConfig

    def __init__(self, name: str, every: int, config: VercelProviderConfig):
        """Initialize the Vercel provider.

        Args:
            name: Unique name for this provider instance
            every: Interval in seconds for reconciliation runs
            config: Vercel provider configuration
        """
        # Create reconciliation strategy using entity ID as the unique key
        reconciliation_strategy = FullStateReconciliation()
        super().__init__(name, every, config, reconciliation_strategy)

    def _init_client(self, config: VercelProviderConfig) -> VercelClient:
        """Initialize Vercel client.

        Args:
            config: Vercel provider configuration

        Returns:
            Initialized Vercel client
        """
        return VercelClient(
            base_url=config.api_url, token=config.token, timeout=config.timeout
        )

    def entity_definitions(self) -> list[EntityDefinitionSpec]:
        """Return entity definitions that this provider can create.

        Returns:
            List containing Vercel team, project, and deployment entity definitions
        """
        logger.debug("Fetching entity definitions from Vercel provider")
        return [
            V1VercelTeamEntityDefinition(),
            V1VercelProjectEntityDefinition(),
            V1VercelDeploymentEntityDefinition(),
        ]

    def _discover_current_entities(self) -> list[Entity]:
        """Discover all entities that should currently exist in Vercel.

        Returns:
            List of entities representing the current state in Vercel
        """
        entities = []

        # Get teams first if we need them
        teams_by_id = {}
        teams = self.client.get_teams()
        for team in teams:
            team_entity = self._create_entity(
                V1VercelTeamEntity,
                name=team["slug"],
                spec=V1VercelTeamEntitySpec(
                    id=team["id"],
                    slug=team["slug"],
                    name=team["name"],
                    avatar=team.get("avatar"),
                    created_at=team.get("createdAt"),
                ),
                labels={"team_id": team["id"]},
            )
            entities.append(team_entity)
            teams_by_id[team["id"]] = team_entity

        # Ensure we have a team entity for the configured team_id
        # This handles cases where the token is scoped to a specific team
        # and the /v2/teams API doesn't return it
        if self.config.team_id not in teams_by_id:
            logger.info(
                f"Creating team entity for configured team_id: {self.config.team_id}"
            )
            team_entity = self._create_entity(
                V1VercelTeamEntity,
                name=self.config.team_id,  # Use team_id as name since we don't have team details
                spec=V1VercelTeamEntitySpec(
                    id=self.config.team_id,
                    slug=self.config.team_id,
                    name=self.config.team_id,
                    avatar=None,
                    created_at=None,
                ),
                labels={"team_id": self.config.team_id},
            )
            entities.append(team_entity)
            teams_by_id[self.config.team_id] = team_entity

        # Process projects for each selector
        # Store raw project data for relation creation
        self._raw_projects = {}

        for selector in self.config.selectors:
            # Use selector team_id if specified, otherwise use provider-level team_id
            team_id = selector.team_id or self.config.team_id
            projects = self.client.get_projects(team_id=team_id)

            for project in projects:
                # Apply project name pattern filter
                if not re.match(selector.project_name_pattern, project["name"]):
                    continue

                try:
                    project_entity = self._create_entity(
                        V1VercelProjectEntity,
                        name=project["name"],
                        spec=V1VercelProjectEntitySpec(
                            name=project["name"],
                            id=project["id"],
                            framework=project.get("framework"),
                            url=project.get("ssoProtection", {}).get("deploymentType")
                            or f"https://{project['name']}.vercel.app",
                            description=project.get("description"),
                            team_id=team_id,
                            created_at=project.get("createdAt"),
                            updated_at=project.get("updatedAt"),
                        ),
                        labels={
                            "project_id": project["id"],
                            "team_id": team_id,
                        },
                    )
                    entities.append(project_entity)

                    # Store raw project data for relation creation
                    self._raw_projects[project["id"]] = project

                    # Get recent deployments for this project
                    deployments = self.client.get_deployments(project["id"], team_id)
                    for deployment in deployments[
                        :5
                    ]:  # Limit to 5 most recent deployments
                        try:
                            deployment_entity = self._create_entity(
                                V1VercelDeploymentEntity,
                                name=f"{project['name']}-{deployment['uid'][:8]}",
                                spec=V1VercelDeploymentEntitySpec(
                                    uid=deployment["uid"],
                                    name=deployment.get("name", project["name"]),
                                    url=deployment.get("url", ""),
                                    project_id=project["id"],
                                    state=deployment.get("state", "unknown"),
                                    type=deployment.get("type", "lambda"),
                                    target=deployment.get("target"),
                                    created_at=deployment.get("createdAt"),
                                    ready=deployment.get("ready"),
                                    git_source=deployment.get("gitSource"),
                                ),
                                labels={
                                    "project_id": project["id"],
                                    "deployment_uid": deployment["uid"],
                                    "state": deployment.get("state", "unknown"),
                                },
                            )
                            entities.append(deployment_entity)
                        except Exception as e:
                            logger.warning(
                                f"Failed to create deployment entity for {deployment.get('uid')}: {e}"
                            )
                            continue

                except Exception as e:
                    logger.exception(
                        f"Could not create entity for project {project['name']}: {e}"
                    )
                    continue

        return entities

    def _get_managed_entity_kinds(self) -> list[str]:
        """Get list of entity kinds managed by this Vercel provider.

        Returns:
            List of Vercel entity kind strings
        """
        return ["VercelTeam", "VercelProject", "VercelDeployment"]

    def _create_relations_for_entities(self, entities: list[Entity]) -> list:
        """Create relations for Vercel entities.

        Args:
            entities: Entities to create relations for

        Returns:
            List of relation objects
        """
        relations = []

        # Group entities by type
        teams_by_id = {}
        projects_by_id = {}
        deployments = []

        for entity in entities:
            if entity.kind == "VercelTeam":
                teams_by_id[entity.spec.id] = entity
            elif entity.kind == "VercelProject":
                projects_by_id[entity.spec.id] = entity
            elif entity.kind == "VercelDeployment":
                deployments.append(entity)

        # Create project-to-team relations
        for project_entity in projects_by_id.values():
            team_id = project_entity.spec.team_id
            if team_id and team_id in teams_by_id:
                relations.append(
                    self.create_relation_with_metadata(
                        VercelProjectBelongsToTeamRelation,
                        namespace=self.config.namespace,
                        source=project_entity.reference,
                        target=teams_by_id[team_id].reference,
                    )
                )

            # Create relation to GitHub repository if available
            project_id = project_entity.spec.id
            if project_id in getattr(self, "_raw_projects", {}):
                raw_project = self._raw_projects[project_id]
                git_repository = raw_project.get("link", {})
                if git_repository and git_repository.get("type") == "github":
                    repo_url = f"https://github.com/{git_repository.get('org')}/{git_repository.get('repo')}"
                    repo_relation = self._create_repository_relation(
                        VercelProjectUsesRepositoryRelation,
                        project_entity.reference,
                        repo_url,
                    )
                    relations.append(repo_relation)

        # Create deployment-to-project relations
        for deployment_entity in deployments:
            project_id = deployment_entity.spec.project_id
            if project_id in projects_by_id:
                relations.append(
                    self.create_relation_with_metadata(
                        VercelDeploymentBelongsToProjectRelation,
                        namespace=self.config.namespace,
                        source=deployment_entity.reference,
                        target=projects_by_id[project_id].reference,
                    )
                )

        return relations
