"""GitHub provider for Devgraph molecule framework.

This module implements a provider that discovers and manages GitHub repositories
and hosting services as entities in the Devgraph system. It integrates with the
GitHub API to fetch repository information and create corresponding entities
and relationships.
"""

import datetime
import re
import time
from base64 import b64decode

from github import Auth, Github
from github.GithubException import UnknownObjectException
from loguru import logger

from devgraph_integrations.core.entity import EntityDefinitionSpec
from devgraph_integrations.core.file_parser import parse_entity_file
from devgraph_integrations.molecules.base.reconciliation import (
    FullStateReconciliation,
    ReconcilingMoleculeProvider,
)
from devgraph_integrations.types.entities import Entity, EntityMetadata

from .config import GithubProviderConfig
from .types.relations import GithubRepositoryHostedByRelation
from .types.v1_github_hosting_service import (
    V1GithubHostingServiceEntity,
    V1GithubHostingServiceEntityDefinition,
    V1GithubHostingServiceEntitySpec,
)
from .types.v1_github_repository import (
    V1GithubRepositoryEntity,
    V1GithubRepositoryEntityDefinition,
    V1GithubRepositoryEntitySpec,
)


class GithubProvider(ReconcilingMoleculeProvider):
    """Provider for discovering GitHub repositories and hosting services.

    This provider connects to the GitHub API to discover repositories within
    specified organizations and creates corresponding entities in the Devgraph.
    It supports filtering repositories by name patterns and organizing them
    under hosting service entities.

    Attributes:
        _config_cls: Configuration class for this provider
        config: Provider configuration instance
        github: GitHub API client instance
    """

    _config_cls = GithubProviderConfig
    _display_name = "GitHub"
    _description = "Discover repositories and hosting services from GitHub"
    _logo = """<svg role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><title>GitHub</title><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>"""

    def __init__(self, name: str, every: int, config: GithubProviderConfig):
        """Initialize the GitHub provider.

        Args:
            name: Unique name for this provider instance
            every: Interval in seconds for reconciliation runs
            config: GitHub provider configuration
        """
        # Create reconciliation strategy using entity IDs as unique keys
        reconciliation_strategy = FullStateReconciliation()
        super().__init__(name, every, config, reconciliation_strategy)

        # Initialize GitHub client with appropriate authentication method
        if config.app_id and config.app_private_key:
            # Use GitHub App authentication (higher rate limits: 15,000/hour)
            logger.info(
                f"Initializing GitHub provider with App authentication (App ID: {config.app_id})"
            )

            # Ensure private key has proper formatting (PyGithub expects exact format)
            private_key = config.app_private_key.strip()

            # Fix common formatting issues
            if not private_key.startswith("-----BEGIN"):
                logger.error("Private key does not start with -----BEGIN header")
                raise ValueError("Invalid private key format: missing BEGIN header")
            if not private_key.endswith("-----"):
                logger.error("Private key does not end with ----- footer")
                raise ValueError("Invalid private key format: missing END footer")

            try:
                auth = Auth.AppAuth(
                    app_id=config.app_id,
                    private_key=private_key,
                )
            except Exception as e:
                logger.error(f"Failed to initialize GitHub App authentication: {e}")
                logger.error(f"Private key starts with: {private_key[:50]}...")
                raise ValueError(f"Failed to parse GitHub App private key: {e}")
            # If installation_id is provided, use it directly
            if config.installation_id:
                auth = auth.get_installation_auth(config.installation_id)
                logger.info(
                    f"Using GitHub App installation {config.installation_id} "
                    f"(rate limit: 15,000 requests/hour)"
                )
            else:
                logger.warning(
                    "GitHub App configured but no installation_id provided, "
                    "will use app-level auth"
                )
        elif config.token:
            # Use Personal Access Token (lower rate limits: 5,000/hour)
            logger.info("Initializing GitHub provider with PAT authentication")
            auth = Auth.Token(config.token)
            logger.warning(
                "Using PAT authentication (5,000 requests/hour). "
                "Consider using GitHub App for 3x higher rate limits."
            )
        else:
            raise ValueError(
                "GitHub provider requires either 'token' (PAT) or "
                "'app_id' + 'app_private_key' (GitHub App) configuration"
            )

        self.github = Github(
            auth=auth,
            retry=3,  # Retry up to 3 times
            per_page=100,  # Get more items per request to reduce API calls
        )

    def _should_init_client(self) -> bool:
        """GitHub providers should not use the standard client initialization."""
        return False

    def entity_definitions(self) -> list[EntityDefinitionSpec]:
        """Return entity definitions that this provider can create.

        Returns:
            List containing GitHub hosting service and repository entity definitions
        """
        logger.debug("Fetching entity definitions from GitHub provider")
        return [
            V1GithubHostingServiceEntityDefinition(),
            V1GithubRepositoryEntityDefinition(),
        ]

    def _discover_current_entities(self) -> list[Entity]:
        """Discover all entities that should currently exist in GitHub.

        Returns:
            List of entities representing the current state in GitHub
        """
        entities = []

        # Create the GitHub hosting service entity
        logger.debug(
            f"Creating GitHub hosting service entity with namespace: {self.config.namespace}"
        )
        logger.debug(f"GitHub hosting service will use api_url: {self.config.api_url}")
        github_host = V1GithubHostingServiceEntity(
            metadata=EntityMetadata(
                name="github",
                namespace=self.config.namespace,
                labels={"organization": "github"},
            ),
            spec=V1GithubHostingServiceEntitySpec(api_url=self.config.api_url),
        )
        entities.append(github_host)
        logger.info(f"Added GitHub hosting service entity: {github_host.id}")
        logger.info(f"GitHub hosting service ID: {github_host.id}")
        logger.info(f"GitHub hosting service spec: {github_host.spec.to_dict()}")

        # Discover repositories from GitHub API
        for selector in self.config.selectors:
            try:
                # Check rate limit before making requests
                rate_limit = self.github.get_rate_limit()
                core_limit = rate_limit.resources.core
                if core_limit.remaining < 100:
                    reset_time = core_limit.reset
                    wait_seconds = (
                        reset_time - datetime.datetime.now(datetime.timezone.utc)
                    ).total_seconds()
                    if wait_seconds > 0:
                        logger.warning(
                            f"GitHub API rate limit low ({core_limit.remaining} remaining), "
                            f"waiting {wait_seconds:.0f}s until reset"
                        )
                        time.sleep(wait_seconds + 1)

                org = self.github.get_organization(selector.organization)
                repos = list(org.get_repos())
            except Exception as e:
                error_msg = str(e)
                # Check if it's an authentication error - don't print full traceback for these
                if (
                    "401" in error_msg
                    or "bad credentials" in error_msg.lower()
                    or "unauthorized" in error_msg.lower()
                ):
                    logger.error(
                        f"Authentication failed for GitHub organization {selector.organization}. Please check your token configuration."
                    )
                    continue
                else:
                    logger.exception(
                        f"Could not access GitHub organization {selector.organization}: {e}"
                    )
                    continue
            for repo in repos:
                m = re.match(selector.repo_name, repo.name)
                if not m:
                    continue
                try:
                    url = self.config.base_url + f"/{selector.organization}/{repo.name}"

                    # Fetch repository languages
                    languages = None
                    try:
                        languages = repo.get_languages()
                        logger.debug(
                            f"Retrieved {len(languages)} languages for {repo.name}: {list(languages.keys())}"
                        )
                    except Exception as lang_error:
                        logger.warning(
                            f"Failed to fetch languages for {repo.name}: {lang_error}"
                        )

                    repo_entity = V1GithubRepositoryEntity(
                        metadata=EntityMetadata(
                            name=repo.name,
                            namespace=self.config.namespace,
                            labels={"owner": selector.organization},
                        ),
                        spec=V1GithubRepositoryEntitySpec(
                            owner=selector.organization,
                            name=repo.name,
                            url=url,
                            description=repo.description
                            or "",  # Ensure consistent empty string instead of None
                            languages=languages,
                        ),
                    )
                    entities.append(repo_entity)

                    # Read graph files from repository
                    for file_path in selector.graph_files:
                        content = self._read_file_from_repo(repo, file_path)
                        if content:
                            file_entities, file_relations = parse_entity_file(
                                content=content,
                                source_name=repo.name,
                                file_path=file_path,
                                namespace=self.config.namespace,
                                additional_labels={"source-repository": repo.name},
                            )
                            entities.extend(file_entities)
                            # Store relations for later processing
                            if not hasattr(self, "_file_relations"):
                                self._file_relations = []
                            self._file_relations.extend(file_relations)

                            if file_entities or file_relations:
                                logger.info(
                                    f"Found {len(file_entities)} entities and {len(file_relations)} relations in {repo.name}:{file_path}"
                                )

                except Exception as e:
                    logger.exception(
                        f"Could not create entity for repo {repo.name}: {e}"
                    )
                    continue

        logger.info(f"GitHub provider discovered {len(entities)} total entities:")
        for entity in entities:
            logger.info(f"  - {entity.kind}: {entity.metadata.name} (ID: {entity.id})")
        return entities

    def _get_managed_entity_kinds(self) -> list[str]:
        """Get list of entity kinds managed by this GitHub provider.

        Returns:
            List of GitHub entity kind strings
        """
        return ["GithubRepository", "GithubHostingService"]

    def _read_file_from_repo(self, repo, file_path: str) -> str | None:
        """Read a file from a GitHub repository.

        Args:
            repo: GitHub repository object
            file_path: Path to the file in the repository

        Returns:
            File content as string, or None if file doesn't exist
        """
        try:
            file_content = repo.get_contents(file_path)
            if file_content.encoding == "base64":
                return b64decode(file_content.content).decode("utf-8")
            else:
                return file_content.decoded_content.decode("utf-8")
        except UnknownObjectException:
            logger.debug(f"File {file_path} not found in {repo.full_name}")
            return None
        except Exception as e:
            logger.warning(f"Error reading file {file_path} from {repo.full_name}: {e}")
            return None

    def _create_relations_for_entities(self, entities: list[Entity]) -> list:
        """Create relations for GitHub entities.

        Args:
            entities: Entities to create relations for

        Returns:
            List of relation objects
        """
        relations = []

        # Find hosting service and repositories
        github_host = None
        repositories = []

        logger.debug(f"Creating relations for {len(entities)} GitHub entities")

        for entity in entities:
            logger.debug(f"Processing entity: {entity.kind} - {entity.metadata.name}")
            if entity.kind == "GithubHostingService":
                github_host = entity
                logger.debug(f"Found GitHub host: {entity.metadata.name}")
            elif entity.kind == "GithubRepository":
                repositories.append(entity)
                logger.debug(f"Found repository: {entity.metadata.name}")

        # Create HOSTED_BY relations between repositories and hosting service
        if github_host:
            logger.debug(f"Creating {len(repositories)} HOSTED_BY relations")
            for repository in repositories:
                relation = self.create_relation_with_metadata(
                    GithubRepositoryHostedByRelation,
                    namespace=self.config.namespace,
                    source=repository.reference,
                    target=github_host.reference,
                )
                relations.append(relation)
                logger.debug(
                    f"Created relation: {repository.metadata.name} HOSTED_BY {github_host.metadata.name}"
                )
        else:
            logger.warning(
                "No GitHub hosting service found - cannot create HOSTED_BY relations"
            )

        # Add file-based relations
        if hasattr(self, "_file_relations"):
            relations.extend(self._file_relations)
            logger.info(f"Added {len(self._file_relations)} file-based relations")
            # Clear for next run
            self._file_relations = []

        logger.info(f"Created {len(relations)} total relations")
        return relations
