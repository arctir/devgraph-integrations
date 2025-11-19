"""Tests for GitHub molecule provider."""

import pytest
from tests.framework import HTTPMoleculeTestCase

from devgraph_integrations.molecules.github.config import (
    GithubAppAuth,
    GithubPATAuth,
    GithubProviderConfig,
    GithubSelectorConfig,
)
from devgraph_integrations.molecules.github.provider import GithubProvider


class TestGitHubMolecule(HTTPMoleculeTestCase):
    """Test suite for GitHub molecule."""

    provider_class = GithubProvider
    config_class = GithubProviderConfig

    def get_test_config(self) -> GithubProviderConfig:
        """Return valid GitHub test configuration."""
        return GithubProviderConfig(
            namespace="test-namespace",
            authentication=GithubPATAuth(
                type="pat",
                token="ghp_test_token",
            ),
            selectors=[
                GithubSelectorConfig(
                    organization="test-org",
                    repo_name=".*",
                )
            ],
        )

    def get_mock_api_data(self) -> dict:
        """Return mock GitHub API response data."""
        return {
            "repositories": [
                {
                    "name": "test-repo",
                    "full_name": "test-org/test-repo",
                    "html_url": "https://github.com/test-org/test-repo",
                    "description": "Test repository",
                    "default_branch": "main",
                },
            ]
        }

    def get_api_base_url(self) -> str:
        """Return GitHub API base URL."""
        return "https://api.github.com"

    def test_config_requires_authentication(self):
        """Test that config validation requires authentication field."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            GithubProviderConfig(
                namespace="test",
                selectors=[],
            )

    def test_config_pat_authentication(self):
        """Test PAT authentication configuration."""
        config = GithubProviderConfig(
            namespace="test",
            authentication=GithubPATAuth(
                type="pat",
                token="ghp_token",
            ),
            selectors=[],
        )
        assert config.authentication.type == "pat"
        assert config.token == "ghp_token"

    def test_config_app_authentication(self):
        """Test GitHub App authentication configuration."""
        config = GithubProviderConfig(
            namespace="test",
            authentication=GithubAppAuth(
                type="app",
                app_id=12345,
                app_private_key="-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
                installation_id=67890,
            ),
            selectors=[],
        )
        assert config.authentication.type == "app"
        assert config.app_id == 12345
        assert config.installation_id == 67890

    def test_config_has_default_urls(self):
        """Test that API URLs have sensible defaults."""
        config = self.get_test_config()
        assert config.base_url == "https://github.com"
        assert config.api_url == "https://api.github.com"

    def test_selector_config_defaults(self):
        """Test GitHub selector configuration defaults."""
        selector = GithubSelectorConfig(organization="test-org")
        assert selector.repo_name == ".*"  # Match all by default
        assert selector.graph_files == [".devgraph.yaml"]

    def test_entity_definitions_include_github_types(self):
        """Test that provider defines GitHub entity types."""
        provider = self.get_provider_instance()
        definitions = provider.entity_definitions()

        kinds = [d.kind for d in definitions]
        # Check case-insensitively for repository and hosting service
        kinds_lower = [k.lower() for k in kinds]
        assert any(
            "repository" in k for k in kinds_lower
        ), f"No repository kind found in {kinds}"
        assert any(
            "hosting" in k for k in kinds_lower
        ), f"No hosting service kind found in {kinds}"

    def test_pat_auth_helper_properties(self):
        """Test authentication helper properties."""
        config = self.get_test_config()
        assert config.token == "ghp_test_token"
        assert config.app_id is None
        assert config.app_private_key is None

    def test_multiple_selectors(self):
        """Test configuration with multiple organization selectors."""
        config = GithubProviderConfig(
            namespace="test",
            authentication=GithubPATAuth(type="pat", token="test"),
            selectors=[
                GithubSelectorConfig(organization="org1"),
                GithubSelectorConfig(organization="org2", repo_name="^api-.*"),
            ],
        )
        assert len(config.selectors) == 2
        assert config.selectors[1].repo_name == "^api-.*"

    def test_custom_graph_files(self):
        """Test custom graph file paths in selector."""
        selector = GithubSelectorConfig(
            organization="test-org",
            graph_files=[".devgraph.yaml", ".devgraph/*.yaml"],
        )
        assert len(selector.graph_files) == 2
        assert ".devgraph/*.yaml" in selector.graph_files

    def test_app_auth_properties(self):
        """Test GitHub App authentication properties."""
        config = GithubProviderConfig(
            namespace="test",
            authentication=GithubAppAuth(
                type="app",
                app_id=12345,
                app_private_key="-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
                installation_id=67890,
            ),
            selectors=[],
        )
        assert config.app_id == 12345
        assert config.app_private_key is not None
        assert config.token is None

    def test_repo_name_filtering(self, mock_devgraph_client):
        """Test filtering repositories by name pattern."""
        config = GithubProviderConfig(
            namespace="test",
            authentication=GithubPATAuth(type="pat", token="test"),
            selectors=[
                GithubSelectorConfig(organization="test-org", repo_name="^api-.*"),
            ],
        )
        provider = self.get_provider_instance(config)

        # Provider should store the selector config
        assert len(provider.config.selectors) == 1
        assert provider.config.selectors[0].repo_name == "^api-.*"
