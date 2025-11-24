"""Molecule metadata management."""

from importlib import import_module
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class MoleculeMetadata(BaseModel):
    """Metadata for a molecule provider."""

    version: str = Field(description="Semantic version of the molecule")
    name: str = Field(description="Machine-readable name (lowercase, hyphen-separated)")
    display_name: str = Field(description="Human-readable display name")
    description: str = Field(description="Brief description of what the molecule does")
    logo: Dict[str, str] = Field(
        default_factory=dict,
        description="Logo sources: reactIcons (icon identifier like 'SiGithub' or 'PiFile'), url, or svg",
    )
    homepage_url: Optional[str] = Field(
        default=None, description="Homepage or product URL"
    )
    docs_url: Optional[str] = Field(default=None, description="Documentation URL")
    capabilities: List[str] = Field(
        default_factory=list,
        description="List of capabilities: discovery, mcp, relations, etc.",
    )
    entity_types: List[str] = Field(
        default_factory=list, description="Entity types this molecule creates"
    )
    relation_types: List[str] = Field(
        default_factory=list, description="Relation types this molecule creates"
    )
    requires_auth: bool = Field(
        default=False, description="Whether authentication is required"
    )
    auth_types: List[str] = Field(
        default_factory=list,
        description="Supported auth types: api_token, oauth, app, pat, etc.",
    )
    min_framework_version: str = Field(
        default="0.1.0", description="Minimum devgraph-integrations version required"
    )
    deprecated: bool = Field(
        default=False, description="Whether molecule is deprecated"
    )
    replacement: Optional[str] = Field(
        default=None, description="Replacement molecule if deprecated"
    )
    config_schema: Optional[Dict] = Field(
        default=None, description="JSON schema for the molecule's configuration"
    )


def get_molecule_metadata(module_path: str) -> Optional[MoleculeMetadata]:
    """
    Get metadata for a molecule by module path.

    Args:
        module_path: Python module path (e.g., 'devgraph_integrations.molecules.fossa')

    Returns:
        MoleculeMetadata if available, None otherwise

    Example:
        >>> metadata = get_molecule_metadata('devgraph_integrations.molecules.fossa')
        >>> print(f"{metadata.display_name} v{metadata.version}")
        FOSSA v1.0.0
    """
    try:
        module = import_module(module_path)
        if hasattr(module, "__molecule_metadata__"):
            return MoleculeMetadata(**module.__molecule_metadata__)
        return None
    except (ImportError, Exception):
        return None


def list_all_molecules() -> Dict[str, MoleculeMetadata]:
    """
    List all available molecules and their metadata.

    Uses stevedore to discover molecules from all installed packages
    that register entry points under 'devgraph.molecules'.

    Returns:
        Dictionary mapping molecule name to metadata

    Example:
        >>> molecules = list_all_molecules()
        >>> for name, meta in molecules.items():
        ...     print(f"{meta.display_name}: {', '.join(meta.capabilities)}")
        FOSSA: discovery, mcp, relations
        GitHub: discovery, mcp
    """
    from stevedore import ExtensionManager

    result = {}

    def on_load_failure(_manager, _entrypoint, _exception):
        pass  # Silently skip failed loads

    # Use stevedore to discover all molecules from entry points
    mgr = ExtensionManager(
        namespace="devgraph.molecules",
        invoke_on_load=False,
        on_load_failure_callback=on_load_failure,
    )

    for ext in mgr:
        plugin_class = ext.plugin

        # Try to get full metadata (includes auto-generated config_schema)
        if hasattr(plugin_class, "get_full_metadata"):
            try:
                meta_dict = plugin_class.get_full_metadata()
                metadata = MoleculeMetadata(**meta_dict)
                result[metadata.name] = metadata
                continue
            except Exception:
                pass

        # Fallback: try get_metadata without auto-generation
        if hasattr(plugin_class, "get_metadata"):
            try:
                meta_dict = plugin_class.get_metadata()
                metadata = MoleculeMetadata(**meta_dict)
                result[metadata.name] = metadata
                continue
            except Exception:
                pass

        # Fallback: try to get from module's __molecule_metadata__
        module_path = plugin_class.__module__.rsplit(".", 1)[0]
        metadata = get_molecule_metadata(module_path)
        if metadata:
            result[metadata.name] = metadata

    return result


def check_version_compatibility(molecule_version: str, required_version: str) -> bool:
    """
    Check if molecule version meets minimum requirement.

    Args:
        molecule_version: Current molecule version (e.g., "1.2.3")
        required_version: Minimum required version (e.g., "1.0.0")

    Returns:
        True if compatible, False otherwise

    Example:
        >>> check_version_compatibility("1.2.3", "1.0.0")
        True
        >>> check_version_compatibility("0.9.0", "1.0.0")
        False
    """
    from packaging import version

    try:
        return version.parse(molecule_version) >= version.parse(required_version)
    except Exception:
        return False
