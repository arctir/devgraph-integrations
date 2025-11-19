"""Configuration models for File provider.

This module defines the configuration classes used to configure the File
provider, including glob patterns for finding .devgraph.yaml files.
"""

from typing import List

from pydantic import Field

from devgraph_integrations.molecules.base.config import MoleculeProviderConfig


class FileProviderConfig(MoleculeProviderConfig):
    """Main configuration for File provider.

    Contains all settings needed to read .devgraph.yaml files from disk.

    Attributes:
        namespace: Kubernetes-style namespace for created entities
        paths: List of file paths or glob patterns to read (e.g., [".devgraph.yaml", "configs/*.yaml"])
        base_path: Base directory for resolving relative paths (defaults to current directory)
    """

    paths: List[str] = Field(
        default=[".devgraph.yaml"],
        description="List of file paths or glob patterns to read",
    )
    base_path: str = Field(
        default=".",
        description="Base directory for resolving relative paths",
    )
