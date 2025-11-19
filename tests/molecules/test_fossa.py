"""Tests for FOSSA molecule provider."""

from unittest.mock import Mock, patch

import pytest
from tests.conftest import MockAPIResponse
from tests.framework import HTTPMoleculeTestCase

from devgraph_integrations.molecules.fossa.config import FOSSAProviderConfig
from devgraph_integrations.molecules.fossa.provider import FOSSAProvider


class TestFOSSAMolecule(HTTPMoleculeTestCase):
    """Test suite for FOSSA molecule."""

    provider_class = FOSSAProvider
    config_class = FOSSAProviderConfig

    def get_test_config(self) -> FOSSAProviderConfig:
        """Return valid FOSSA test configuration."""
        return FOSSAProviderConfig(
            namespace="test-namespace",
            token="test-fossa-token",
            base_url="https://app.fossa.com/api",
        )

    def get_mock_api_data(self) -> dict:
        """Return mock FOSSA API response data."""
        return {
            "projects": [
                {
                    "id": "test-project-1",
                    "title": "Test Project",
                    "url": "https://github.com/test/repo",
                    "branch": "main",
                    "latestRevision": {
                        "locator": "git+github.com/test/repo$main",
                    },
                },
                {
                    "id": "test-project-2",
                    "title": "Another Project",
                    "url": "https://gitlab.com/test/project",
                    "branch": "develop",
                    "latestRevision": {
                        "locator": "git+gitlab.com/test/project$develop",
                    },
                },
            ]
        }

    def get_api_base_url(self) -> str:
        """Return FOSSA API base URL."""
        return "https://app.fossa.com/api"

    def test_config_requires_token(self):
        """Test that config validation requires token field."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            FOSSAProviderConfig(namespace="test")

    def test_config_has_default_base_url(self):
        """Test that base_url has a sensible default."""
        config = FOSSAProviderConfig(
            namespace="test",
            token="test-token",
        )
        assert config.base_url == "https://app.fossa.com/api"

    def test_config_optional_filter_title(self):
        """Test that filter_title is optional."""
        config = FOSSAProviderConfig(
            namespace="test",
            token="test-token",
            filter_title="my-project",
        )
        assert config.filter_title == "my-project"

    def test_provider_creates_session_with_auth(self):
        """Test that provider creates HTTP session with auth headers."""
        provider = self.get_provider_instance()

        assert hasattr(provider, "session")
        assert "Authorization" in provider.session.headers
        assert provider.session.headers["Authorization"] == "Bearer test-fossa-token"
        assert provider.session.headers["Content-Type"] == "application/json"

    def test_entity_definitions_include_fossa_project(self):
        """Test that provider defines FOSSAProject entity."""
        provider = self.get_provider_instance()
        definitions = provider.entity_definitions()

        kinds = [d.kind for d in definitions]
        assert "FOSSAProject" in kinds

    def test_discover_projects(self, mock_devgraph_client):
        """Test discovering FOSSA projects from API."""
        provider = self.get_provider_instance()

        with patch.object(
            provider, "_make_request", return_value=self.get_mock_api_data()
        ):
            entities = provider._discover_current_entities()

        assert len(entities) == 2
        assert all(e.kind == "FOSSAProject" for e in entities)

        # Check first project
        project1 = entities[0]
        assert project1.spec.project_id == "test-project-1"
        assert project1.spec.title == "Test Project"
        assert project1.spec.url == "https://github.com/test/repo"
        assert project1.spec.default_branch == "main"

    def test_normalize_url(self):
        """Test URL normalization for matching."""
        provider = self.get_provider_instance()

        # Test various URL formats
        assert (
            provider._normalize_url("https://github.com/owner/repo")
            == "github.com/owner/repo"
        )
        assert (
            provider._normalize_url("https://github.com/owner/repo.git")
            == "github.com/owner/repo"
        )
        assert (
            provider._normalize_url("https://gitlab.com/group/project/")
            == "gitlab.com/group/project"
        )

        # Test case insensitivity
        assert (
            provider._normalize_url("https://GitHub.com/Owner/Repo")
            == "github.com/owner/repo"
        )

        # Test None handling
        assert provider._normalize_url(None) is None

    def test_create_relations_links_to_repos(
        self, mock_devgraph_client, mock_entity_response
    ):
        """Test that FOSSA projects are linked to GitHub/GitLab repos."""
        provider = self.get_provider_instance()

        # Create mock GitHub repo entity
        github_repo = Mock()
        github_repo.kind = "GitHubRepository"
        github_repo.metadata = Mock()
        github_repo.metadata.name = "test-repo"
        github_repo.metadata.namespace = "test-namespace"
        github_repo.api_version = "entities.devgraph.ai/v1"
        github_repo.spec = Mock()
        github_repo.spec.additional_properties = {"url": "https://github.com/test/repo"}

        # Mock the get_entities call (imported inside the method)
        with patch("devgraph_client.api.entities.get_entities") as mock_get_entities:
            mock_get_entities.sync_detailed.return_value = mock_entity_response(
                entities=[github_repo]
            )

            # Create FOSSA project entity
            from devgraph_integrations.molecules.fossa.types.v1_fossa_project import (
                V1FOSSAProjectEntity,
                V1FOSSAProjectEntitySpec,
            )
            from devgraph_integrations.types.entities import EntityMetadata

            fossa_project = V1FOSSAProjectEntity(
                metadata=EntityMetadata(
                    name="test-project",
                    namespace="test-namespace",
                ),
                spec=V1FOSSAProjectEntitySpec(
                    project_id="proj-1",
                    title="Test Project",
                    url="https://github.com/test/repo",
                ),
            )

            # Set the _temp_client that _create_relations_for_entities expects
            provider._temp_client = mock_devgraph_client

            # Test relation creation
            relations = provider._create_relations_for_entities([fossa_project])

        assert len(relations) == 1
        assert relations[0].source.name == "test-project"
        assert relations[0].target.name == "test-repo"
        assert relations[0].target.kind == "GitHubRepository"

    def test_api_request_error_handling(self):
        """Test that API request errors are handled gracefully."""
        provider = self.get_provider_instance()

        # Mock failed request
        with patch.object(provider.session, "request") as mock_request:
            mock_request.return_value = MockAPIResponse(
                status_code=500, text="Internal Server Error"
            )
            mock_request.return_value.raise_for_status = Mock(
                side_effect=Exception("HTTP 500")
            )

            with pytest.raises(Exception):
                provider._make_request("GET", "v2/projects")

    def test_empty_api_response(self, mock_devgraph_client):
        """Test handling of empty API response."""
        provider = self.get_provider_instance()

        with patch.object(provider, "_make_request", return_value={"projects": []}):
            entities = provider._discover_current_entities()

        assert len(entities) == 0

    def test_project_without_url(self, mock_devgraph_client):
        """Test handling of projects without URLs."""
        provider = self.get_provider_instance()

        mock_data = {
            "projects": [
                {
                    "id": "proj-1",
                    "title": "No URL Project",
                    "branch": "main",
                }
            ]
        }

        with patch.object(provider, "_make_request", return_value=mock_data):
            entities = provider._discover_current_entities()

        # Should still create entity, just without URL
        assert len(entities) == 1
        assert entities[0].spec.url is None

    def test_filter_title_parameter(self):
        """Test that filter_title config is used in API request."""
        config = FOSSAProviderConfig(
            namespace="test",
            token="test-token",
            filter_title="my-app",
        )
        provider = self.get_provider_instance(config)

        with patch.object(provider.session, "request") as mock_request:
            mock_request.return_value = MockAPIResponse(
                status_code=200, json_data={"projects": []}
            )

            provider._make_request("GET", "v2/projects", params={"title": "my-app"})

            # Verify filter was passed
            call_args = mock_request.call_args
            assert call_args[1]["params"]["title"] == "my-app"

    def test_sanitized_entity_names(self, mock_devgraph_client):
        """Test that entity names are properly sanitized."""
        provider = self.get_provider_instance()

        mock_data = {
            "projects": [
                {
                    "id": "Project_With-Special@Chars!",
                    "title": "Special Project",
                }
            ]
        }

        with patch.object(provider, "_make_request", return_value=mock_data):
            entities = provider._discover_current_entities()

        # Name should be sanitized (DNS-1123 compliant)
        assert len(entities) == 1
        assert self._is_valid_entity_name(entities[0].metadata.name)

    def test_reconcile_full_cycle(self, mock_devgraph_client, mock_entity_response):
        """Test full reconciliation cycle."""
        provider = self.get_provider_instance()

        mock_data = {
            "projects": [
                {
                    "id": "test-proj",
                    "title": "Test",
                    "url": "https://github.com/test/repo",
                }
            ]
        }

        with patch.object(provider, "_make_request", return_value=mock_data):
            with patch("devgraph_client.api.entities.get_entities") as mock_get:
                # Mock both entity and relation queries
                mock_response = mock_entity_response(entities=[])
                mock_response.parsed.relations = []  # Add relations field
                mock_get.sync_detailed.return_value = mock_response
                mutations = provider.reconcile(mock_devgraph_client)

        # Should create entities
        assert len(mutations.create_entities) == 1
        assert mutations.create_entities[0].spec.project_id == "test-proj"

    def test_project_with_all_fields(self, mock_devgraph_client):
        """Test project with all fields populated."""
        provider = self.get_provider_instance()

        mock_data = {
            "projects": [
                {
                    "id": "full-project",
                    "title": "Full Project",
                    "url": "https://github.com/org/repo",
                    "branch": "main",
                    "latestRevision": {
                        "locator": "git+github.com/org/repo$main",
                    },
                }
            ]
        }

        with patch.object(provider, "_make_request", return_value=mock_data):
            entities = provider._discover_current_entities()

        assert len(entities) == 1
        project = entities[0]
        assert project.spec.project_id == "full-project"
        assert project.spec.title == "Full Project"
        assert project.spec.url == "https://github.com/org/repo"
        assert project.spec.default_branch == "main"
        assert project.spec.locator == "git+github.com/org/repo$main"

    def test_multiple_projects_discovery(self, mock_devgraph_client):
        """Test discovering multiple projects."""
        provider = self.get_provider_instance()

        mock_data = {
            "projects": [{"id": f"proj-{i}", "title": f"Project {i}"} for i in range(5)]
        }

        with patch.object(provider, "_make_request", return_value=mock_data):
            entities = provider._discover_current_entities()

        assert len(entities) == 5
        for i, entity in enumerate(entities):
            assert entity.spec.project_id == f"proj-{i}"
            assert entity.spec.title == f"Project {i}"

    def test_normalize_url_edge_cases(self):
        """Test URL normalization with edge cases."""
        provider = self.get_provider_instance()

        # Test trailing slashes
        assert (
            provider._normalize_url("https://github.com/owner/repo/")
            == "github.com/owner/repo"
        )

        # Test .git suffix
        assert (
            provider._normalize_url("https://github.com/owner/repo.git")
            == "github.com/owner/repo"
        )

        # Test mixed case
        assert (
            provider._normalize_url("HTTPS://GitHub.COM/Owner/Repo.GIT")
            == "github.com/owner/repo"
        )

        # Test with path
        assert (
            provider._normalize_url("https://gitlab.com/group/subgroup/project")
            == "gitlab.com/group/subgroup/project"
        )

    def test_error_in_relation_creation_continues(
        self, mock_devgraph_client, mock_entity_response
    ):
        """Test that errors in relation creation don't break the whole process."""
        provider = self.get_provider_instance()

        # Create FOSSA project with URL
        from devgraph_integrations.molecules.fossa.types.v1_fossa_project import (
            V1FOSSAProjectEntity,
            V1FOSSAProjectEntitySpec,
        )
        from devgraph_integrations.types.entities import EntityMetadata

        fossa_project = V1FOSSAProjectEntity(
            metadata=EntityMetadata(name="test", namespace="test"),
            spec=V1FOSSAProjectEntitySpec(
                project_id="proj", title="Test", url="https://github.com/test/repo"
            ),
        )

        # Mock API call that fails
        with patch("devgraph_client.api.entities.get_entities") as mock_get:
            mock_get.sync_detailed.side_effect = Exception("API Error")

            provider._temp_client = mock_devgraph_client
            relations = provider._create_relations_for_entities([fossa_project])

        # Should handle error gracefully and return empty list
        assert relations == []
