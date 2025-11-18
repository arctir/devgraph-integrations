"""Tests for GitLab molecule provider."""
import pytest
from unittest.mock import Mock
from tests.framework import HTTPMoleculeTestCase
from gitlab.exceptions import GitlabGetError

from devgraph_integrations.molecules.gitlab.provider import GitlabProvider
from devgraph_integrations.molecules.gitlab.config import (
    GitlabProviderConfig,
    GitlabSelectorConfig,
)


class TestGitLabMolecule(HTTPMoleculeTestCase):
    """Test suite for GitLab molecule."""

    provider_class = GitlabProvider
    config_class = GitlabProviderConfig

    def get_test_config(self) -> GitlabProviderConfig:
        """Return valid GitLab test configuration."""
        return GitlabProviderConfig(
            namespace="test-namespace",
            token="glpat_test_token",
            selectors=[
                GitlabSelectorConfig(
                    group="test-group",
                )
            ],
        )

    def get_mock_api_data(self) -> dict:
        """Return mock GitLab API response data."""
        return {
            "projects": [
                {
                    "id": 123,
                    "name": "test-project",
                    "path_with_namespace": "test-group/test-project",
                    "web_url": "https://gitlab.com/test-group/test-project",
                    "description": "Test project",
                    "default_branch": "main",
                }
            ]
        }

    def get_api_base_url(self) -> str:
        """Return GitLab API base URL."""
        return "https://gitlab.com/api/v4"

    def test_config_requires_token(self):
        """Test that config validation requires token field."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            GitlabProviderConfig(
                namespace="test",
                selectors=[],
            )

    def test_config_has_default_urls(self):
        """Test that URLs have sensible defaults for GitLab.com."""
        config = self.get_test_config()
        assert config.base_url == "https://gitlab.com"
        assert config.api_url == "https://gitlab.com/api/v4"

    def test_config_self_hosted_gitlab(self):
        """Test configuration for self-hosted GitLab instance."""
        config = GitlabProviderConfig(
            namespace="test",
            token="test-token",
            base_url="https://gitlab.company.com",
            api_url="https://gitlab.company.com/api/v4",
            selectors=[],
        )
        assert "gitlab.company.com" in config.base_url
        assert "gitlab.company.com" in config.api_url

    def test_selector_config_defaults(self):
        """Test GitLab selector configuration defaults."""
        selector = GitlabSelectorConfig(group="test-group")
        assert selector.project_name == ".*"  # Match all by default
        assert selector.graph_files == [".devgraph.yaml"]

    def test_entity_definitions_include_gitlab_types(self):
        """Test that provider defines GitLab entity types."""
        provider = self.get_provider_instance()
        definitions = provider.entity_definitions()

        kinds = [d.kind for d in definitions]
        # Check case-insensitively for project and hosting service
        kinds_lower = [k.lower() for k in kinds]
        assert any("project" in k and "git" in k for k in kinds_lower), f"No GitLab project kind found in {kinds}"
        assert any("hosting" in k for k in kinds_lower), f"No hosting service kind found in {kinds}"

    def test_multiple_group_selectors(self):
        """Test configuration with multiple group selectors."""
        config = GitlabProviderConfig(
            namespace="test",
            token="test-token",
            selectors=[
                GitlabSelectorConfig(group="group1"),
                GitlabSelectorConfig(group="group2", project_name="^api-.*"),
            ],
        )
        assert len(config.selectors) == 2
        assert config.selectors[1].project_name == "^api-.*"

    def test_custom_graph_files(self):
        """Test custom graph file paths in selector."""
        selector = GitlabSelectorConfig(
            group="test-group",
            graph_files=[".devgraph.yaml", "config/.devgraph.yaml"],
        )
        assert len(selector.graph_files) == 2

    def test_error_handling_invalid_group(self, mock_devgraph_client):
        """Test error handling when group doesn't exist."""
        config = self.get_test_config()
        provider = self.get_provider_instance(config)

        # Mock GitLab client to raise error
        mock_gitlab = Mock()
        mock_gitlab.groups.get = Mock(side_effect=GitlabGetError("Group not found"))
        provider.gitlab = mock_gitlab

        # Should handle error gracefully
        mutations = provider.reconcile(mock_devgraph_client)
        assert mutations is not None

    def test_devgraph_file_parsing(self, mock_devgraph_client):
        """Test parsing .devgraph.yaml from project."""
        config = self.get_test_config()
        provider = self.get_provider_instance(config)

        # Mock GitLab client with project containing devgraph file
        mock_gitlab = Mock()
        mock_group = Mock()
        mock_project = Mock()
        mock_project.id = 123
        mock_project.name = "test-project"
        mock_project.path_with_namespace = "test-group/test-project"
        mock_project.web_url = "https://gitlab.com/test-group/test-project"
        mock_project.description = "Test project"
        mock_project.default_branch = "main"

        # Mock devgraph file content
        mock_file = Mock()
        mock_file.decode = Mock(return_value=b"entities: []")
        mock_project.files.get = Mock(return_value=mock_file)

        mock_group.projects.list = Mock(return_value=[mock_project])
        mock_gitlab.groups.get = Mock(return_value=mock_group)
        provider.gitlab = mock_gitlab

        # Should not raise error
        mutations = provider.reconcile(mock_devgraph_client)
        assert mutations is not None

    def test_multiple_selectors_processing(self, mock_devgraph_client):
        """Test processing multiple group selectors."""
        config = GitlabProviderConfig(
            namespace="test",
            token="test-token",
            selectors=[
                GitlabSelectorConfig(group="group1"),
                GitlabSelectorConfig(group="group2"),
            ],
        )
        provider = self.get_provider_instance(config)

        # Mock GitLab client
        mock_gitlab = Mock()

        def get_group(group_id):
            mock_group = Mock()
            mock_group.projects.list = Mock(return_value=[])
            return mock_group

        mock_gitlab.groups.get = Mock(side_effect=get_group)
        provider.gitlab = mock_gitlab

        _ = provider.reconcile(mock_devgraph_client)

        # Should call groups.get for each selector
        assert mock_gitlab.groups.get.call_count == 2
