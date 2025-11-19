"""GitLab provider for Devgraph molecule framework.

This module implements a provider that discovers and manages GitLab projects
and hosting services as entities in the Devgraph system. It integrates with the
GitLab API to fetch project information and create corresponding entities
and relationships.
"""

import re
from base64 import b64decode

from gitlab import Gitlab
from gitlab.exceptions import GitlabGetError
from loguru import logger

from devgraph_integrations.core.entity import EntityDefinitionSpec
from devgraph_integrations.core.file_parser import parse_entity_file
from devgraph_integrations.molecules.base.reconciliation import (
    FullStateReconciliation,
    ReconcilingMoleculeProvider,
)
from devgraph_integrations.types.entities import Entity, EntityMetadata

from .config import GitlabProviderConfig
from .types.relations import GitlabProjectHostedByRelation
from .types.v1_gitlab_hosting_service import (
    V1GitlabHostingServiceEntity,
    V1GitlabHostingServiceEntityDefinition,
    V1GitlabHostingServiceEntitySpec,
)
from .types.v1_gitlab_project import (
    V1GitlabProjectEntity,
    V1GitlabProjectEntityDefinition,
    V1GitlabProjectEntitySpec,
)


class GitlabProvider(ReconcilingMoleculeProvider):
    """Provider for discovering GitLab projects and hosting services.

    This provider connects to the GitLab API to discover projects within
    specified groups and creates corresponding entities in the Devgraph.
    It supports filtering projects by name patterns and organizing them
    under hosting service entities.

    Attributes:
        _config_cls: Configuration class for this provider
        config: Provider configuration instance
        gitlab: GitLab API client instance
    """

    _config_cls = GitlabProviderConfig

    def __init__(self, name: str, every: int, config: GitlabProviderConfig):
        """Initialize the GitLab provider.

        Args:
            name: Unique name for this provider instance
            every: Interval in seconds for reconciliation runs
            config: GitLab provider configuration
        """
        # Create reconciliation strategy using entity IDs as unique keys
        reconciliation_strategy = FullStateReconciliation()
        super().__init__(name, every, config, reconciliation_strategy)
        # Initialize GitLab client - use base_url, not api_url (client adds /api/v4 automatically)
        self.gitlab = Gitlab(url=config.base_url, private_token=config.token)

    def _should_init_client(self) -> bool:
        """GitLab providers should not use the standard client initialization."""
        return False

    def entity_definitions(self) -> list[EntityDefinitionSpec]:
        """Return entity definitions that this provider can create.

        Returns:
            List containing GitLab hosting service and project entity definitions
        """
        logger.debug("Fetching entity definitions from GitLab provider")
        return [
            V1GitlabHostingServiceEntityDefinition(),
            V1GitlabProjectEntityDefinition(),
        ]

    def _discover_current_entities(self) -> list[Entity]:
        """Discover all entities that should currently exist in GitLab.

        Returns:
            List of entities representing the current state in GitLab
        """
        entities = []

        # Create the GitLab hosting service entity
        logger.debug(
            f"Creating GitLab hosting service entity with namespace: {self.config.namespace}"
        )
        logger.debug(f"GitLab hosting service will use api_url: {self.config.api_url}")
        gitlab_host = V1GitlabHostingServiceEntity(
            metadata=EntityMetadata(
                name="gitlab",
                namespace=self.config.namespace,
                labels={"service": "gitlab"},
            ),
            spec=V1GitlabHostingServiceEntitySpec(api_url=self.config.api_url),
        )
        entities.append(gitlab_host)
        logger.info(f"Added GitLab hosting service entity: {gitlab_host.id}")
        logger.info(f"GitLab hosting service ID: {gitlab_host.id}")
        logger.info(f"GitLab hosting service spec: {gitlab_host.spec.to_dict()}")

        # Discover projects from GitLab API
        for selector in self.config.selectors:
            try:
                # Get group
                group = self.gitlab.groups.get(selector.group)
                # Get all projects in the group
                projects = group.projects.list(get_all=True)

                for project in projects:
                    # Get full project details
                    full_project = self.gitlab.projects.get(project.id)

                    if not re.match(selector.project_name, full_project.name):
                        continue

                    try:
                        # Fetch project languages
                        languages = None
                        try:
                            languages = full_project.languages()
                            logger.debug(
                                f"Retrieved {len(languages)} languages for {full_project.name}: {list(languages.keys())}"
                            )
                        except Exception as lang_error:
                            logger.warning(
                                f"Failed to fetch languages for {full_project.name}: {lang_error}"
                            )

                        # Create project_id as group/project_name
                        project_id = f"{selector.group}/{full_project.name}"

                        project_entity = V1GitlabProjectEntity(
                            metadata=EntityMetadata(
                                name=full_project.name,
                                namespace=self.config.namespace,
                                labels={"group": selector.group},
                            ),
                            spec=V1GitlabProjectEntitySpec(
                                group=selector.group,
                                name=full_project.name,
                                project_id=project_id,
                                url=full_project.web_url,
                                description=full_project.description or "",
                                languages=languages,
                                visibility=full_project.visibility,
                            ),
                        )
                        entities.append(project_entity)

                        # Read graph files from project
                        for file_path in selector.graph_files:
                            content = self._read_file_from_project(
                                full_project, file_path
                            )
                            if content:
                                file_entities, file_relations = parse_entity_file(
                                    content=content,
                                    source_name=full_project.name,
                                    file_path=file_path,
                                    namespace=self.config.namespace,
                                    additional_labels={
                                        "source-project": full_project.name
                                    },
                                )
                                entities.extend(file_entities)
                                # Store relations for later processing
                                if not hasattr(self, "_file_relations"):
                                    self._file_relations = []
                                self._file_relations.extend(file_relations)

                                if file_entities or file_relations:
                                    logger.info(
                                        f"Found {len(file_entities)} entities and {len(file_relations)} relations in {full_project.name}:{file_path}"
                                    )

                    except Exception as e:
                        logger.exception(
                            f"Could not create entity for project {full_project.name}: {e}"
                        )
                        continue

            except Exception as e:
                error_msg = str(e)
                # Check if it's an authentication error - don't print full traceback for these
                if (
                    "401" in error_msg
                    or "invalid_token" in error_msg
                    or "unauthorized" in error_msg.lower()
                ):
                    logger.error(
                        f"Authentication failed for GitLab group {selector.group}. Please check your token configuration."
                    )
                else:
                    logger.exception(
                        f"Could not access GitLab group {selector.group}: {e}"
                    )
                continue

        logger.info(f"GitLab provider discovered {len(entities)} total entities:")
        for entity in entities:
            logger.info(f"  - {entity.kind}: {entity.metadata.name} (ID: {entity.id})")
        return entities

    def _get_managed_entity_kinds(self) -> list[str]:
        """Get list of entity kinds managed by this GitLab provider.

        Returns:
            List of GitLab entity kind strings
        """
        return ["GitlabProject", "GitlabHostingService"]

    def _read_file_from_project(self, project, file_path: str) -> str | None:
        """Read a file from a GitLab project.

        Args:
            project: GitLab project object
            file_path: Path to the file in the project

        Returns:
            File content as string, or None if file doesn't exist
        """
        try:
            file_content = project.files.get(file_path, ref="main")
            if file_content.encoding == "base64":
                return b64decode(file_content.content).decode("utf-8")
            else:
                return file_content.content.decode("utf-8")
        except GitlabGetError:
            # Try 'master' branch if 'main' doesn't exist
            try:
                file_content = project.files.get(file_path, ref="master")
                if file_content.encoding == "base64":
                    return b64decode(file_content.content).decode("utf-8")
                else:
                    return file_content.content.decode("utf-8")
            except GitlabGetError:
                logger.debug(
                    f"File {file_path} not found in {project.path_with_namespace}"
                )
                return None
        except Exception as e:
            logger.warning(
                f"Error reading file {file_path} from {project.path_with_namespace}: {e}"
            )
            return None

    def _create_relations_for_entities(self, entities: list[Entity]) -> list:
        """Create relations for GitLab entities.

        Args:
            entities: Entities to create relations for

        Returns:
            List of relation objects
        """
        relations = []

        # Find hosting service and projects
        gitlab_host = None
        projects = []

        logger.debug(f"Creating relations for {len(entities)} GitLab entities")

        for entity in entities:
            logger.debug(f"Processing entity: {entity.kind} - {entity.metadata.name}")
            if entity.kind == "GitlabHostingService":
                gitlab_host = entity
                logger.debug(f"Found GitLab host: {entity.metadata.name}")
            elif entity.kind == "GitlabProject":
                projects.append(entity)
                logger.debug(f"Found project: {entity.metadata.name}")

        # Create HOSTED_BY relations between projects and hosting service
        if gitlab_host:
            logger.debug(f"Creating {len(projects)} HOSTED_BY relations")
            for project in projects:
                relation = GitlabProjectHostedByRelation(
                    namespace=self.config.namespace,
                    source=project.reference,
                    target=gitlab_host.reference,
                )
                relations.append(relation)
                logger.debug(
                    f"Created HOSTED_BY relation: {project.metadata.name} -> {gitlab_host.metadata.name}"
                )

        # Add any file-based relations
        if hasattr(self, "_file_relations"):
            relations.extend(self._file_relations)
            logger.debug(f"Added {len(self._file_relations)} file-based relations")
            # Clear file relations after use
            delattr(self, "_file_relations")

        logger.info(f"GitLab provider created {len(relations)} total relations")
        return relations
