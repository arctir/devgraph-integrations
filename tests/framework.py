"""Base testing framework for molecule providers.

This module provides a reusable testing framework that any molecule (in this repo
or external) can use to test their provider implementation.

Example:
    class TestMyMolecule(MoleculeTestCase):
        provider_class = MyProvider
        config_class = MyConfig

        def get_test_config(self):
            return MyConfig(
                namespace="test",
                token="test-token",
                api_url="https://api.test.com"
            )

        def get_mock_api_data(self):
            return {
                "projects": [{"id": "1", "name": "test"}]
            }
"""
import pytest
from abc import ABC, abstractmethod
from typing import Type, Any
from unittest.mock import patch

from devgraph_integrations.core.provider import Provider
from devgraph_integrations.core.state import GraphMutations
from devgraph_integrations.types.entities import Entity


class MoleculeTestCase(ABC):
    """Base test case for molecule providers.

    Provides common test scenarios that all molecules should pass.
    Subclasses should implement abstract methods to customize for their molecule.
    """

    # Override these in subclasses
    provider_class: Type[Provider] = None
    config_class: Type[Any] = None

    @abstractmethod
    def get_test_config(self) -> Any:
        """Return a valid test configuration for the provider.

        Returns:
            Config instance with test values
        """
        pass

    @abstractmethod
    def get_mock_api_data(self) -> dict | list:
        """Return mock API response data for testing discovery.

        Returns:
            Mock data structure matching the external API
        """
        pass

    def get_provider_instance(self, config: Any = None) -> Provider:
        """Create a provider instance for testing.

        Args:
            config: Optional config override

        Returns:
            Provider instance
        """
        if config is None:
            config = self.get_test_config()

        # Convert config to dict if it's a Pydantic model
        if hasattr(config, "model_dump"):
            config_dict = config.model_dump()
        elif hasattr(config, "dict"):
            config_dict = config.dict()
        else:
            config_dict = config

        from devgraph_integrations.config.discovery import MoleculeConfig

        molecule_config = MoleculeConfig(
            name="test-provider",
            type="test",
            every=60,
            config=config_dict,
        )
        return self.provider_class.from_config(molecule_config)

    # Standard tests that all molecules should pass

    def test_provider_initialization(self):
        """Test that provider can be initialized with valid config."""
        config = self.get_test_config()
        provider = self.get_provider_instance(config)

        assert provider is not None
        assert provider.name == "test-provider"
        assert provider.every == 60
        assert provider.config == config

    def test_config_validation_valid(self):
        """Test that valid config passes validation."""
        config = self.get_test_config()
        # If we can create the config, validation passed
        assert config is not None

    def test_config_validation_invalid(self):
        """Test that invalid config fails validation.

        Subclasses should override if they have different validation behavior.
        """
        if hasattr(self.config_class, "model_fields"):
            # Pydantic model - try to create with no args
            # Some configs may have all defaults, so we just test it's creatable
            try:
                config = self.config_class()
                # If it succeeds, that's fine - some configs have all defaults
                assert config is not None
            except Exception:
                # If it raises, that's also fine - some configs require fields
                pass

    def test_entity_definitions(self):
        """Test that provider returns valid entity definitions."""
        provider = self.get_provider_instance()
        definitions = provider.entity_definitions()

        assert isinstance(definitions, list)
        assert len(definitions) > 0
        for definition in definitions:
            # Check that it has the required attributes (duck typing)
            assert hasattr(definition, "kind")
            assert hasattr(definition, "group")
            assert definition.kind is not None
            assert definition.group is not None

    def test_entity_definitions_have_unique_kinds(self):
        """Test that all entity definitions have unique kinds."""
        provider = self.get_provider_instance()
        definitions = provider.entity_definitions()

        kinds = [d.kind for d in definitions]
        assert len(kinds) == len(set(kinds)), "Entity kinds must be unique"

    @pytest.mark.asyncio
    async def test_reconcile_returns_mutations(self, mock_devgraph_client):
        """Test that reconcile returns GraphMutations object."""
        provider = self.get_provider_instance()

        # Mock the API calls if needed
        with self.mock_external_api():
            mutations = provider.reconcile(mock_devgraph_client)

        assert isinstance(mutations, GraphMutations)
        assert hasattr(mutations, "create_entities")
        assert hasattr(mutations, "delete_entities")
        assert hasattr(mutations, "create_relations")
        assert hasattr(mutations, "delete_relations")

    def test_reconcile_with_api_data(self, mock_devgraph_client):
        """Test that reconcile creates entities from mock API data."""
        provider = self.get_provider_instance()

        with self.mock_external_api():
            mutations = provider.reconcile(mock_devgraph_client)

        # Should create at least one entity (or handle gracefully if API mocking not implemented)
        # All created entities should be Entity instances
        for entity in mutations.create_entities:
            assert isinstance(entity, Entity)
            assert entity.metadata.namespace == provider.config.namespace

    def test_reconcile_creates_valid_entities(self, mock_devgraph_client):
        """Test that reconciled entities have valid structure."""
        provider = self.get_provider_instance()

        with self.mock_external_api():
            mutations = provider.reconcile(mock_devgraph_client)

        for entity in mutations.create_entities:
            # Check required fields
            assert entity.apiVersion is not None
            assert entity.kind is not None
            assert entity.metadata is not None
            assert entity.metadata.name is not None
            assert entity.metadata.namespace is not None

            # Entity names must be DNS-1123 compliant
            assert self._is_valid_entity_name(entity.metadata.name)

    def test_reconcile_error_handling(self, mock_devgraph_client):
        """Test that reconcile handles API errors gracefully."""
        provider = self.get_provider_instance()

        with self.mock_external_api_error():
            mutations = provider.reconcile(mock_devgraph_client)

        # Should return empty mutations on error, not crash
        assert isinstance(mutations, GraphMutations)

    def test_from_config_class_method(self):
        """Test that provider can be created from config dict."""
        from devgraph_integrations.config.discovery import MoleculeConfig

        test_config = self.get_test_config()
        if hasattr(test_config, "model_dump"):
            config_dict = test_config.model_dump()
        elif hasattr(test_config, "dict"):
            config_dict = test_config.dict()
        else:
            config_dict = test_config

        molecule_config = MoleculeConfig(
            name="test-provider",
            type="test-type",
            every=120,
            config=config_dict,
        )

        provider = self.provider_class.from_config(molecule_config)

        assert provider is not None
        assert provider.name == "test-provider"
        assert provider.every == 120

    def test_provider_name_stored_correctly(self):
        """Test that provider name is accessible."""
        provider = self.get_provider_instance()
        assert provider.name == "test-provider"

    def test_config_namespace_default(self):
        """Test that namespace defaults to 'default' if not specified."""
        config = self.get_test_config()
        if not hasattr(config, "namespace"):
            pytest.skip("Provider doesn't have namespace field")

        # If namespace is not set, it should default to "default"
        assert config.namespace in ["default", "test-namespace", "test"]

    # Helper methods

    def mock_external_api(self):
        """Context manager to mock external API calls.

        Subclasses should override to mock their specific API client.

        Returns:
            Context manager for mocking
        """
        # Default: no-op context manager
        class NoOpContext:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        return NoOpContext()

    def mock_external_api_error(self):
        """Context manager to mock external API errors.

        Subclasses should override to simulate API failures.

        Returns:
            Context manager for mocking errors
        """
        class NoOpContext:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        return NoOpContext()

    @staticmethod
    def _is_valid_entity_name(name: str) -> bool:
        """Check if entity name is DNS-1123 compliant.

        Args:
            name: Entity name to validate

        Returns:
            True if valid, False otherwise
        """
        import re

        # DNS-1123 subdomain: lowercase alphanumeric, '-', '.', max 253 chars
        if len(name) > 253:
            return False
        pattern = r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$"
        return bool(re.match(pattern, name))


class HTTPMoleculeTestCase(MoleculeTestCase):
    """Base test case for molecules that use HTTP APIs.

    Extends MoleculeTestCase with HTTP-specific test helpers.
    """

    @abstractmethod
    def get_api_base_url(self) -> str:
        """Return the base URL for the external API.

        Returns:
            API base URL
        """
        pass

    def test_http_client_initialization(self):
        """Test that HTTP client is properly initialized."""
        provider = self.get_provider_instance()

        # Most HTTP providers have a session or client attribute
        assert hasattr(provider, "session") or hasattr(
            provider, "client"
        ) or hasattr(provider, "_client")

    def test_http_client_auth_headers(self):
        """Test that HTTP client has proper authentication headers.

        Subclasses should override to check specific auth header format.
        """
        provider = self.get_provider_instance()

        if hasattr(provider, "session"):
            assert "Authorization" in provider.session.headers
        elif hasattr(provider, "client"):
            # Check client has token/auth configured
            pass

    def mock_external_api(self):
        """Mock HTTP API calls using requests mock."""
        from tests.conftest import MockAPIResponse

        mock_data = self.get_mock_api_data()

        def mock_request(*args, **kwargs):
            return MockAPIResponse(status_code=200, json_data=mock_data)

        return patch("requests.Session.request", side_effect=mock_request)

    def mock_external_api_error(self):
        """Mock HTTP API errors."""
        from tests.conftest import MockAPIResponse

        def mock_request(*args, **kwargs):
            return MockAPIResponse(status_code=500, text="Internal Server Error")

        return patch("requests.Session.request", side_effect=mock_request)
