"""
Tests for relation ownership tracking and reconciliation.

This test suite covers:
- create_relation_with_metadata helper method
- Relation signature generation with ownership
- Ownership-based reconciliation logic
- File parser metadata population
- Typed relation specs (BuiltFromSpec, BuildsSpec)
"""
import pytest
from devgraph_integrations.types.entities import (
    EntityReference,
    EntityRelation,
    RelationMetadata,
)
from devgraph_integrations.molecules.base.reconciliation import (
    ReconcilingMoleculeProvider,
)
from devgraph_integrations.molecules.base.provider import MoleculeProvider
from devgraph_integrations.molecules.docker.types.relations import (
    DockerRepositoryBuiltFromGithubRepositoryRelation,
    GithubRepositoryBuildsDockerRepositoryRelation,
    BuiltFromSpec,
    BuildsSpec,
)
from devgraph_integrations.core.file_parser import (
    parse_entity_file,
    _create_relation_from_data,
    validate_entity_file_content,
)


class MockReconciliationProvider(ReconcilingMoleculeProvider):
    """Mock provider for testing reconciliation logic."""

    def __init__(self, name: str = "test-provider"):
        self.name = name
        # Initialize minimal provider attributes
        self.config = None

    async def fetch_entities(self):
        """Mock fetch_entities - not used in these tests."""
        return [], []

    def entity_definitions(self):
        """Mock entity_definitions - not used in these tests."""
        return []

    async def _discover_current_entities(self):
        """Mock _discover_current_entities - required abstract method."""
        return [], []

    def _get_managed_entity_kinds(self):
        """Mock _get_managed_entity_kinds - required abstract method."""
        return []


class TestCreateRelationWithMetadata:
    """Test the create_relation_with_metadata helper method."""

    def test_create_relation_with_default_metadata(self):
        """Test creating relation with default provider metadata."""
        provider = MockReconciliationProvider(name="docker")
        source = EntityReference(
            apiVersion="v1",
            kind="DockerRepository",
            name="my-app",
            namespace="default",
        )
        target = EntityReference(
            apiVersion="v1",
            kind="GithubRepository",
            name="my-repo",
            namespace="default",
        )

        relation = provider.create_relation_with_metadata(
            EntityRelation,
            source=source,
            target=target,
            relation="TEST_RELATION",
        )

        assert relation.metadata.labels["managed-by"] == "provider:docker"
        assert relation.metadata.labels["source-type"] == "discovered"
        assert relation.source == source
        assert relation.target == target
        assert relation.namespace == "default"

    def test_create_relation_with_custom_namespace(self):
        """Test creating relation with custom namespace."""
        provider = MockReconciliationProvider(name="ldap")
        source = EntityReference(
            apiVersion="v1",
            kind="User",
            name="john-doe",
            namespace="production",
        )
        target = EntityReference(
            apiVersion="v1",
            kind="Group",
            name="developers",
            namespace="production",
        )

        relation = provider.create_relation_with_metadata(
            EntityRelation,
            source=source,
            target=target,
            namespace="production",
            relation="MEMBER_OF",
        )

        assert relation.namespace == "production"
        assert relation.metadata.labels["managed-by"] == "provider:ldap"

    def test_create_relation_with_spec(self):
        """Test creating relation with spec data."""
        provider = MockReconciliationProvider(name="docker")
        source = EntityReference(
            apiVersion="v1",
            kind="DockerRepository",
            name="my-app",
            namespace="default",
        )
        target = EntityReference(
            apiVersion="v1",
            kind="GithubRepository",
            name="my-repo",
            namespace="default",
        )
        spec = {
            "dockerfile_path": "Dockerfile",
            "build_context": ".",
        }

        relation = provider.create_relation_with_metadata(
            EntityRelation,
            source=source,
            target=target,
            spec=spec,
            relation="BUILT_FROM",
        )

        assert relation.spec["dockerfile_path"] == "Dockerfile"
        assert relation.spec["build_context"] == "."
        assert relation.metadata.labels["managed-by"] == "provider:docker"

    def test_create_relation_with_additional_metadata(self):
        """Test creating relation with additional user metadata."""
        provider = MockReconciliationProvider(name="github")
        source = EntityReference(
            apiVersion="v1",
            kind="Repository",
            name="my-repo",
            namespace="default",
        )
        target = EntityReference(
            apiVersion="v1",
            kind="Team",
            name="my-team",
            namespace="default",
        )
        user_metadata = RelationMetadata(
            labels={"priority": "high", "team": "platform"},
            annotations={"description": "Critical repository"},
        )

        relation = provider.create_relation_with_metadata(
            EntityRelation,
            source=source,
            target=target,
            metadata=user_metadata,
            relation="HOSTED_BY",
        )

        # Should have both default and user labels
        assert relation.metadata.labels["managed-by"] == "provider:github"
        assert relation.metadata.labels["source-type"] == "discovered"
        assert relation.metadata.labels["priority"] == "high"
        assert relation.metadata.labels["team"] == "platform"
        assert relation.metadata.annotations["description"] == "Critical repository"

    def test_different_providers_different_ownership(self):
        """Test that different providers create different ownership labels."""
        providers = [
            MockReconciliationProvider(name="docker"),
            MockReconciliationProvider(name="ldap"),
            MockReconciliationProvider(name="github"),
        ]
        source = EntityReference(
            apiVersion="v1",
            kind="Component",
            name="test",
            namespace="default",
        )
        target = EntityReference(
            apiVersion="v1",
            kind="Component",
            name="test2",
            namespace="default",
        )

        relations = []
        for provider in providers:
            relation = provider.create_relation_with_metadata(
                EntityRelation,
                source=source,
                target=target,
                relation="TEST_RELATION",
            )
            relations.append(relation)

        assert relations[0].metadata.labels["managed-by"] == "provider:docker"
        assert relations[1].metadata.labels["managed-by"] == "provider:ldap"
        assert relations[2].metadata.labels["managed-by"] == "provider:github"


class TestRelationSignature:
    """Test relation signature generation with ownership."""

    def test_signature_includes_managed_by(self):
        """Test that signature includes managed-by label."""
        provider = MockReconciliationProvider(name="docker")
        source = EntityReference(
            apiVersion="v1",
            kind="DockerRepository",
            name="my-app",
            namespace="default",
        )
        target = EntityReference(
            apiVersion="v1",
            kind="GithubRepository",
            name="my-repo",
            namespace="default",
        )
        relation = provider.create_relation_with_metadata(
            EntityRelation,
            source=source,
            target=target,
            relation="TEST_RELATION",
        )
        relation.relation = "BUILT_FROM"

        signature = provider._get_relation_signature(relation)

        assert "provider:docker" in signature
        assert source.id in signature
        assert target.id in signature
        assert "BUILT_FROM" in signature

    def test_different_owners_different_signatures(self):
        """Test that relations with different owners have different signatures."""
        source = EntityReference(
            apiVersion="v1",
            kind="DockerRepository",
            name="my-app",
            namespace="default",
        )
        target = EntityReference(
            apiVersion="v1",
            kind="GithubRepository",
            name="my-repo",
            namespace="default",
        )

        provider1 = MockReconciliationProvider(name="docker")
        relation1 = provider1.create_relation_with_metadata(
            EntityRelation,
            source=source,
            target=target,
            relation="BUILT_FROM",
        )

        provider2 = MockReconciliationProvider(name="user")
        relation2 = provider2.create_relation_with_metadata(
            EntityRelation,
            source=source,
            target=target,
            relation="BUILT_FROM",
        )

        sig1 = provider1._get_relation_signature(relation1)
        sig2 = provider2._get_relation_signature(relation2)

        assert sig1 != sig2
        assert "provider:docker" in sig1
        assert "provider:user" in sig2


class TestFileParserMetadata:
    """Test file parser metadata population."""

    def test_parse_relation_with_metadata(self):
        """Test parsing relation from YAML with metadata."""
        content = """
relations:
  - relation: DEPENDS_ON
    source:
      apiVersion: v1
      kind: Component
      name: service-a
      namespace: default
    target:
      apiVersion: v1
      kind: Database
      name: db-a
      namespace: default
"""
        entities, relations = parse_entity_file(
            content=content,
            source_name="my-repo",
            file_path=".devgraph.yaml",
            namespace="default",
        )

        assert len(relations) == 1
        relation = relations[0]
        assert relation.metadata.labels["source-name"] == "my-repo"
        assert relation.metadata.labels["source-file"] == ".devgraph.yaml"
        assert relation.metadata.labels["source-type"] == "declared"
        assert relation.metadata.labels["managed-by"] == "file:my-repo"

    def test_parse_relation_with_spec(self):
        """Test parsing relation from YAML with spec."""
        content = """
relations:
  - relation: BUILT_FROM
    source:
      apiVersion: v1
      kind: DockerRepository
      name: my-app
      namespace: default
    target:
      apiVersion: v1
      kind: GithubRepository
      name: my-repo
      namespace: default
    spec:
      dockerfile_path: Dockerfile
      build_context: .
      workflow_file: .github/workflows/docker-build.yml
"""
        entities, relations = parse_entity_file(
            content=content,
            source_name="my-repo",
            file_path=".devgraph.yaml",
            namespace="default",
        )

        assert len(relations) == 1
        relation = relations[0]
        assert relation.spec["dockerfile_path"] == "Dockerfile"
        assert relation.spec["build_context"] == "."
        assert relation.spec["workflow_file"] == ".github/workflows/docker-build.yml"
        assert relation.metadata.labels["managed-by"] == "file:my-repo"

    def test_parse_multiple_relations_with_metadata(self):
        """Test parsing multiple relations with metadata."""
        content = """
relations:
  - relation: MEMBER_OF
    source:
      apiVersion: v1
      kind: Person
      name: john-doe
      namespace: default
    target:
      apiVersion: v1
      kind: Team
      name: developers
      namespace: default
  - relation: OWNS
    source:
      apiVersion: v1
      kind: Team
      name: developers
      namespace: default
    target:
      apiVersion: v1
      kind: Workstream
      name: backend
      namespace: default
"""
        entities, relations = parse_entity_file(
            content=content,
            source_name="org-repo",
            file_path=".devgraph.yaml",
            namespace="default",
        )

        assert len(relations) == 2
        for relation in relations:
            assert relation.metadata.labels["source-name"] == "org-repo"
            assert relation.metadata.labels["source-file"] == ".devgraph.yaml"
            assert relation.metadata.labels["source-type"] == "declared"
            assert relation.metadata.labels["managed-by"] == "file:org-repo"

    def test_validate_relation_with_spec(self):
        """Test validation of relation with spec field."""
        content = """
relations:
  - relation: BUILDS
    source:
      apiVersion: v1
      kind: GithubRepository
      name: my-repo
      namespace: default
    target:
      apiVersion: v1
      kind: DockerRepository
      name: my-app
      namespace: default
    spec:
      dockerfile_path: Dockerfile
      build_context: .
      target_tags:
        - latest
        - main
      build_on_push: true
"""
        is_valid, errors = validate_entity_file_content(
            content=content,
            source_name="my-repo",
            file_path=".devgraph.yaml",
        )

        assert is_valid
        assert len(errors) == 0


class TestTypedRelationSpecs:
    """Test typed relation spec classes."""

    def test_built_from_spec_creation(self):
        """Test creating BuiltFromSpec."""
        spec = BuiltFromSpec(
            dockerfile_path="Dockerfile",
            build_context=".",
            build_args={"NODE_ENV": "production"},
            workflow_file=".github/workflows/docker.yml",
            source_commit="abc123",
            source_branch="main",
        )
        assert spec.dockerfile_path == "Dockerfile"
        assert spec.build_context == "."
        assert spec.build_args["NODE_ENV"] == "production"
        assert spec.workflow_file == ".github/workflows/docker.yml"
        assert spec.source_commit == "abc123"
        assert spec.source_branch == "main"

    def test_built_from_spec_optional_fields(self):
        """Test BuiltFromSpec with optional fields."""
        spec = BuiltFromSpec(
            dockerfile_path="Dockerfile",
        )
        assert spec.dockerfile_path == "Dockerfile"
        assert spec.build_context is None
        assert spec.build_args == {}
        assert spec.workflow_file is None

    def test_builds_spec_creation(self):
        """Test creating BuildsSpec."""
        spec = BuildsSpec(
            dockerfile_path="Dockerfile",
            build_context=".",
            build_args={"APP_VERSION": "1.0.0"},
            workflow_file=".github/workflows/build.yml",
            target_tags=["latest", "main", "v1.0.0"],
            build_on_push=True,
        )
        assert spec.dockerfile_path == "Dockerfile"
        assert spec.build_context == "."
        assert spec.build_args["APP_VERSION"] == "1.0.0"
        assert len(spec.target_tags) == 3
        assert spec.build_on_push is True

    def test_builds_spec_optional_fields(self):
        """Test BuildsSpec with optional fields."""
        spec = BuildsSpec()
        assert spec.dockerfile_path is None
        assert spec.build_context is None
        assert spec.build_args == {}
        assert spec.workflow_file is None
        assert spec.target_tags == []  # default_factory=list makes this []
        assert spec.build_on_push is None

    def test_built_from_relation_with_typed_spec(self):
        """Test creating DockerRepositoryBuiltFromGithubRepositoryRelation with typed spec."""
        source = EntityReference(
            apiVersion="v1",
            kind="DockerRepository",
            name="my-app",
            namespace="default",
        )
        target = EntityReference(
            apiVersion="v1",
            kind="GithubRepository",
            name="my-repo",
            namespace="default",
        )
        spec = BuiltFromSpec(
            dockerfile_path="Dockerfile",
            build_context=".",
        )
        relation = DockerRepositoryBuiltFromGithubRepositoryRelation(
            source=source,
            target=target,
            spec=spec,
        )
        assert isinstance(relation.spec, BuiltFromSpec)
        assert relation.spec.dockerfile_path == "Dockerfile"
        assert relation.relation == "BUILT_FROM"

    def test_built_from_relation_with_dict_spec(self):
        """Test creating DockerRepositoryBuiltFromGithubRepositoryRelation with dict spec."""
        source = EntityReference(
            apiVersion="v1",
            kind="DockerRepository",
            name="my-app",
            namespace="default",
        )
        target = EntityReference(
            apiVersion="v1",
            kind="GithubRepository",
            name="my-repo",
            namespace="default",
        )
        spec_dict = {
            "dockerfile_path": "Dockerfile",
            "build_context": ".",
            "build_args": {"ENV": "prod"},
        }
        relation = DockerRepositoryBuiltFromGithubRepositoryRelation(
            source=source,
            target=target,
            spec=spec_dict,
        )
        # Should auto-convert dict to BuiltFromSpec
        assert isinstance(relation.spec, BuiltFromSpec)
        assert relation.spec.dockerfile_path == "Dockerfile"
        assert relation.spec.build_args["ENV"] == "prod"

    def test_builds_relation_with_typed_spec(self):
        """Test creating GithubRepositoryBuildsDockerRepositoryRelation with typed spec."""
        source = EntityReference(
            apiVersion="v1",
            kind="GithubRepository",
            name="my-repo",
            namespace="default",
        )
        target = EntityReference(
            apiVersion="v1",
            kind="DockerRepository",
            name="my-app",
            namespace="default",
        )
        spec = BuildsSpec(
            dockerfile_path="Dockerfile",
            target_tags=["latest", "main"],
            build_on_push=True,
        )
        relation = GithubRepositoryBuildsDockerRepositoryRelation(
            source=source,
            target=target,
            spec=spec,
        )
        assert isinstance(relation.spec, BuildsSpec)
        assert len(relation.spec.target_tags) == 2
        assert relation.spec.build_on_push is True
        assert relation.relation == "BUILDS"

    def test_builds_relation_with_dict_spec(self):
        """Test creating GithubRepositoryBuildsDockerRepositoryRelation with dict spec."""
        source = EntityReference(
            apiVersion="v1",
            kind="GithubRepository",
            name="my-repo",
            namespace="default",
        )
        target = EntityReference(
            apiVersion="v1",
            kind="DockerRepository",
            name="my-app",
            namespace="default",
        )
        spec_dict = {
            "dockerfile_path": "Dockerfile",
            "target_tags": ["latest"],
            "build_on_push": False,
        }
        relation = GithubRepositoryBuildsDockerRepositoryRelation(
            source=source,
            target=target,
            spec=spec_dict,
        )
        # Should auto-convert dict to BuildsSpec
        assert isinstance(relation.spec, BuildsSpec)
        assert relation.spec.target_tags == ["latest"]
        assert relation.spec.build_on_push is False


class TestOwnershipBasedReconciliation:
    """Test ownership-based reconciliation logic."""

    def test_relation_signature_with_ownership(self):
        """Test that relation signatures include ownership information."""
        provider = MockReconciliationProvider(name="docker")
        source = EntityReference(
            apiVersion="v1",
            kind="DockerRepository",
            name="app",
            namespace="default",
        )
        target = EntityReference(
            apiVersion="v1",
            kind="GithubRepository",
            name="repo",
            namespace="default",
        )

        relation1 = provider.create_relation_with_metadata(
            EntityRelation,
            source=source,
            target=target,
            relation="BUILT_FROM",
        )

        relation2 = EntityRelation(
            source=source,
            target=target,
            relation="BUILT_FROM",
            metadata=RelationMetadata(
                labels={"managed-by": "file:my-repo"}
            ),
        )

        sig1 = provider._get_relation_signature(relation1)
        sig2 = provider._get_relation_signature(relation2)

        # Same source/target/relation but different ownership = different signatures
        assert sig1 != sig2
        assert "provider:docker" in sig1
        assert "file:my-repo" in sig2

    def test_provider_only_reconciles_owned_relations(self):
        """Test that provider reconciliation respects ownership."""
        provider = MockReconciliationProvider(name="docker")

        # Create relations with different ownership
        source = EntityReference(
            apiVersion="v1",
            kind="DockerRepository",
            name="app",
            namespace="default",
        )
        target = EntityReference(
            apiVersion="v1",
            kind="GithubRepository",
            name="repo",
            namespace="default",
        )

        # Provider-owned relation
        provider_relation = provider.create_relation_with_metadata(
            EntityRelation,
            source=source,
            target=target,
            relation="BUILT_FROM",
        )

        # File-owned relation (should not be managed by provider)
        file_relation = EntityRelation(
            source=source,
            target=target,
            relation="BUILT_FROM",
            metadata=RelationMetadata(
                labels={"managed-by": "file:my-repo"}
            ),
        )

        # User-created relation (should not be managed by provider)
        user_relation = EntityRelation(
            source=source,
            target=target,
            relation="BUILT_FROM",
            metadata=RelationMetadata(
                labels={"managed-by": "user:admin"}
            ),
        )

        # Check ownership
        assert provider_relation.metadata.labels.get("managed-by") == "provider:docker"
        assert file_relation.metadata.labels.get("managed-by") == "file:my-repo"
        assert user_relation.metadata.labels.get("managed-by") == "user:admin"
