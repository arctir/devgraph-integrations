from typing import Dict, List, Optional

from github import Github as GithubClient
from github.GithubException import UnknownObjectException
from loguru import logger
from pydantic import BaseModel

from devgraph_integrations.mcpserver.plugin import DevgraphMCPPlugin
from devgraph_integrations.mcpserver.pluginmanager import DevgraphMCPPluginManager


class GithubAppConfig(BaseModel):
    app_id: str
    private_key_path: str
    installation_id: int


class GithubConfig(BaseModel):
    auth_url: str = "https://github.com/login/oauth/authorize"
    token_url: str = "https://github.com/login/oauth/access_token"
    api_url: str = "https://api.github.com"
    token: Optional[str] = None
    app: Optional[GithubAppConfig] = None


class GithubBuildStatus(BaseModel):
    state: str


class GithubMCPServer(DevgraphMCPPlugin):
    config_type = GithubConfig

    def __init__(self, app, config: GithubConfig):
        super().__init__(app, config)
        self.config = config

        self.app.add_tool(self.github_create_issue)

    @DevgraphMCPPluginManager.mcp_tool
    def github_create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Dict:
        """
        Create a new issue in a GitHub repository.

        Args:
            owner: Repository owner (organization or user)
            repo: Repository name
            title: Issue title
            body: Issue body/description (optional)
            labels: List of label names to apply (optional)
            assignees: List of usernames to assign (optional)

        Returns:
            Dictionary containing the created issue information including number, url, and state
        """
        logger.info(f"Creating issue in {owner}/{repo}: {title}")

        github_client = GithubClient(self.config.token)

        try:
            repository = github_client.get_repo(f"{owner}/{repo}")

            # Create the issue
            issue = repository.create_issue(
                title=title,
                body=body or "",
                labels=labels or [],
                assignees=assignees or [],
            )

            logger.info(f"Created issue #{issue.number} in {owner}/{repo}")

            return {
                "number": issue.number,
                "title": issue.title,
                "url": issue.html_url,
                "state": issue.state,
                "created_at": issue.created_at.isoformat(),
                "labels": [label.name for label in issue.labels],
                "assignees": [assignee.login for assignee in issue.assignees],
            }

        except UnknownObjectException:
            error_msg = f"Repository {owner}/{repo} not found or not accessible"
            logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Failed to create issue: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
