"""Vercel API client.

This module provides a client for interacting with the Vercel API to fetch
teams, projects, deployments, and other resources.
"""

from typing import Any, Dict, List

from ..base.client import RestApiClient


class VercelClient(RestApiClient):
    """Client for interacting with Vercel API.

    Extends the base RestApiClient with Vercel-specific functionality
    for fetching teams, projects, and deployments.
    """

    def __init__(self, base_url: str, token: str, timeout: int = 30) -> None:
        """Initialize Vercel client.

        Args:
            base_url: Base URL for Vercel API
            token: Authentication token for API access
            timeout: Request timeout in seconds
        """
        super().__init__(base_url=base_url, token=token, timeout=timeout)

    # Base HTTP methods are inherited from RestApiClient

    def get_projects(self, team_id: str = None) -> List[Dict[str, Any]]:
        """Get all Vercel projects, optionally filtered by team.

        Args:
            team_id: Optional team ID to filter projects

        Returns:
            List of project dictionaries, empty list on failure
        """
        endpoint = "/v10/projects"
        params = {}
        if team_id:
            params["teamId"] = team_id

        data = self.get_json(endpoint, params=params, default_on_error={})
        return data.get("projects", [])

    def get_deployments(
        self, project_id: str, team_id: str = None
    ) -> List[Dict[str, Any]]:
        """Get deployments for a specific Vercel project.

        Args:
            project_id: ID of the Vercel project
            team_id: Optional team ID for team-owned projects

        Returns:
            List of deployment dictionaries, empty list on failure
        """
        endpoint = "/v3/deployments"
        params = {"projectId": project_id}
        if team_id:
            params["teamId"] = team_id

        data = self.get_json(endpoint, params=params, default_on_error={})
        return data.get("deployments", [])

    def get_teams(self) -> List[Dict[str, Any]]:
        """Get all Vercel teams accessible to the authenticated user.

        Returns:
            List of team dictionaries, empty list on failure
        """
        endpoint = "/v2/teams"
        data = self.get_json(endpoint, default_on_error={})
        return data.get("teams", [])
