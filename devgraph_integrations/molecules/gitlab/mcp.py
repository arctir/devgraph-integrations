from typing import Optional

from loguru import logger
from pydantic import BaseModel

from devgraph_integrations.mcpserver.plugin import DevgraphMCPPlugin
from devgraph_integrations.mcpserver.pluginmanager import DevgraphMCPPluginManager
from devgraph_integrations.molecules.gitlab.types.v1_gitlab_project import V1GitlabProjectEntity
from devgraph_integrations.types.auth import AuthContext
from gitlab import Gitlab as GitlabClient
from gitlab.exceptions import GitlabGetError


class GitlabConfig(BaseModel):
    api_url: str = "https://gitlab.com/api/v4"
    token: Optional[str] = None


class GitlabPipelineStatus(BaseModel):
    status: str
    ref: str
    sha: str


class GitlabMCPServer(DevgraphMCPPlugin):
    config_type = GitlabConfig

    def __init__(self, config: GitlabConfig):
        self.config = config

    @DevgraphMCPPluginManager.mcp_tool
    def get_pipeline_status(
        self,
        auth_context: AuthContext,
        entity: V1GitlabProjectEntity,
        branch: str = "main",
    ) -> GitlabPipelineStatus:
        """
        Retrieve the GitLab CI/CD pipeline status of a GitLab project.

        Args:
            auth_context (AuthContext): The authentication context containing token and environment.
            entity (V1GitlabProjectEntity): The full entity resource to interrogate.
            branch (str): The branch to check the pipeline status for. Defaults to "main".
        Returns:
            GitlabPipelineStatus: The pipeline status of the project on the specified branch.
        """
        logger.info(
            f"Retrieving pipeline status for entity: {entity.model_dump()}, branch: {branch}"
        )
        gitlab_client = GitlabClient(
            url=self.config.api_url, private_token=self.config.token
        )
        project_path = f"{entity.spec.group}/{entity.spec.name}"

        try:
            project = gitlab_client.projects.get(project_path)
            logger.debug(f"Project found: {project.path_with_namespace}")

            # Get latest pipeline for the branch
            pipelines = project.pipelines.list(ref=branch, per_page=1)
            if not pipelines:
                raise ValueError(
                    f"No pipelines found for branch {branch} in project {project_path}"
                )

            latest_pipeline = pipelines[0]
            logger.debug(f"Latest pipeline status: {latest_pipeline.status}")

            return GitlabPipelineStatus(
                status=latest_pipeline.status,
                ref=latest_pipeline.ref,
                sha=latest_pipeline.sha,
            ).model_dump(mode="json")

        except GitlabGetError as e:
            logger.error(f"GitLab API error: {e}")
            raise ValueError(f"Failed to get pipeline status for {project_path}: {e}")
