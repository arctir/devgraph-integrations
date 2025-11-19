"""FOSSA MCP Server for SBOM and license data retrieval."""

from typing import Dict, Literal, Optional

import requests  # type: ignore
from loguru import logger
from pydantic import BaseModel

from devgraph_integrations.mcpserver.plugin import DevgraphMCPPlugin
from devgraph_integrations.mcpserver.pluginmanager import DevgraphMCPPluginManager
from devgraph_integrations.mcpserver.server import DevgraphFastMCP


class FOSSAConfig(BaseModel):
    """Configuration for FOSSA MCP integration.

    Attributes:
        api_token: FOSSA API token for authentication
        base_url: Base URL for FOSSA API (default: https://app.fossa.com/api)
    """

    api_token: str
    base_url: str = "https://app.fossa.com/api"


class FOSSAMCPServer(DevgraphMCPPlugin):
    """MCP server providing FOSSA SBOM and license data capabilities.

    This server provides tools to interact with FOSSA's API to retrieve:
    - Software Bill of Materials (SBOM) in various formats
    - License information and compliance data
    - Project dependencies
    - Project metadata
    """

    config_type = FOSSAConfig

    def __init__(self, app: DevgraphFastMCP, config: FOSSAConfig):
        super().__init__(app, config)
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {config.api_token}",
                "Content-Type": "application/json",
            }
        )

        # Register tools with the MCP app
        self.app.add_tool(self.list_projects)
        # self.app.add_tool(self.get_project_sbom)  # Disabled - requires FOSSA enterprise license
        self.app.add_tool(self.get_project_licenses)
        self.app.add_tool(self.get_project_dependencies)
        self.app.add_tool(self.get_project_issues)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        stream: bool = False,
    ) -> Dict:
        """Make a request to the FOSSA API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            stream: Whether to stream the response

        Returns:
            Response data as dict or raw response if streaming

        Raises:
            Exception: If the request fails
        """
        url = f"{self.config.base_url}/{endpoint}"

        try:
            response = self.session.request(
                method=method, url=url, params=params, stream=stream
            )
            response.raise_for_status()

            if stream:
                return {"status": "success", "content": response.text}

            # Try to parse JSON, fall back to text if it fails
            try:
                return response.json()
            except ValueError:
                return {"status": "success", "content": response.text}

        except requests.exceptions.HTTPError as e:
            logger.error(f"FOSSA API HTTP error: {e}")
            return {
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "status_code": e.response.status_code,
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"FOSSA API request error: {e}")
            return {"error": str(e)}

    @DevgraphMCPPluginManager.mcp_tool
    def list_projects(
        self,
        filter_title: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict:
        """List all FOSSA projects.

        Args:
            auth_context: Authentication context
            filter_title: Optional filter to search projects by title
            limit: Maximum number of results (default 100)
            offset: Pagination offset (default 0)

        Returns:
            Dictionary containing list of projects and pagination info
        """
        logger.info(f"Listing FOSSA projects (title filter: {filter_title})")

        params = {
            "count": limit,
            "offset": offset,
        }

        if filter_title:
            params["title"] = filter_title

        result = self._make_request("GET", "v2/projects", params=params)

        if "error" in result:
            return result

        # Extract relevant project info
        projects = []
        for project in result.get("projects", []):
            # Extract locator from latestRevision if available
            locator = None
            if "latestRevision" in project and project["latestRevision"]:
                locator = project["latestRevision"].get("locator")

            projects.append(
                {
                    "id": project.get("id"),
                    "title": project.get("title"),
                    "locator": locator,
                    "branch": project.get("branch"),
                    "url": project.get("url"),
                }
            )

        return {
            "projects": projects,
            "total": len(projects),
            "offset": offset,
            "limit": limit,
        }

    @DevgraphMCPPluginManager.mcp_tool
    def get_project_sbom(
        self,
        project_id: str,
        locator: str | None = None,
        format: Literal[
            "cyclonedx-json", "cyclonedx-xml", "spdx-json", "spdx-tag-value"
        ] = "cyclonedx-json",
        include_deep_dependencies: bool = True,
    ) -> Dict:
        """Download SBOM (Software Bill of Materials) for a project.

        Args:
            project_id: FOSSA project ID (from list_projects)
            locator: Optional FOSSA revision locator (from list_projects). If not provided,
                    fetches the latest revision for the project.
            format: SBOM format (cyclonedx-json, cyclonedx-xml, spdx-json, spdx-tag-value)
            include_deep_dependencies: Include transitive dependencies (default True)

        Returns:
            Dictionary containing the SBOM data
        """
        # If locator not provided, fetch the project to get the latest revision
        if not locator:
            params = {"title": project_id.split("/")[-1]}
            projects_result = self._make_request("GET", "v2/projects", params=params)

            if "error" in projects_result:
                return projects_result

            # Find the matching project and get its locator
            for proj in projects_result.get("projects", []):
                if proj.get("id") == project_id:
                    if "latestRevision" in proj and proj["latestRevision"]:
                        locator = proj["latestRevision"].get("locator")
                        break

            if not locator:
                return {
                    "error": f"Could not find revision locator for project {project_id}"
                }

        logger.info(
            f"Getting SBOM for project {project_id} (locator: {locator}) in format {format}"
        )

        # URL-encode the locator since it contains special characters (+, $)
        from urllib.parse import quote

        encoded_locator = quote(locator, safe="")

        params = {
            "download": "true",
            "format": format.upper().replace("-", "_"),
            "includeDeepDependencies": str(include_deep_dependencies).lower(),
        }

        endpoint = f"revisions/{encoded_locator}/sbom/download"
        result = self._make_request("GET", endpoint, params=params, stream=True)

        if "error" in result:
            # SBOM download may not be available for all projects or API tiers
            error_msg = result.get("error", "Unknown error")
            if "404" in error_msg:
                return {
                    "error": "SBOM not available for this project. This feature may require a FOSSA enterprise license or the project may not have SBOM data generated.",
                    "project_id": project_id,
                    "locator": locator,
                }
            return result

        return {
            "project_id": project_id,
            "locator": locator,
            "format": format,
            "sbom": result.get("content"),
        }

    @DevgraphMCPPluginManager.mcp_tool
    def get_project_licenses(
        self,
        project_id: str,
        locator: str | None = None,
    ) -> Dict:
        """Get license information for a project.

        Args:
            project_id: FOSSA project ID (from list_projects)
            locator: Optional FOSSA revision locator (from list_projects). If not provided,
                    fetches the latest revision for the project.

        Returns:
            Dictionary containing license summary and details
        """
        # If locator not provided, fetch the project to get the latest revision
        if not locator:
            params = {"title": project_id.split("/")[-1]}
            projects_result = self._make_request("GET", "v2/projects", params=params)

            if "error" in projects_result:
                return projects_result

            # Find the matching project and get its locator
            for proj in projects_result.get("projects", []):
                if proj.get("id") == project_id:
                    if "latestRevision" in proj and proj["latestRevision"]:
                        locator = proj["latestRevision"].get("locator")
                        break

            if not locator:
                return {
                    "error": f"Could not find revision locator for project {project_id}"
                }

        logger.info(f"Getting licenses for project {project_id} (locator: {locator})")

        # URL-encode the locator since it contains special characters (+, $)
        from urllib.parse import quote

        encoded_locator = quote(locator, safe="")

        # Get attribution report which includes license data
        params = {
            "download": "true",
            "format": "JSON",
        }

        endpoint = f"revisions/{encoded_locator}/attribution/download"
        result = self._make_request("GET", endpoint, params=params, stream=True)

        if "error" in result:
            return result

        return {
            "project_id": project_id,
            "locator": locator,
            "attribution_data": result.get("content"),
        }

    @DevgraphMCPPluginManager.mcp_tool
    def get_project_dependencies(
        self,
        project_id: str,
        locator: str | None = None,
    ) -> Dict:
        """Get dependencies for a project.

        Args:
            project_id: FOSSA project ID (from list_projects)
            locator: Optional FOSSA revision locator (from list_projects). If not provided,
                    fetches the latest revision for the project.

        Returns:
            Dictionary containing list of dependencies
        """
        # If locator not provided, fetch the project to get the latest revision
        if not locator:
            params = {"title": project_id.split("/")[-1]}
            projects_result = self._make_request("GET", "v2/projects", params=params)

            if "error" in projects_result:
                return projects_result

            # Find the matching project and get its locator
            for proj in projects_result.get("projects", []):
                if proj.get("id") == project_id:
                    if "latestRevision" in proj and proj["latestRevision"]:
                        locator = proj["latestRevision"].get("locator")
                        break

            if not locator:
                return {
                    "error": f"Could not find revision locator for project {project_id}"
                }

        logger.info(
            f"Getting dependencies for project {project_id} (locator: {locator})"
        )

        # URL-encode the locator since it contains special characters (+, $)
        from urllib.parse import quote

        encoded_locator = quote(locator, safe="")
        endpoint = f"revisions/{encoded_locator}/dependencies"
        result = self._make_request("GET", endpoint)

        if "error" in result:
            return result

        # Extract and format dependency info
        # The API returns a list directly, not a dict
        dependencies = []
        dep_list = (
            result if isinstance(result, list) else result.get("dependencies", [])
        )
        for dep in dep_list:
            # Extract name from project.title if available
            name = None
            if "project" in dep and dep["project"]:
                name = dep["project"].get("title")
            if not name:
                name = dep.get("title", "unknown")

            # Check if direct dependency (depth == 0 means direct)
            is_direct = False
            if "DependencyLock" in dep:
                is_direct = dep["DependencyLock"].get("depth", 1) == 0

            dependencies.append(
                {
                    "name": name,
                    "locator": dep.get("locator"),
                    "direct": is_direct,
                }
            )

        result = {
            "project_id": project_id,
            "locator": locator,
            "dependencies": dependencies,
            "total": len(dependencies),
        }

        # Debug logging
        logger.info(f"Returning {len(dependencies)} dependencies for {project_id}")
        logger.debug(f"Full response: {result}")

        return result

    @DevgraphMCPPluginManager.mcp_tool
    def get_project_issues(
        self,
        project_id: str,
        issue_type: Optional[Literal["vulnerability", "license", "quality"]] = None,
    ) -> Dict:
        """Get security and compliance issues for a project.

        Args:
            auth_context: Authentication context
            project_id: FOSSA project ID
            issue_type: Filter by issue type (vulnerability, license, quality)

        Returns:
            Dictionary containing list of issues
        """
        logger.info(f"Getting issues for project {project_id} (type: {issue_type})")

        params = {}
        if issue_type:
            params["type"] = issue_type

        endpoint = f"projects/{project_id}/issues"
        result = self._make_request("GET", endpoint, params=params)

        if "error" in result:
            return result

        return {
            "project_id": project_id,
            "issues": result.get("issues", []),
            "total": len(result.get("issues", [])),
        }
