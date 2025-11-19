"""Pytest configuration and shared fixtures for molecule tests."""

from unittest.mock import Mock
from uuid import uuid4

import pytest
from devgraph_client.client import AuthenticatedClient

from devgraph_integrations.types.entities import EntityMetadata


@pytest.fixture
def mock_devgraph_client():
    """Create a mock Devgraph API client for testing.

    Returns:
        Mock AuthenticatedClient with common methods mocked
    """
    client = Mock(spec=AuthenticatedClient)
    client.base_url = "https://api.test.devgraph.ai"
    client.token = "test-token"
    return client


@pytest.fixture
def test_namespace():
    """Return a test namespace for entity creation.

    Returns:
        Standard test namespace string
    """
    return "test-namespace"


@pytest.fixture
def test_environment_id():
    """Return a test environment UUID.

    Returns:
        UUID for test environment
    """
    return uuid4()


@pytest.fixture
def sample_entity_metadata(test_namespace):
    """Create sample entity metadata for testing.

    Args:
        test_namespace: Test namespace from fixture

    Returns:
        EntityMetadata instance with test data
    """
    return EntityMetadata(
        name="test-entity",
        namespace=test_namespace,
        labels={"test": "true"},
    )


class MockAPIResponse:
    """Mock API response for testing HTTP clients."""

    def __init__(
        self,
        status_code: int = 200,
        json_data: dict | list | None = None,
        text: str = "",
        headers: dict | None = None,
    ):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.headers = headers or {}
        self.ok = 200 <= status_code < 300

    def json(self):
        """Return JSON data."""
        return self._json_data

    def raise_for_status(self):
        """Raise HTTPError for bad status codes."""
        if not self.ok:
            from requests import HTTPError

            raise HTTPError(f"HTTP {self.status_code}")


@pytest.fixture
def mock_requests_session(monkeypatch):
    """Create a mock requests.Session for HTTP testing.

    Usage:
        def test_something(mock_requests_session):
            mock_requests_session.get.return_value = MockAPIResponse(
                status_code=200,
                json_data={"key": "value"}
            )

    Returns:
        Mock Session object
    """
    import requests

    session_mock = Mock(spec=requests.Session)

    def mock_session_init(*args, **kwargs):
        return session_mock

    monkeypatch.setattr(requests, "Session", mock_session_init)
    return session_mock


@pytest.fixture
def mock_entity_response():
    """Create a mock entity query response.

    Returns:
        Function that creates mock responses with entities
    """

    def _create_response(entities: list = None, status_code: int = 200):
        response = Mock()
        response.status_code = status_code
        response.parsed = Mock()
        response.parsed.primary_entities = entities or []
        return response

    return _create_response
