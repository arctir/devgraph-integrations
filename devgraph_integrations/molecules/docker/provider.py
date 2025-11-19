"""Docker registry provider for Devgraph molecule framework.

This module implements a provider that discovers and manages Docker registries,
repositories, images, and manifests as entities in the Devgraph system.
"""

import re
from typing import List, Optional

from loguru import logger

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.molecules.base.reconciliation import (
    FullStateReconciliation,
    ReconcilingMoleculeProvider,
)
from devgraph_integrations.types.entities import Entity

from .client import DockerRegistryClient
from .config import DockerProviderConfig
from .types import (
    V1DockerImageEntity,
    V1DockerImageEntityDefinition,
    V1DockerImageEntitySpec,
    V1DockerManifestEntity,
    V1DockerManifestEntityDefinition,
    V1DockerManifestEntitySpec,
    V1DockerRegistryEntity,
    V1DockerRegistryEntityDefinition,
    V1DockerRegistryEntitySpec,
    V1DockerRepositoryEntity,
    V1DockerRepositoryEntityDefinition,
    V1DockerRepositoryEntitySpec,
)


class DockerProvider(ReconcilingMoleculeProvider):
    """Provider for discovering Docker registries, repositories, and images.

    This provider connects to Docker registry APIs to discover registries,
    repositories, images, and manifests, creating corresponding entities and
    relationships in Devgraph.
    """

    _config_cls = DockerProviderConfig

    def __init__(
        self,
        name: str,
        every: int,
        config: DockerProviderConfig,
        reconciliation_strategy=None,
    ):
        """Initialize Docker provider.

        Args:
            name: Provider name
            every: Reconciliation interval in seconds
            config: Docker provider configuration
            reconciliation_strategy: Reconciliation strategy (optional)
        """
        if reconciliation_strategy is None:
            reconciliation_strategy = FullStateReconciliation()
        super().__init__(name, every, config, reconciliation_strategy)
        self.config = config
        self._client = None

    def _get_client(self) -> DockerRegistryClient:
        """Get or create Docker registry client."""
        if not self._client:
            self._client = DockerRegistryClient(
                base_url=self.config.api_url,
                token=self.config.token,
                username=self.config.username,
                password=self.config.password,
                registry_type=self.config.registry_type,
                timeout=self.config.timeout,
            )
        return self._client

    def entity_definitions(self) -> List[EntityDefinition]:
        """Return entity definitions this provider can create."""
        return [
            V1DockerRegistryEntityDefinition(),
            V1DockerRepositoryEntityDefinition(),
            V1DockerImageEntityDefinition(),
            V1DockerManifestEntityDefinition(),
        ]

    def _get_managed_entity_kinds(self) -> List[str]:
        """Get list of entity kinds managed by this Docker provider.

        Returns:
            List of Docker entity kind strings
        """
        return ["DockerRegistry", "DockerRepository", "DockerImage", "DockerManifest"]

    def _discover_current_entities(self) -> List[Entity]:
        """Discover all current entities from the Docker registry."""
        entities = []
        client = self._get_client()

        try:
            # Create registry entity
            registry_entity = self._create_registry_entity()
            entities.append(registry_entity)

            # Discover repositories
            if self.config.registry_type == "ghcr":
                # GHCR doesn't support /v2/_catalog endpoint
                # Use configured repository list from selectors instead
                repositories = self._get_ghcr_repositories()
                logger.info(
                    f"Using configured repository list for GHCR: {len(repositories)} repositories"
                )
            else:
                repositories = client.list_repositories()
                logger.info(f"Found {len(repositories)} repositories in registry")

            for repo_name in repositories:
                # Apply selector filters (skip for GHCR since we already filtered)
                if (
                    self.config.registry_type != "ghcr"
                    and not self._should_include_repository(repo_name)
                ):
                    logger.debug(
                        f"Skipping repository {repo_name} due to selector filters"
                    )
                    continue

                # Create repository entity
                repo_entity = self._create_repository_entity(repo_name)
                entities.append(repo_entity)

                # Discover images/tags for this repository
                tags = client.list_tags(repo_name)
                filtered_tags = self._filter_tags(tags)

                logger.debug(
                    f"Repository {repo_name}: found {len(tags)} tags, using {len(filtered_tags)}"
                )

                # Try to get source repository from the first image
                source_repository = None
                if filtered_tags:
                    try:
                        source_repository = client.get_source_repository(
                            repo_name, filtered_tags[0]
                        )
                        if source_repository:
                            logger.info(
                                f"Found source repository for {repo_name}: {source_repository}"
                            )
                            # Update the repository entity with source_repository
                            repo_entity.spec.source_repository = source_repository
                    except Exception as e:
                        logger.debug(
                            f"Could not extract source repository for {repo_name}: {e}"
                        )

                for tag in filtered_tags:
                    # Create image entity
                    image_entity = self._create_image_entity(repo_name, tag)
                    if image_entity:
                        entities.append(image_entity)

                        # Get manifest and create manifest entity
                        manifest_data = client.get_manifest(repo_name, tag)
                        if manifest_data:
                            manifest_entity = self._create_manifest_entity(
                                repo_name, manifest_data
                            )
                            if manifest_entity:
                                entities.append(manifest_entity)

        except Exception as e:
            logger.error(f"Error discovering Docker entities: {e}")

        logger.info(f"Discovered {len(entities)} total Docker entities")
        return entities

    def _create_registry_entity(self) -> V1DockerRegistryEntity:
        """Create registry entity."""
        registry_name = self._get_registry_name()

        return V1DockerRegistryEntity(
            metadata={
                "name": registry_name,
                "namespace": self.config.namespace,
                "labels": {
                    "devgraph.ai/provider": "docker",
                    "devgraph.ai/registry-type": self.config.registry_type,
                },
            },
            spec=V1DockerRegistryEntitySpec(
                name=registry_name,
                registry_type=self.config.registry_type,
                url=self.config.api_url,
                description=f"{self.config.registry_type} Docker registry",
                public=self.config.registry_type == "docker-hub",
            ),
        )

    def _create_repository_entity(self, repo_name: str) -> V1DockerRepositoryEntity:
        """Create repository entity."""
        # Parse namespace from repository name
        namespace = None
        if "/" in repo_name:
            namespace, short_name = repo_name.split("/", 1)
        else:
            short_name = repo_name

        return V1DockerRepositoryEntity(
            metadata={
                "name": self._sanitize_name(repo_name),
                "namespace": self.config.namespace,
                "labels": {
                    "devgraph.ai/provider": "docker",
                    "devgraph.ai/registry-type": self.config.registry_type,
                    "devgraph.ai/repository-name": repo_name,
                },
            },
            spec=V1DockerRepositoryEntitySpec(
                name=short_name,
                full_name=repo_name,
                namespace=namespace,
                registry_url=self.config.api_url,
            ),
        )

    def _create_image_entity(
        self, repo_name: str, tag: str
    ) -> Optional[V1DockerImageEntity]:
        """Create image entity."""
        try:
            client = self._get_client()
            manifest = client.get_manifest(repo_name, tag)

            # Extract metadata from manifest
            size = None
            architecture = None
            os_type = None
            digest = None
            layers = None

            if manifest:
                digest = manifest.get("digest")
                if "config" in manifest:
                    config = manifest["config"]
                    size = config.get("size")

                if "architecture" in manifest:
                    architecture = manifest["architecture"]
                if "os" in manifest:
                    os_type = manifest["os"]

                if "layers" in manifest:
                    layers = len(manifest["layers"])

            return V1DockerImageEntity(
                metadata={
                    "name": self._sanitize_name(f"{repo_name}-{tag}"),
                    "namespace": self.config.namespace,
                    "labels": {
                        "devgraph.ai/provider": "docker",
                        "devgraph.ai/registry-type": self.config.registry_type,
                        "devgraph.ai/repository-name": repo_name,
                        "devgraph.ai/image-tag": tag,
                    },
                },
                spec=V1DockerImageEntitySpec(
                    repository=repo_name,
                    tag=tag,
                    digest=digest,
                    size=size,
                    architecture=architecture,
                    os=os_type,
                    layers=layers,
                    registry_url=self.config.api_url,
                ),
            )
        except Exception as e:
            logger.error(f"Error creating image entity for {repo_name}:{tag}: {e}")
            return None

    def _create_manifest_entity(
        self, repo_name: str, manifest_data: dict
    ) -> Optional[V1DockerManifestEntity]:
        """Create manifest entity."""
        try:
            digest = manifest_data.get("digest", "unknown")
            media_type = manifest_data.get("mediaType", "unknown")
            schema_version = manifest_data.get("schemaVersion", 1)

            # Extract layer information
            layer_digests = []
            if "layers" in manifest_data:
                layer_digests = [
                    layer.get("digest", "") for layer in manifest_data["layers"]
                ]

            config_digest = None
            if "config" in manifest_data:
                config_digest = manifest_data["config"].get("digest")

            return V1DockerManifestEntity(
                metadata={
                    "name": self._sanitize_name(f"{repo_name}-manifest-{digest[:12]}"),
                    "namespace": self.config.namespace,
                    "labels": {
                        "devgraph.ai/provider": "docker",
                        "devgraph.ai/registry-type": self.config.registry_type,
                        "devgraph.ai/repository-name": repo_name,
                        "devgraph.ai/manifest-digest": digest,
                    },
                },
                spec=V1DockerManifestEntitySpec(
                    repository=repo_name,
                    digest=digest,
                    media_type=media_type,
                    schema_version=schema_version,
                    config_digest=config_digest,
                    layer_digests=layer_digests,
                    registry_url=self.config.api_url,
                ),
            )
        except Exception as e:
            logger.error(f"Error creating manifest entity for {repo_name}: {e}")
            return None

    def _should_include_repository(self, repo_name: str) -> bool:
        """Check if repository should be included based on selectors."""
        for selector in self.config.selectors:
            # Check namespace pattern
            repo_namespace = ""
            if "/" in repo_name:
                repo_namespace = repo_name.split("/")[0]

            if not re.match(selector.namespace_pattern, repo_namespace, re.IGNORECASE):
                continue

            # Check repository pattern
            if not re.match(selector.repository_pattern, repo_name, re.IGNORECASE):
                continue

            return True
        return False

    def _filter_tags(self, tags: List[str]) -> List[str]:
        """Filter tags based on selector criteria."""
        filtered = []

        for selector in self.config.selectors:
            selector_tags = tags.copy()

            # Include specific tags
            if selector.include_tags:
                selector_tags = [
                    tag for tag in selector_tags if tag in selector.include_tags
                ]

            # Exclude tags by pattern
            if selector.exclude_tags:
                for exclude_pattern in selector.exclude_tags:
                    selector_tags = [
                        tag
                        for tag in selector_tags
                        if not re.match(exclude_pattern, tag, re.IGNORECASE)
                    ]

            # Limit number of tags
            if selector.max_tags > 0:
                selector_tags = selector_tags[: selector.max_tags]

            filtered.extend(selector_tags)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(filtered))

    def _get_ghcr_repositories(self) -> List[str]:
        """Get repository list for GHCR using configured selectors.

        Since GHCR doesn't support /v2/_catalog, we need to construct
        repository names from the selector patterns.
        """
        repositories = []

        for selector in self.config.selectors:
            # For GHCR, repository names follow the pattern: namespace/repository
            namespace = (
                selector.namespace_pattern.replace(".*", "")
                .replace("^", "")
                .replace("$", "")
            )

            # Extract repository names from pattern
            repo_pattern = selector.repository_pattern

            if namespace and repo_pattern:
                # If both namespace and repo are specified, create the full name
                if "|" in repo_pattern:
                    # Handle patterns like "^(repo1|repo2|repo3)$"
                    repo_names = (
                        repo_pattern.replace("^", "")
                        .replace("$", "")
                        .replace("(", "")
                        .replace(")", "")
                        .split("|")
                    )
                    for repo_name in repo_names:
                        repositories.append(f"{namespace}/{repo_name.strip()}")
                elif "(" in repo_pattern and ")" in repo_pattern:
                    # Handle single repo patterns like "^(repo-name)$"
                    repo_name = (
                        repo_pattern.replace("^", "")
                        .replace("$", "")
                        .replace("(", "")
                        .replace(")", "")
                    )
                    repositories.append(f"{namespace}/{repo_name}")
                elif repo_pattern != "":
                    repositories.append(f"{namespace}/{repo_pattern}")

        if not repositories:
            logger.warning(
                "No specific repositories configured for GHCR. "
                "GHCR requires explicit repository names in selectors. "
                "Example: namespace_pattern: 'myorg', repository_pattern: '^(repo1|repo2)$'"
            )

        return repositories

    def _get_registry_name(self) -> str:
        """Get a normalized registry name."""
        if self.config.registry_type == "docker-hub":
            return "docker-hub"
        else:
            # Extract name from URL
            from urllib.parse import urlparse

            parsed = urlparse(self.config.api_url)
            return parsed.hostname or "docker-registry"

    def _sanitize_name(self, name: str) -> str:
        """Sanitize name for use as Kubernetes resource name."""
        # Replace invalid characters with dashes
        sanitized = re.sub(r"[^a-z0-9\-]", "-", name.lower())
        # Remove leading/trailing dashes
        sanitized = sanitized.strip("-")
        # Limit length
        return sanitized[:63] if len(sanitized) > 63 else sanitized

    def _create_relations_for_entities(self, entities: List[Entity]) -> List:
        """Create relations for Docker entities.

        Args:
            entities: Entities to create relations for

        Returns:
            List of relation objects
        """
        from .types.relations import (
            DockerImageBelongsToRepositoryRelation,
            DockerImageUsesManifestRelation,
            DockerManifestBelongsToRepositoryRelation,
            DockerRepositoryBelongsToRegistryRelation,
            DockerRepositoryBuiltFromGithubRepositoryRelation,
            GithubRepositoryBuildsDockerRepositoryRelation,
        )

        relations = []

        # Organize entities by type
        registry = None
        repositories = {}  # Map repository name to entity
        images = []
        manifests = {}  # Map manifest digest to entity
        github_repos = {}  # Map GitHub repo URL to entity

        logger.debug(f"Creating relations for {len(entities)} Docker entities")

        for entity in entities:
            if entity.kind == "DockerRegistry":
                registry = entity
                logger.debug(f"Found Docker registry: {entity.metadata.name}")
            elif entity.kind == "DockerRepository":
                # Use the full repository name as key
                repo_name = entity.spec.full_name
                repositories[repo_name] = entity
                logger.debug(f"Found repository: {repo_name}")
            elif entity.kind == "DockerImage":
                images.append(entity)
                logger.debug(f"Found image: {entity.metadata.name}")
            elif entity.kind == "DockerManifest":
                manifest_digest = entity.spec.digest
                manifests[manifest_digest] = entity
                logger.debug(f"Found manifest: {manifest_digest}")
            elif entity.kind == "GithubRepository":
                # Build a map of GitHub repo URLs for linking
                github_repos[entity.spec.url] = entity
                logger.debug(f"Found GitHub repository: {entity.spec.url}")

        # Create relations between repositories and registry
        if registry:
            logger.debug(
                f"Creating {len(repositories)} BELONGS_TO relations for repositories"
            )
            for repo_entity in repositories.values():
                relation = DockerRepositoryBelongsToRegistryRelation(
                    source=repo_entity.reference,
                    target=registry.reference,
                    namespace=self.config.namespace,
                )
                relations.append(relation)

        # Create BUILT_FROM/BUILDS relations between Docker and GitHub repositories
        logger.debug(
            f"Checking {len(repositories)} Docker repositories for source links"
        )
        for docker_repo in repositories.values():
            if (
                hasattr(docker_repo.spec, "source_repository")
                and docker_repo.spec.source_repository
            ):
                source_url = docker_repo.spec.source_repository
                # Normalize URL (remove .git suffix, trailing slashes, etc.)
                normalized_url = source_url.rstrip("/").replace(".git", "")

                # Try to find matching GitHub repository
                matching_repo = None
                for repo_url, repo_entity in github_repos.items():
                    if (
                        normalized_url == repo_url.rstrip("/")
                        or normalized_url in repo_url
                    ):
                        matching_repo = repo_entity
                        break

                if matching_repo:
                    # Create bidirectional relations
                    built_from_relation = (
                        DockerRepositoryBuiltFromGithubRepositoryRelation(
                            source=docker_repo.reference,
                            target=matching_repo.reference,
                            namespace=self.config.namespace,
                        )
                    )
                    relations.append(built_from_relation)

                    builds_relation = GithubRepositoryBuildsDockerRepositoryRelation(
                        source=matching_repo.reference,
                        target=docker_repo.reference,
                        namespace=self.config.namespace,
                    )
                    relations.append(builds_relation)

                    logger.info(
                        f"Created bidirectional relations: DockerRepo {docker_repo.metadata.name} <-> GithubRepo {matching_repo.metadata.name}"
                    )
                else:
                    logger.debug(
                        f"No matching GitHub repository found for Docker repo {docker_repo.metadata.name} with source URL: {source_url}"
                    )

        # Create relations between images and repositories
        logger.debug(f"Creating BELONGS_TO relations for {len(images)} images")
        for image in images:
            repo_name = image.spec.repository
            if repo_name in repositories:
                relation = DockerImageBelongsToRepositoryRelation(
                    source=image.reference,
                    target=repositories[repo_name].reference,
                    namespace=self.config.namespace,
                )
                relations.append(relation)
            else:
                logger.warning(
                    f"Repository {repo_name} not found for image {image.metadata.name}"
                )

        # Create relations between images and manifests, and manifests and repositories
        for image in images:
            # Get manifest digest from image (if available)
            if hasattr(image.spec, "digest") and image.spec.digest:
                manifest_digest = image.spec.digest
                if manifest_digest in manifests:
                    # Image USES manifest
                    relation = DockerImageUsesManifestRelation(
                        source=image.reference,
                        target=manifests[manifest_digest].reference,
                        namespace=self.config.namespace,
                    )
                    relations.append(relation)

        # Create relations between manifests and repositories
        logger.debug(f"Creating BELONGS_TO relations for {len(manifests)} manifests")
        for manifest in manifests.values():
            repo_name = manifest.spec.repository
            if repo_name in repositories:
                relation = DockerManifestBelongsToRepositoryRelation(
                    source=manifest.reference,
                    target=repositories[repo_name].reference,
                    namespace=self.config.namespace,
                )
                relations.append(relation)
            else:
                logger.warning(
                    f"Repository {repo_name} not found for manifest {manifest.metadata.name}"
                )

        logger.info(f"Created {len(relations)} Docker relations")
        return relations
