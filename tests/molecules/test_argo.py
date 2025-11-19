"""Tests for Argo CD molecule provider."""

import pytest
from tests.framework import HTTPMoleculeTestCase

from devgraph_integrations.molecules.argo.config import ArgoProviderConfig
from devgraph_integrations.molecules.argo.provider import ArgoProvider


class TestArgoMolecule(HTTPMoleculeTestCase):
    """Test suite for Argo CD molecule."""

    provider_class = ArgoProvider
    config_class = ArgoProviderConfig

    def get_test_config(self) -> ArgoProviderConfig:
        """Return valid Argo CD test configuration."""
        return ArgoProviderConfig(
            namespace="test-namespace",
            api_url="https://argocd.test.com/api/v1/",
            token="test-argo-token",
        )

    def get_mock_api_data(self) -> dict:
        """Return mock Argo CD API response data."""
        return {
            "items": [
                {
                    "metadata": {
                        "name": "test-app",
                        "namespace": "argocd",
                    },
                    "spec": {
                        "project": "default",
                        "source": {
                            "repoURL": "https://github.com/test/repo",
                            "path": "k8s",
                        },
                    },
                }
            ]
        }

    def get_api_base_url(self) -> str:
        """Return Argo CD API base URL."""
        return "https://argocd.test.com/api/v1/"

    def test_config_requires_api_url_and_token(self):
        """Test that config requires api_url and token."""
        with pytest.raises(Exception):
            ArgoProviderConfig(namespace="test")

    def test_entity_definitions_include_argo_types(self):
        """Test that provider defines Argo entity types."""
        provider = self.get_provider_instance()
        definitions = provider.entity_definitions()

        kinds = [d.kind for d in definitions]
        assert "ArgoInstance" in kinds
        assert "ArgoProject" in kinds
        assert "ArgoApplication" in kinds
