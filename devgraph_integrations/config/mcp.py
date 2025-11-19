"""MCP Server configuration models."""

from pydantic import BaseModel, Field


class MoleculeConfig(BaseModel):
    """Configuration for an MCP molecule."""

    name: str = Field(description="Name of the molecule")
    type: str = Field(description="Molecule type (e.g., 'github', 'gitlab')")
    config: dict = Field(
        default_factory=dict, description="Configuration settings for the molecule"
    )
    enabled: bool = Field(
        default=True, description="Whether the molecule is enabled or not"
    )


class MCPServerConfig(BaseModel):
    """Configuration for the MCP server."""

    name: str = Field(default="DevgraphMCPServer", description="Name of the MCP server")
    host: str = Field(
        default="127.0.0.1", description="Host address to bind the MCP server"
    )
    port: int = Field(default=9000, description="Port number for the MCP server")
    molecules: list[MoleculeConfig] = Field(
        default_factory=list, description="Molecule configurations for MCP tools"
    )
