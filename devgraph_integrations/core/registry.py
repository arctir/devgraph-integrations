"""Entity definition registry for Devgraph discovery system.

This module provides functionality to register, manage, and create entity definitions
independently of provider instances. This allows for schema setup, validation,
and documentation without running specific providers.
"""
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from devgraph_client.api.entities import create_entity_definition
from devgraph_client.client import AuthenticatedClient
from devgraph_integrations.core.base import EntityDefinition


class EntityDefinitionRegistry:
    """Registry for managing entity definitions across the Devgraph system."""

    def __init__(self):
        """Initialize the entity definition registry."""
        self._definitions: Dict[str, EntityDefinition] = {}
        self._loaded_modules: List[str] = []

    def register(self, definition: EntityDefinition) -> None:
        """Register an entity definition.

        Args:
            definition: EntityDefinition instance to register

        Raises:
            ValueError: If definition with same key already exists
        """
        key = self._get_definition_key(definition)
        if key in self._definitions:
            logger.warning(f"Entity definition already registered: {key}")
            return

        self._definitions[key] = definition
        logger.debug(f"Registered entity definition: {key}")

    def get(self, group: str, kind: str, version: str) -> Optional[EntityDefinition]:
        """Get an entity definition by group, kind, and version.

        Args:
            group: API group (e.g., 'entities.devgraph.ai')
            kind: Entity kind (e.g., 'Workstream')
            version: API version (e.g., 'v1')

        Returns:
            EntityDefinition instance or None if not found
        """
        key = f"{group}/{version}/{kind}"
        return self._definitions.get(key)

    def list_definitions(self) -> List[EntityDefinition]:
        """Get all registered entity definitions.

        Returns:
            List of all registered EntityDefinition instances
        """
        return list(self._definitions.values())

    def list_by_group(self, group: str) -> List[EntityDefinition]:
        """Get entity definitions for a specific API group.

        Args:
            group: API group to filter by

        Returns:
            List of EntityDefinition instances for the group
        """
        return [defn for defn in self._definitions.values() if defn.group == group]

    def auto_discover_definitions(
        self, search_paths: Optional[List[str]] = None
    ) -> int:
        """Auto-discover entity definitions from Python modules.

        Searches for EntityDefinition subclasses in the specified paths.

        Args:
            search_paths: List of module paths to search. Defaults to devgraph types.

        Returns:
            Number of definitions discovered and registered
        """
        if search_paths is None:
            search_paths = [
                "devgraph.types.meta",
                "devgraph.molecules.github.types",
                "devgraph.molecules.vercel.types",
                "devgraph.molecules.ldap.types",
                "devgraph.molecules.argo.types",
            ]

        discovered_count = 0
        for module_path in search_paths:
            discovered_count += self._discover_in_module(module_path)

        logger.info(f"Auto-discovered {discovered_count} entity definitions")
        return discovered_count

    def _discover_in_module(self, module_path: str) -> int:
        """Discover entity definitions in a specific module.

        Args:
            module_path: Python module path to search

        Returns:
            Number of definitions found in the module
        """
        if module_path in self._loaded_modules:
            logger.debug(f"Module already loaded: {module_path}")
            return 0

        try:
            # Import the module and all its submodules
            count = self._import_module_recursively(module_path)
            self._loaded_modules.append(module_path)
            return count
        except ImportError as e:
            logger.debug(f"Could not import module {module_path}: {e}")
            return 0

    def _import_module_recursively(self, module_path: str) -> int:
        """Recursively import module and find EntityDefinition classes.

        Args:
            module_path: Module path to import

        Returns:
            Number of definitions found
        """
        count = 0

        try:
            module = importlib.import_module(module_path)

            # Look for EntityDefinition subclasses in this module
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, EntityDefinition)
                    and obj != EntityDefinition
                ):
                    try:
                        # Create instance of the definition class
                        definition_instance = obj()
                        self.register(definition_instance)
                        count += 1
                        logger.debug(f"Found definition: {name} in {module_path}")
                    except Exception as e:
                        logger.warning(f"Could not instantiate {name}: {e}")

            # Try to find submodules
            if hasattr(module, "__path__"):
                module_dir = Path(module.__path__[0])
                for py_file in module_dir.glob("*.py"):
                    if py_file.name.startswith("v") and py_file.name != "__init__.py":
                        submodule_path = f"{module_path}.{py_file.stem}"
                        count += self._import_module_recursively(submodule_path)

        except Exception as e:
            logger.debug(f"Error importing {module_path}: {e}")

        return count

    def create_all_definitions(self, client: AuthenticatedClient) -> None:
        """Create all registered entity definitions in the Devgraph API.

        Args:
            client: Authenticated API client
        """
        logger.info(f"Creating {len(self._definitions)} entity definitions")

        for definition in self._definitions.values():
            try:
                # Convert to API spec
                spec = definition.to_entity_definition_spec()

                # Create via API
                response = create_entity_definition.sync_detailed(
                    client=client,
                    body=spec,
                )

                if response.status_code == 201:
                    logger.debug(
                        f"Created entity definition: {self._get_definition_key(definition)}"
                    )
                elif response.status_code == 409:
                    logger.debug(
                        f"Entity definition already exists: {self._get_definition_key(definition)}"
                    )
                else:
                    logger.error(
                        f"Failed to create entity definition: {response.status_code}"
                    )

            except Exception as e:
                logger.error(
                    f"Error creating definition {self._get_definition_key(definition)}: {e}"
                )

    def _get_definition_key(self, definition: EntityDefinition) -> str:
        """Get a unique key for an entity definition.

        Args:
            definition: EntityDefinition instance

        Returns:
            Unique string key
        """
        return f"{definition.group}/{definition.name}/{definition.kind}"


# Global registry instance
registry = EntityDefinitionRegistry()


def register_definition(definition: EntityDefinition) -> None:
    """Register an entity definition in the global registry.

    Args:
        definition: EntityDefinition to register
    """
    registry.register(definition)


def get_definition(group: str, kind: str, version: str) -> Optional[EntityDefinition]:
    """Get an entity definition from the global registry.

    Args:
        group: API group
        kind: Entity kind
        version: API version

    Returns:
        EntityDefinition or None if not found
    """
    return registry.get(group, kind, version)


def auto_discover_all_definitions() -> int:
    """Auto-discover all entity definitions in the system.

    Returns:
        Number of definitions discovered
    """
    return registry.auto_discover_definitions()


def create_all_definitions(client: AuthenticatedClient) -> None:
    """Create all registered entity definitions via API.

    Args:
        client: Authenticated API client
    """
    registry.create_all_definitions(client)


def list_all_definitions() -> List[EntityDefinition]:
    """List all registered entity definitions.

    Returns:
        List of all EntityDefinition instances
    """
    return registry.list_definitions()
