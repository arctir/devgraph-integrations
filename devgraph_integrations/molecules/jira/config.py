"""Configuration models for Jira provider.

This module defines the configuration classes used to configure the Jira
provider, including authentication and selector patterns.
"""
from pydantic import BaseModel, Field

from devgraph_integrations.config.base import SensitiveBaseModel
from devgraph_integrations.molecules.base.config import MoleculeProviderConfig


class JiraSelectorConfig(BaseModel):
    """Configuration for selecting Jira projects.

    Defines criteria for selecting projects and issues within a Jira instance.

    Attributes:
        project_keys: List of project keys to include (e.g., ["PROJ", "DEV"])
        jql_filter: Optional JQL query to filter issues
        include_archived: Whether to include archived projects
    """

    project_keys: list[str] = Field(default_factory=list)
    jql_filter: str | None = None
    include_archived: bool = False


class JiraProviderConfig(MoleculeProviderConfig, SensitiveBaseModel):
    """Main configuration for Jira provider.

    Contains all settings needed to connect to Jira API and configure
    project/issue discovery behavior.

    Attributes:
        base_url: Base URL for Jira instance (e.g., https://company.atlassian.net)
        email: Email address for authentication (Cloud)
        api_token: API token for authentication (Cloud)
        username: Username for authentication (Server/Data Center)
        password: Password for authentication (Server/Data Center)
        cloud: Whether this is a Jira Cloud instance (vs Server/Data Center)
        selectors: List of project selection criteria

    Note:
        namespace field is inherited from MoleculeProviderConfig base class
    """

    base_url: str

    # Jira Cloud authentication (email + API token)
    email: str | None = None
    api_token: str | None = None

    # Jira Server/Data Center authentication (username + password)
    username: str | None = None
    password: str | None = None

    # Instance type
    cloud: bool = True

    selectors: list[JiraSelectorConfig] = Field(  # type: ignore[assignment]
        default_factory=list
    )
