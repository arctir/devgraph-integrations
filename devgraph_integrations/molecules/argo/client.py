"""Argo CD API client.

This module provides a client for interacting with the Argo CD API to fetch
projects, applications, and other resources.
"""
from typing import List, Dict, Any

from ..base.client import HttpApiClient


class ArgoClient(HttpApiClient):
    """Client for interacting with Argo CD API.

    Extends the base HttpApiClient with Argo CD-specific functionality
    for fetching projects and applications.
    """

    def __init__(self, base_url: str, token: str, timeout: int = 30) -> None:
        """Initialize Argo CD client.

        Args:
            base_url: Base URL for Argo CD API
            token: Authentication token for API access
            timeout: Request timeout in seconds
        """
        super().__init__(base_url=base_url, token=token, timeout=timeout)

    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all Argo CD projects.

        Returns:
            List of project dictionaries, empty list on failure
        """
        data = self.get_json("projects", default_on_error={})
        return data.get("items", [])

    def get_apps(self, project: str) -> List[Dict[str, Any]]:
        """Get all applications in a specific project.

        Args:
            project: Name of the Argo CD project

        Returns:
            List of application dictionaries, empty list on failure
        """
        params = {"project": [project]}
        data = self.get_json("applications", params=params, default_on_error={})
        return data.get("items", [])
