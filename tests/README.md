# Testing Framework for Devgraph Integrations

This directory contains the test suite for devgraph-integrations molecules.

## Structure

```
tests/
├── conftest.py           # Shared pytest fixtures
├── framework.py          # Base test framework for molecules
├── molecules/            # Molecule-specific tests
│   ├── test_github.py
│   ├── test_gitlab.py
│   ├── test_fossa.py
│   └── ...
└── README.md            # This file
```

## Running Tests

### Run all tests

```bash
poetry run pytest
```

### Run tests for a specific molecule

```bash
poetry run pytest tests/molecules/test_github.py
```

### Run with coverage

```bash
poetry run pytest --cov=devgraph_integrations --cov-report=html
```

### Run only unit tests (fast)

```bash
poetry run pytest -m unit
```

### Run specific test by name

```bash
poetry run pytest -k test_config_validation
```

## Test Categories

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Fast unit tests with no external dependencies
- `@pytest.mark.integration` - Integration tests (may require services)
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.molecule` - Molecule provider tests
- `@pytest.mark.config` - Configuration validation tests

## Writing Tests for Molecules

### Using the Base Test Framework

The `tests/framework.py` module provides base classes that any molecule can extend:

#### For HTTP-based molecules:

```python
from tests.framework import HTTPMoleculeTestCase
from your_molecule.provider import YourProvider
from your_molecule.config import YourConfig

class TestYourMolecule(HTTPMoleculeTestCase):
    provider_class = YourProvider
    config_class = YourConfig

    def get_test_config(self) -> YourConfig:
        return YourConfig(
            namespace="test",
            token="test-token",
        )

    def get_mock_api_data(self) -> dict:
        return {"items": [{"id": "1", "name": "test"}]}

    def get_api_base_url(self) -> str:
        return "https://api.yourservice.com"
```

#### For non-HTTP molecules:

```python
from tests.framework import MoleculeTestCase

class TestYourMolecule(MoleculeTestCase):
    provider_class = YourProvider
    config_class = YourConfig

    def get_test_config(self) -> YourConfig:
        return YourConfig(namespace="test")

    def get_mock_api_data(self) -> dict:
        return {}  # Not used for non-HTTP molecules
```

### Base Tests Provided

When you extend `MoleculeTestCase`, you automatically get these tests:

- ✅ Provider initialization
- ✅ Config validation (valid and invalid)
- ✅ Entity definition generation
- ✅ Entity definition uniqueness
- ✅ Reconciliation returns GraphMutations
- ✅ Entities have valid structure
- ✅ Entity names are DNS-1123 compliant
- ✅ Error handling
- ✅ from_config class method
- ✅ Namespace defaults

For HTTP molecules, you also get:
- ✅ HTTP client initialization
- ✅ Authentication headers

### Adding Custom Tests

Add molecule-specific tests alongside the base tests:

```python
class TestYourMolecule(HTTPMoleculeTestCase):
    # ... base configuration ...

    def test_specific_feature(self):
        """Test molecule-specific functionality."""
        provider = self.get_provider_instance()
        # Your test logic here
        assert provider.some_feature() == expected_value

    def test_relation_creation(self, mock_devgraph_client):
        """Test that relations are created correctly."""
        provider = self.get_provider_instance()
        # Mock API responses
        with patch.object(provider, '_make_request') as mock_request:
            mock_request.return_value = self.get_mock_api_data()
            mutations = provider.reconcile(mock_devgraph_client)

        assert len(mutations.create_relations) > 0
```

## Fixtures

### Available fixtures (from conftest.py):

- `mock_devgraph_client` - Mock AuthenticatedClient for API calls
- `test_namespace` - Standard test namespace ("test-namespace")
- `test_environment_id` - Test environment UUID
- `sample_entity_metadata` - Sample EntityMetadata for testing
- `mock_requests_session` - Mock requests.Session for HTTP testing
- `mock_entity_response` - Helper to create mock entity query responses

### Using fixtures:

```python
def test_with_fixtures(self, mock_devgraph_client, test_namespace):
    """Test using pytest fixtures."""
    provider = self.get_provider_instance()
    mutations = provider.reconcile(mock_devgraph_client)

    assert mutations.create_entities[0].metadata.namespace == test_namespace
```

## Mocking External APIs

### Mock HTTP responses:

```python
from tests.conftest import MockAPIResponse

def test_api_call(self, mock_requests_session):
    mock_requests_session.get.return_value = MockAPIResponse(
        status_code=200,
        json_data={"result": "success"}
    )

    provider = self.get_provider_instance()
    result = provider.fetch_data()
    assert result["result"] == "success"
```

### Mock API errors:

```python
def test_api_error_handling(self, mock_requests_session):
    mock_requests_session.get.return_value = MockAPIResponse(
        status_code=500,
        text="Internal Server Error"
    )

    provider = self.get_provider_instance()
    mutations = provider.reconcile(mock_devgraph_client)

    # Should handle gracefully
    assert isinstance(mutations, GraphMutations)
```

## Testing External Molecules

The testing framework can be used by external molecule repositories:

1. Install devgraph-integrations as a dev dependency:
```bash
poetry add --group dev devgraph-integrations
```

2. Import and extend the base test class:
```python
from devgraph_integrations.tests.framework import MoleculeTestCase

class TestMyExternalMolecule(MoleculeTestCase):
    # Your tests here
```

3. Run with pytest:
```bash
pytest
```

## Best Practices

### 1. Test Configuration Variations

```python
def test_config_with_optional_fields(self):
    """Test configuration with all optional fields."""
    config = YourConfig(
        namespace="test",
        token="test",
        optional_field="value",
        another_optional=123,
    )
    assert config.optional_field == "value"
```

### 2. Test Error Conditions

```python
def test_handles_missing_data_gracefully(self):
    """Test that provider handles missing API data."""
    provider = self.get_provider_instance()

    with patch.object(provider, '_make_request', return_value={}):
        entities = provider._discover_current_entities()

    # Should return empty, not crash
    assert entities == []
```

### 3. Test Entity Name Sanitization

```python
def test_sanitizes_invalid_entity_names(self):
    """Test that invalid names are sanitized."""
    provider = self.get_provider_instance()

    mock_data = {"items": [{"id": "Invalid@Name!", "title": "Test"}]}

    with patch.object(provider, '_make_request', return_value=mock_data):
        entities = provider._discover_current_entities()

    # Name should be DNS-1123 compliant
    assert self._is_valid_entity_name(entities[0].metadata.name)
```

### 4. Test Relationship Creation

```python
def test_creates_correct_relationships(self, mock_devgraph_client):
    """Test that relationships are created between entities."""
    provider = self.get_provider_instance()

    # Setup mock entities
    with patch('your_module.get_entities') as mock_get:
        mock_get.sync_detailed.return_value = mock_entity_response(
            entities=[mock_target_entity]
        )

        relations = provider._create_relations_for_entities([source_entity])

    assert len(relations) == 1
    assert relations[0].source == source_entity.reference
    assert relations[0].target == mock_target_entity.reference
```

## Continuous Integration

Add to your CI pipeline (GitHub Actions example):

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install poetry
      - run: poetry install
      - run: poetry run pytest --cov --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Debugging Tests

### Run with verbose output:

```bash
poetry run pytest -vv
```

### Show print statements:

```bash
poetry run pytest -s
```

### Drop into debugger on failure:

```bash
poetry run pytest --pdb
```

### Run specific test with debugging:

```bash
poetry run pytest tests/molecules/test_fossa.py::TestFOSSAMolecule::test_normalize_url -vv -s
```

## Contributing

When adding a new molecule:

1. Create `tests/molecules/test_yourmolecule.py`
2. Extend `MoleculeTestCase` or `HTTPMoleculeTestCase`
3. Implement required abstract methods
4. Add molecule-specific tests
5. Ensure all tests pass: `poetry run pytest`
6. Aim for >80% code coverage

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [unittest.mock guide](https://docs.python.org/3/library/unittest.mock.html)
- [Pydantic testing](https://docs.pydantic.dev/latest/concepts/validation/)
