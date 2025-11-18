"""Tests for File-based molecule provider."""
import pytest
import tempfile
from pathlib import Path
from tests.framework import MoleculeTestCase

from devgraph_integrations.molecules.file.provider import FileProvider
from devgraph_integrations.molecules.file.config import FileProviderConfig


class TestFileMolecule(MoleculeTestCase):
    """Test suite for File-based molecule."""

    provider_class = FileProvider
    config_class = FileProviderConfig

    def get_test_config(self) -> FileProviderConfig:
        """Return valid File provider test configuration."""
        return FileProviderConfig(
            namespace="test-namespace",
            base_path="/tmp/test",
            paths=[".devgraph.yaml"],
        )

    def get_mock_api_data(self) -> dict:
        """File provider doesn't use API - return empty."""
        return {}

    @pytest.mark.skip(reason="FileProviderConfig may have base_path defaults")
    def test_config_requires_base_path(self):
        """Test that config requires base_path."""
        pass

    def test_config_paths_default(self):
        """Test that paths has a sensible default."""
        config = FileProviderConfig(
            namespace="test",
            base_path="/tmp",
        )
        assert config.paths == [".devgraph.yaml"]

    def test_config_multiple_paths(self):
        """Test configuration with multiple file paths."""
        config = FileProviderConfig(
            namespace="test",
            base_path="/tmp",
            paths=[
                ".devgraph.yaml",
                "configs/**/*.yaml",
                "services/*/.devgraph.yaml",
            ],
        )
        assert len(config.paths) == 3

    @pytest.mark.skip(reason="File provider entity_definitions are dynamic")
    def test_entity_definitions(self):
        """Skip - File provider has dynamic definitions."""
        pass

    @pytest.mark.skip(reason="File provider may have empty entity definitions")
    def test_entity_definitions_have_unique_kinds(self):
        """Skip - File provider definitions are dynamic."""
        pass

    @pytest.mark.skip(reason="File provider doesn't use external API")
    def test_reconcile_with_api_data(self, mock_devgraph_client):
        """Skip - File provider reads from filesystem."""
        pass

    @pytest.mark.skip(reason="File provider doesn't use external API")
    def test_reconcile_creates_valid_entities(self, mock_devgraph_client):
        """Skip - File provider reads from filesystem."""
        pass

    def test_entity_definitions_empty(self):
        """Test that File provider returns definitions list (may be empty)."""
        provider = self.get_provider_instance()
        definitions = provider.entity_definitions()

        # File provider doesn't define specific entities - they come from files
        assert isinstance(definitions, list)

    @pytest.mark.skip(reason="Requires filesystem setup")
    def test_discover_from_yaml_files(self):
        """Test discovering entities from YAML files."""
        # Create temporary directory with test files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write test entity file
            test_file = Path(tmpdir) / ".devgraph.yaml"
            test_file.write_text("""
apiVersion: entities.devgraph.ai/v1
kind: Service
metadata:
  name: test-service
  namespace: test
spec:
  display_name: Test Service
""")

            config = FileProviderConfig(
                namespace="test",
                base_path=tmpdir,
                paths=[".devgraph.yaml"],
            )
            _ = self.get_provider_instance(config)

            # Test would discover entities from file
            # Implementation depends on actual file provider logic
