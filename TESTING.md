# Testing Framework

## Overview

Base test classes provide 15+ automatic tests for any molecule provider. Subclass `MoleculeTestCase` or `HTTPMoleculeTestCase`, implement 2-3 abstract methods, and get comprehensive test coverage automatically.

## Framework Structure

**`tests/framework.py`**
- `MoleculeTestCase` - Base class providing automatic tests for config validation, entity definitions, reconciliation, DNS-1123 compliance, and error handling
- `HTTPMoleculeTestCase` - Extends base with HTTP client testing and API mocking helpers

**`tests/conftest.py`** - Shared pytest fixtures:
- `mock_devgraph_client` - Mock authenticated client
- `mock_entity_response` - Factory for entity responses
- `MockAPIResponse` - HTTP response helper

**`pytest.ini`** - Test configuration with markers (unit, integration, molecule), async support, and output formatting

## Usage

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=devgraph_integrations

# Run specific molecule
poetry run pytest tests/molecules/test_fossa.py
```

## Writing Tests

Inherit from base classes and implement abstract methods:

```python
from tests.framework import HTTPMoleculeTestCase

class TestMyMolecule(HTTPMoleculeTestCase):
    provider_class = MyProvider
    config_class = MyProviderConfig

    def get_test_config(self):
        return MyProviderConfig(namespace="test", token="secret")

    def get_mock_api_data(self):
        return {"items": [{"id": 1, "name": "test"}]}

    # Inherits 15+ automatic tests
    # Add custom tests below
```

This gives you automatic tests for:
- Provider initialization
- Config validation (valid and invalid)
- Entity definitions structure
- Reconciliation
- DNS-1123 name compliance
- HTTP client setup (if using HTTPMoleculeTestCase)
- Error handling

## Current Coverage

| Module | Coverage | Tests |
|--------|----------|-------|
| FOSSA | 90% | 32 |
| GitHub Config | 98% | 25 |
| GitLab | 57% | 24 |
| Argo | 83% | 16 |
| Docker | 50% | 21 |
| File | 73% | 11 |

**Total: 135 tests, 128 passing, 7 skipped**
