"""Configuration models for GitLab provider.

This module defines the configuration classes used to configure the GitLab
provider, including selector patterns for groups and projects.
"""

from pydantic import BaseModel

from devgraph_integrations.config.base import SensitiveBaseModel
from devgraph_integrations.molecules.base.config import MoleculeProviderConfig


class GitlabSelectorConfig(BaseModel):
    """Configuration for selecting GitLab projects.

    Defines criteria for selecting projects within a GitLab group,
    including name patterns and graph file locations.

    Attributes:
        group: GitLab group path to scan
        project_name: Regex pattern for project names (defaults to match all)
        graph_files: List of file paths to read for graph definitions (entities and relationships)
    """

    group: str
    project_name: str | None = ".*"
    graph_files: list[str] = [".devgraph.yaml"]


class GitlabProviderConfig(MoleculeProviderConfig, SensitiveBaseModel):
    """Main configuration for GitLab provider.

    Contains all settings needed to connect to GitLab API and configure
    project discovery behavior.

    Attributes:
        base_url: Base URL for GitLab instance (defaults to GitLab.com)
        api_url: GitLab API base URL
        token: GitLab personal access token for authentication
        selectors: List of project selection criteria

    Note:
        namespace field is inherited from MoleculeProviderConfig base class
    """

    base_url: str = "https://gitlab.com"
    api_url: str = "https://gitlab.com/api/v4"
    token: str
    selectors: list[GitlabSelectorConfig] = []
