"""Jira MCP Server implementation.

This module provides MCP tools for interacting with Jira, including
issue creation, searching, updating, and project management.
"""

from typing import Any, Dict, List, Optional

from jira import JIRA
from jira.exceptions import JIRAError
from loguru import logger
from pydantic import BaseModel

from devgraph_integrations.mcpserver.plugin import DevgraphMCPPlugin
from devgraph_integrations.mcpserver.pluginmanager import DevgraphMCPPluginManager


class JiraConfig(BaseModel):
    """Configuration for Jira MCP server."""

    base_url: str
    email: Optional[str] = None
    api_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    cloud: bool = True


class JiraMCPServer(DevgraphMCPPlugin):
    """MCP server providing Jira integration tools."""

    config_type = JiraConfig

    def __init__(self, app, config: JiraConfig):
        """Initialize the Jira MCP server.

        Args:
            app: FastMCP application instance
            config: Jira configuration
        """
        super().__init__(app, config)
        self.config = config

        # Register all tools
        self.app.add_tool(self.jira_create_issue)
        self.app.add_tool(self.jira_get_issue)
        self.app.add_tool(self.jira_update_issue)
        self.app.add_tool(self.jira_search_issues)
        self.app.add_tool(self.jira_add_comment)
        self.app.add_tool(self.jira_get_project)
        self.app.add_tool(self.jira_list_projects)
        self.app.add_tool(self.jira_transition_issue)

    def _get_client(self) -> JIRA:
        """Get authenticated Jira client.

        Returns:
            Authenticated JIRA client instance
        """
        if self.config.cloud and self.config.email and self.config.api_token:
            # Jira Cloud authentication
            return JIRA(
                server=self.config.base_url,
                basic_auth=(self.config.email, self.config.api_token),
            )
        elif self.config.username and self.config.password:
            # Jira Server/Data Center authentication
            return JIRA(
                server=self.config.base_url,
                basic_auth=(self.config.username, self.config.password),
            )
        else:
            raise ValueError("Invalid Jira authentication configuration")

    @DevgraphMCPPluginManager.mcp_tool
    def jira_create_issue(
        self,
        project: str,
        summary: str,
        issue_type: str = "Task",
        description: Optional[str] = None,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        priority: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new issue in Jira.

        Args:
            project: Project key (e.g., "PROJ")
            summary: Issue summary/title
            issue_type: Issue type (Task, Bug, Story, Epic, etc.)
            description: Issue description (optional)
            assignee: Username to assign the issue to (optional)
            labels: List of labels to apply (optional)
            priority: Priority name (e.g., "High", "Medium", "Low")

        Returns:
            Dictionary containing created issue details including key and url
        """
        logger.info(f"Creating {issue_type} in project {project}: {summary}")

        try:
            jira = self._get_client()

            # Build issue fields
            fields = {
                "project": {"key": project},
                "summary": summary,
                "issuetype": {"name": issue_type},
            }

            if description:
                fields["description"] = description
            if assignee:
                fields["assignee"] = {"name": assignee}
            if labels:
                fields["labels"] = labels
            if priority:
                fields["priority"] = {"name": priority}

            # Create the issue
            issue = jira.create_issue(fields=fields)

            logger.info(f"Created issue {issue.key}")

            return {
                "key": issue.key,
                "id": issue.id,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "url": f"{self.config.base_url}/browse/{issue.key}",
                "created": issue.fields.created,
            }

        except JIRAError as e:
            error_msg = f"Failed to create issue: {e.text}"
            logger.error(error_msg)
            return {"error": error_msg, "status_code": e.status_code}
        except Exception as e:
            error_msg = f"Failed to create issue: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    @DevgraphMCPPluginManager.mcp_tool
    def jira_get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get details of a specific Jira issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")

        Returns:
            Dictionary containing issue details
        """
        logger.info(f"Fetching issue {issue_key}")

        try:
            jira = self._get_client()
            issue = jira.issue(issue_key)

            return {
                "key": issue.key,
                "id": issue.id,
                "summary": issue.fields.summary,
                "description": issue.fields.description or "",
                "status": issue.fields.status.name,
                "issue_type": issue.fields.issuetype.name,
                "priority": (
                    issue.fields.priority.name if issue.fields.priority else None
                ),
                "assignee": (
                    issue.fields.assignee.displayName if issue.fields.assignee else None
                ),
                "reporter": (
                    issue.fields.reporter.displayName if issue.fields.reporter else None
                ),
                "created": issue.fields.created,
                "updated": issue.fields.updated,
                "labels": issue.fields.labels,
                "url": f"{self.config.base_url}/browse/{issue.key}",
            }

        except JIRAError as e:
            error_msg = f"Failed to get issue: {e.text}"
            logger.error(error_msg)
            return {"error": error_msg, "status_code": e.status_code}
        except Exception as e:
            error_msg = f"Failed to get issue: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    @DevgraphMCPPluginManager.mcp_tool
    def jira_update_issue(
        self,
        issue_key: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        priority: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing Jira issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            summary: New summary (optional)
            description: New description (optional)
            assignee: New assignee username (optional)
            labels: New labels list (optional)
            priority: New priority name (optional)

        Returns:
            Dictionary containing updated issue details
        """
        logger.info(f"Updating issue {issue_key}")

        try:
            jira = self._get_client()
            issue = jira.issue(issue_key)

            # Build update fields
            fields = {}
            if summary is not None:
                fields["summary"] = summary
            if description is not None:
                fields["description"] = description
            if assignee is not None:
                fields["assignee"] = {"name": assignee}
            if labels is not None:
                fields["labels"] = labels
            if priority is not None:
                fields["priority"] = {"name": priority}

            # Update the issue
            issue.update(fields=fields)

            logger.info(f"Updated issue {issue_key}")

            # Refresh and return updated issue
            issue = jira.issue(issue_key)
            return {
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "url": f"{self.config.base_url}/browse/{issue.key}",
                "updated": issue.fields.updated,
            }

        except JIRAError as e:
            error_msg = f"Failed to update issue: {e.text}"
            logger.error(error_msg)
            return {"error": error_msg, "status_code": e.status_code}
        except Exception as e:
            error_msg = f"Failed to update issue: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    @DevgraphMCPPluginManager.mcp_tool
    def jira_search_issues(
        self,
        jql: str,
        max_results: int = 50,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Search for issues using JQL (Jira Query Language).

        Args:
            jql: JQL query string (e.g., "project = PROJ AND status = Open")
            max_results: Maximum number of results to return (default: 50)
            fields: List of fields to return (optional, returns all by default)

        Returns:
            Dictionary containing search results
        """
        logger.info(f"Searching issues with JQL: {jql}")

        try:
            jira = self._get_client()
            issues = jira.search_issues(
                jql, maxResults=max_results, fields=fields or "*all"
            )

            results = []
            for issue in issues:
                results.append(
                    {
                        "key": issue.key,
                        "summary": issue.fields.summary,
                        "status": issue.fields.status.name,
                        "issue_type": issue.fields.issuetype.name,
                        "assignee": (
                            issue.fields.assignee.displayName
                            if issue.fields.assignee
                            else None
                        ),
                        "url": f"{self.config.base_url}/browse/{issue.key}",
                    }
                )

            logger.info(f"Found {len(results)} issues")

            return {
                "total": len(results),
                "issues": results,
            }

        except JIRAError as e:
            error_msg = f"Failed to search issues: {e.text}"
            logger.error(error_msg)
            return {"error": error_msg, "status_code": e.status_code}
        except Exception as e:
            error_msg = f"Failed to search issues: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    @DevgraphMCPPluginManager.mcp_tool
    def jira_add_comment(self, issue_key: str, comment: str) -> Dict[str, Any]:
        """Add a comment to a Jira issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            comment: Comment text

        Returns:
            Dictionary containing comment details
        """
        logger.info(f"Adding comment to issue {issue_key}")

        try:
            jira = self._get_client()
            comment_obj = jira.add_comment(issue_key, comment)

            logger.info(f"Added comment to {issue_key}")

            return {
                "id": comment_obj.id,
                "body": comment_obj.body,
                "author": comment_obj.author.displayName,
                "created": comment_obj.created,
            }

        except JIRAError as e:
            error_msg = f"Failed to add comment: {e.text}"
            logger.error(error_msg)
            return {"error": error_msg, "status_code": e.status_code}
        except Exception as e:
            error_msg = f"Failed to add comment: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    @DevgraphMCPPluginManager.mcp_tool
    def jira_get_project(self, project_key: str) -> Dict[str, Any]:
        """Get details of a Jira project.

        Args:
            project_key: Project key (e.g., "PROJ")

        Returns:
            Dictionary containing project details
        """
        logger.info(f"Fetching project {project_key}")

        try:
            jira = self._get_client()
            project = jira.project(project_key)

            return {
                "key": project.key,
                "name": project.name,
                "id": project.id,
                "description": getattr(project, "description", ""),
                "lead": project.lead.displayName if hasattr(project, "lead") else None,
                "url": f"{self.config.base_url}/browse/{project.key}",
            }

        except JIRAError as e:
            error_msg = f"Failed to get project: {e.text}"
            logger.error(error_msg)
            return {"error": error_msg, "status_code": e.status_code}
        except Exception as e:
            error_msg = f"Failed to get project: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    @DevgraphMCPPluginManager.mcp_tool
    def jira_list_projects(self) -> Dict[str, Any]:
        """List all accessible Jira projects.

        Returns:
            Dictionary containing list of projects
        """
        logger.info("Listing all projects")

        try:
            jira = self._get_client()
            projects = jira.projects()

            results = []
            for project in projects:
                results.append(
                    {
                        "key": project.key,
                        "name": project.name,
                        "id": project.id,
                        "url": f"{self.config.base_url}/browse/{project.key}",
                    }
                )

            logger.info(f"Found {len(results)} projects")

            return {
                "total": len(results),
                "projects": results,
            }

        except JIRAError as e:
            error_msg = f"Failed to list projects: {e.text}"
            logger.error(error_msg)
            return {"error": error_msg, "status_code": e.status_code}
        except Exception as e:
            error_msg = f"Failed to list projects: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    @DevgraphMCPPluginManager.mcp_tool
    def jira_transition_issue(
        self, issue_key: str, transition: str, comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transition an issue to a new status.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            transition: Transition name (e.g., "Done", "In Progress")
            comment: Optional comment to add during transition

        Returns:
            Dictionary containing updated issue status
        """
        logger.info(f"Transitioning issue {issue_key} to {transition}")

        try:
            jira = self._get_client()
            issue = jira.issue(issue_key)

            # Find the transition ID by name
            transitions = jira.transitions(issue)
            transition_id = None
            for t in transitions:
                if t["name"].lower() == transition.lower():
                    transition_id = t["id"]
                    break

            if not transition_id:
                available = [t["name"] for t in transitions]
                return {
                    "error": f"Transition '{transition}' not found. Available: {available}"
                }

            # Perform the transition
            fields = {}
            if comment:
                fields["comment"] = [{"body": comment}]

            jira.transition_issue(issue, transition_id, fields=fields)

            logger.info(f"Transitioned {issue_key} to {transition}")

            # Refresh and return updated issue
            issue = jira.issue(issue_key)
            return {
                "key": issue.key,
                "status": issue.fields.status.name,
                "url": f"{self.config.base_url}/browse/{issue.key}",
            }

        except JIRAError as e:
            error_msg = f"Failed to transition issue: {e.text}"
            logger.error(error_msg)
            return {"error": error_msg, "status_code": e.status_code}
        except Exception as e:
            error_msg = f"Failed to transition issue: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
