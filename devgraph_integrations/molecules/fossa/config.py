"""Configuration models for FOSSA provider.

This module defines the configuration classes used to configure the FOSSA
provider for discovering FOSSA projects and linking them to repositories.
"""

from devgraph_integrations.config.base import SensitiveBaseModel
from devgraph_integrations.molecules.base.config import MoleculeProviderConfig


class FOSSAProviderConfig(MoleculeProviderConfig, SensitiveBaseModel):
    """Main configuration for FOSSA provider.

    Contains all settings needed to connect to FOSSA API and configure
    project discovery behavior.

    Attributes:
        token: FOSSA API token for authentication
        base_url: Base URL for FOSSA API (default: https://app.fossa.com/api)
        filter_title: Optional filter to search projects by title

    Note:
        namespace field is inherited from MoleculeProviderConfig base class
    """

    token: str
    base_url: str = "https://app.fossa.com/api"
    filter_title: str | None = None
