"""FOSSA provider for Devgraph molecule framework.

This module implements a provider that discovers and manages FOSSA projects
as entities in the Devgraph system. It integrates with the FOSSA API to fetch
project information and creates corresponding entities and relationships with
GitHub/GitLab repositories.
"""

from urllib.parse import urlparse

import requests  # type: ignore
from loguru import logger

from devgraph_integrations.core.entity import EntityDefinitionSpec
from devgraph_integrations.molecules.base.reconciliation import (
    FullStateReconciliation,
    ReconcilingMoleculeProvider,
)
from devgraph_integrations.molecules.base.utils import sanitize_entity_name
from devgraph_integrations.types.entities import Entity, EntityMetadata, EntityReference

from .config import FOSSAProviderConfig
from .types.relations import FOSSAProjectScansRelation
from .types.v1_fossa_project import (
    V1FOSSAProjectEntity,
    V1FOSSAProjectEntityDefinition,
    V1FOSSAProjectEntitySpec,
)


class FOSSAProvider(ReconcilingMoleculeProvider):
    """Provider for discovering FOSSA projects and linking them to repositories.

    This provider connects to the FOSSA API to discover projects and creates
    corresponding entities in the Devgraph. It automatically links FOSSA projects
    to their corresponding GitHub or GitLab repositories based on URL matching.

    Attributes:
        _config_cls: Configuration class for this provider
        config: Provider configuration instance
        session: HTTP session for FOSSA API requests
    """

    _config_cls = FOSSAProviderConfig

    def __init__(self, name: str, every: int, config: FOSSAProviderConfig):
        """Initialize the FOSSA provider.

        Args:
            name: Unique name for this provider instance
            every: Interval in seconds for reconciliation runs
            config: FOSSA provider configuration
        """
        # Create reconciliation strategy using entity IDs as unique keys
        reconciliation_strategy = FullStateReconciliation()
        super().__init__(name, every, config, reconciliation_strategy)

        logger.info(
            f"FOSSA Provider initialized with client: {self.client is not None}"
        )

        # Initialize HTTP session for FOSSA API
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {config.token}",
                "Content-Type": "application/json",
            }
        )

    def _should_init_client(self) -> bool:
        """FOSSA providers need the client to query for GitHub/GitLab repos."""
        return True

    def entity_definitions(self) -> list[EntityDefinitionSpec]:
        """Return entity definitions that this provider can create.

        Returns:
            List containing FOSSA project entity definition
        """
        logger.debug("Fetching entity definitions from FOSSA provider")
        return [
            V1FOSSAProjectEntityDefinition(),
        ]

    def _make_request(self, method: str, endpoint: str, params: dict = None) -> dict:
        """Make a request to the FOSSA API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            Response data as dict

        Raises:
            Exception: If the request fails
        """
        url = f"{self.config.base_url}/{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            # Don't re-raise auth errors - let caller handle gracefully
            if e.response is not None and e.response.status_code in (401, 403):
                logger.warning(f"FOSSA API authentication failed: {e.response.status_code} {e.response.reason}")
                raise
            logger.error(f"FOSSA API HTTP error: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"FOSSA API request error: {e}")
            raise

    def _discover_current_entities(self) -> list[Entity]:
        """Discover all entities that should currently exist in FOSSA.

        Returns:
            List of entities representing the current state in FOSSA
        """
        entities = []

        logger.info("Starting FOSSA project discovery")

        # List all FOSSA projects
        params = {
            "count": 100,
            "offset": 0,
        }

        if self.config.filter_title:
            params["title"] = self.config.filter_title

        try:
            result = self._make_request("GET", "v2/projects", params=params)
            logger.debug(f"FOSSA API response keys: {list(result.keys())}")

            # The v2 API returns "projects" not "data"
            projects = result.get("projects", [])
            logger.info(f"FOSSA API returned {len(projects)} projects")

            # Process each project
            for project in projects:
                project_id = project.get("id")
                title = project.get("title")
                # Get locator from latestRevision if available
                locator = project.get("latestRevision", {}).get("locator")
                default_branch = project.get(
                    "branch"
                )  # v2 API uses "branch" not "default_branch"
                url = project.get("url")

                if not project_id or not title:
                    logger.warning(
                        f"Skipping project with missing ID or title: {project}"
                    )
                    continue

                # Create FOSSA project entity
                # Sanitize the name to be DNS 1123 compliant (max 253 chars)
                sanitized_name = sanitize_entity_name(project_id, max_length=253)

                project_entity = V1FOSSAProjectEntity(
                    metadata=EntityMetadata(
                        name=sanitized_name,
                        namespace=self.config.namespace,
                        labels={"fossa-project-id": project_id},
                    ),
                    spec=V1FOSSAProjectEntitySpec(
                        project_id=project_id,
                        title=title,
                        locator=locator,
                        default_branch=default_branch,
                        url=url,
                    ),
                )
                entities.append(project_entity)
                logger.debug(f"Discovered FOSSA project: {title} (ID: {project_id})")

        except requests.exceptions.HTTPError as e:
            # Handle authentication errors gracefully without traceback
            if e.response is not None and e.response.status_code in (401, 403):
                logger.warning(
                    f"Failed to discover FOSSA projects: Authentication failed ({e.response.status_code}). "
                    "Please check your FOSSA API token."
                )
            else:
                logger.error(f"Failed to discover FOSSA projects: HTTP {e.response.status_code if e.response else 'error'}: {e}")
        except Exception as e:
            logger.error(f"Failed to discover FOSSA projects: {e}")

        logger.info(f"FOSSA provider discovered {len(entities)} total entities")
        return entities

    def _get_managed_entity_kinds(self) -> list[str]:
        """Get list of entity kinds managed by this FOSSA provider.

        Returns:
            List of FOSSA entity kind strings
        """
        return ["FOSSAProject"]

    def _reconcile_entities(self, client):
        """Override to store client for relation creation."""
        # Store client temporarily for use in _create_relations_for_entities
        self._temp_client = client
        try:
            return super()._reconcile_entities(client)
        finally:
            # Clean up temporary client reference
            if hasattr(self, "_temp_client"):
                delattr(self, "_temp_client")

    def _normalize_url(self, url: str | None) -> str | None:
        """Normalize a repository URL for comparison.

        Args:
            url: Repository URL to normalize

        Returns:
            Normalized URL or None
        """
        if not url:
            return None

        try:
            # Parse URL and extract path
            parsed = urlparse(url)
            path = parsed.path.strip("/")

            # Lowercase for case-insensitive comparison
            path = path.lower()

            # Remove .git suffix if present
            if path.endswith(".git"):
                path = path[:-4]

            # Return normalized host + path
            return f"{parsed.netloc.lower()}/{path}"
        except Exception as e:
            logger.warning(f"Failed to normalize URL {url}: {e}")
            return None

    def _create_relations_for_entities(self, entities: list[Entity]) -> list:
        """Create relations for FOSSA entities.

        This method links FOSSA projects to their corresponding GitHub or GitLab
        repositories based on URL matching.

        Args:
            entities: Entities to create relations for

        Returns:
            List of relation objects
        """
        relations = []

        # Find all FOSSA projects
        fossa_projects = [e for e in entities if e.kind == "FOSSAProject"]

        if not fossa_projects:
            logger.debug("No FOSSA projects found to create relations for")
            return relations

        logger.debug(f"Creating relations for {len(fossa_projects)} FOSSA projects")

        # Use the temporary client that was stored during reconciliation
        client = getattr(self, "_temp_client", None)
        logger.info(f"Client available: {client is not None}")

        # Query the graph for all GitHub and GitLab repositories
        github_repos = []
        gitlab_projects = []

        try:
            # Get all GitHub repositories and GitLab projects from the graph
            from devgraph_client.api.entities import (
                get_entities,
            )

            if client:
                # List GitHub repositories
                try:
                    logger.debug("Querying for GitHubRepository entities...")
                    gh_response = get_entities.sync_detailed(
                        client=client,
                        label="GitHubRepository",
                        limit=1000,
                    )
                    logger.debug(f"GitHub query status code: {gh_response.status_code}")
                    if gh_response.parsed and hasattr(
                        gh_response.parsed, "primary_entities"
                    ):
                        github_repos = gh_response.parsed.primary_entities or []
                        logger.info(f"Found {len(github_repos)} GitHub repositories")
                    else:
                        logger.warning(
                            f"GitHub query returned no primary_entities: parsed={gh_response.parsed}"
                        )
                except Exception as e:
                    logger.warning(f"Failed to fetch GitHub repositories: {e}")

                # List GitLab projects
                try:
                    gl_response = get_entities.sync_detailed(
                        client=client,
                        label="GitLabProject",
                        limit=1000,
                    )
                    if gl_response.parsed and hasattr(
                        gl_response.parsed, "primary_entities"
                    ):
                        gitlab_projects = gl_response.parsed.primary_entities or []
                        logger.info(f"Found {len(gitlab_projects)} GitLab projects")
                except Exception as e:
                    logger.warning(f"Failed to fetch GitLab projects: {e}")

        except Exception as e:
            logger.warning(f"Failed to query repositories from graph: {e}")

        # Create a mapping of normalized URLs to entity references
        url_to_repo = {}

        for repo in github_repos:
            # Try to get URL from spec.additional_properties
            url = None
            if hasattr(repo, "spec") and hasattr(repo.spec, "additional_properties"):
                url = repo.spec.additional_properties.get("url")

            if url:
                normalized = self._normalize_url(url)
                if normalized:
                    url_to_repo[normalized] = EntityReference(
                        apiVersion=repo.api_version,
                        kind=repo.kind,
                        name=repo.metadata.name,
                        namespace=repo.metadata.namespace,
                    )

        for project in gitlab_projects:
            # Try to get URL from spec.additional_properties
            url = None
            if hasattr(project, "spec") and hasattr(
                project.spec, "additional_properties"
            ):
                url = project.spec.additional_properties.get("url")

            if url:
                normalized = self._normalize_url(url)
                if normalized:
                    url_to_repo[normalized] = EntityReference(
                        apiVersion=project.api_version,
                        kind=project.kind,
                        name=project.metadata.name,
                        namespace=project.metadata.namespace,
                    )

        logger.info(f"Built URL mapping with {len(url_to_repo)} entries")
        if url_to_repo:
            logger.info(f"Sample URLs in mapping: {list(url_to_repo.keys())[:5]}")

        # Link FOSSA projects to repositories
        for fossa_project in fossa_projects:
            if not fossa_project.spec.url:
                logger.debug(
                    f"FOSSA project {fossa_project.spec.title} has no URL, skipping linking"
                )
                continue

            normalized_fossa_url = self._normalize_url(fossa_project.spec.url)
            logger.info(
                f"FOSSA project {fossa_project.spec.title}: original={fossa_project.spec.url}, normalized={normalized_fossa_url}"
            )
            if not normalized_fossa_url:
                continue

            # Look for matching repository
            if normalized_fossa_url in url_to_repo:
                repo_ref = url_to_repo[normalized_fossa_url]
                relation = self.create_relation_with_metadata(
                    FOSSAProjectScansRelation,
                    namespace=self.config.namespace,
                    source=fossa_project.reference,
                    target=repo_ref,
                )
                relations.append(relation)
                logger.info(
                    f"Linked FOSSA project {fossa_project.spec.title} to {repo_ref.kind} {repo_ref.name}"
                )
            else:
                logger.info(
                    f"No matching repository found for FOSSA project {fossa_project.spec.title} (URL: {fossa_project.spec.url}, normalized: {normalized_fossa_url})"
                )

        logger.info(f"Created {len(relations)} FOSSA relations")
        return relations
