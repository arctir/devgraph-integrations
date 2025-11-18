"""File provider for Devgraph molecule framework.

This module implements a provider that discovers and manages entities and
relations from .devgraph.yaml files on disk.
"""

import os
from pathlib import Path
from glob import glob
from typing import List
from loguru import logger

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntityRelation
from devgraph_integrations.molecules.base.reconciliation import (
    ReconcilingMoleculeProvider,
    FullStateReconciliation,
)
from devgraph_integrations.core.file_parser import parse_entity_file

from .config import FileProviderConfig


class FileProvider(ReconcilingMoleculeProvider):
    """Provider for discovering entities and relations from .devgraph.yaml files.

    This provider reads .devgraph.yaml files from disk and creates corresponding
    entities and relationships in Devgraph.
    """

    _config_cls = FileProviderConfig

    def __init__(
        self,
        name: str,
        every: int,
        config: FileProviderConfig,
        reconciliation_strategy=None,
    ):
        """Initialize File provider.

        Args:
            name: Provider name
            every: Reconciliation interval in seconds
            config: File provider configuration
            reconciliation_strategy: Reconciliation strategy (optional)
        """
        if reconciliation_strategy is None:
            reconciliation_strategy = FullStateReconciliation()
        super().__init__(name, every, config, reconciliation_strategy)
        self.config = config
        self._file_relations = []

    def entity_definitions(self) -> List[EntityDefinition]:
        """Return entity definitions this provider can create.

        File provider doesn't define its own entity types - it reads entities
        of any type from files.
        """
        return []

    def _get_managed_entity_kinds(self) -> List[str]:
        """Get list of entity kinds managed by this File provider.

        Since file provider can read any entity type, we return an empty list
        and rely on the source tracking labels to identify entities created
        by this provider.

        Returns:
            Empty list (all entity types are supported)
        """
        return []

    def _discover_current_entities(self) -> List[Entity]:
        """Discover all current entities from .devgraph.yaml files."""
        entities = []
        self._file_relations = []

        # Resolve base path
        base_path = Path(self.config.base_path).resolve()
        logger.info(f"Searching for entity files in {base_path}")

        # Find all matching files
        all_files = []
        for path_pattern in self.config.paths:
            # Resolve path relative to base_path
            if os.path.isabs(path_pattern):
                pattern = path_pattern
            else:
                pattern = str(base_path / path_pattern)

            # Use glob to find matching files
            matching_files = glob(pattern, recursive=True)
            all_files.extend(matching_files)

        # Remove duplicates
        all_files = list(set(all_files))
        logger.info(f"Found {len(all_files)} entity files to process")

        # Process each file
        for file_path in all_files:
            try:
                logger.debug(f"Processing file: {file_path}")

                # Read file content
                with open(file_path, "r") as f:
                    content = f.read()

                # Parse entities and relations
                file_entities, file_relations = parse_entity_file(
                    content=content,
                    source_name=f"file://{file_path}",
                    file_path=file_path,
                    namespace=self.config.namespace,
                    additional_labels={
                        "devgraph.ai/provider": "file",
                        "devgraph.ai/file-path": file_path,
                    },
                )

                entities.extend(file_entities)
                self._file_relations.extend(file_relations)

                if file_entities or file_relations:
                    logger.info(
                        f"Loaded {len(file_entities)} entities and {len(file_relations)} relations from {file_path}"
                    )

            except FileNotFoundError:
                logger.warning(f"File not found: {file_path}")
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")

        logger.info(
            f"Discovered {len(entities)} total entities and {len(self._file_relations)} relations from files"
        )
        return entities

    def _create_relations_for_entities(
        self, entities: List[Entity]
    ) -> List[EntityRelation]:
        """Create relations for file entities.

        Args:
            entities: Entities to create relations for

        Returns:
            List of relation objects parsed from the files
        """
        # Return relations that were parsed from the files during discovery
        logger.info(f"Returning {len(self._file_relations)} relations from files")
        return self._file_relations
