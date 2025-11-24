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


class JWTAuthConfig(BaseModel):
    """Configuration for JWT authentication."""

    enabled: bool = Field(default=False, description="Enable JWT authentication")
    secret: str = Field(
        default="", description="JWT secret key (or public key for RS256)"
    )
    algorithm: str = Field(
        default="HS256", description="JWT algorithm (HS256, RS256, etc.)"
    )
    audience: str | None = Field(
        default=None, description="Expected JWT audience claim"
    )
    issuer: str | None = Field(default=None, description="Expected JWT issuer claim")


class MCPServerConfig(BaseModel):
    """Configuration for the MCP server."""

    name: str = Field(default="DevgraphMCPServer", description="Name of the MCP server")
    host: str = Field(
        default="127.0.0.1", description="Host address to bind the MCP server"
    )
    port: int = Field(default=9000, description="Port number for the MCP server")
    base_url: str | None = Field(
        default=None,
        description="External base URL for static assets (e.g., https://example.com). If not set, uses http://{host}:{port}",
    )
    molecules: list[MoleculeConfig] = Field(
        default_factory=list, description="Molecule configurations for MCP tools"
    )
    jwt_auth: JWTAuthConfig = Field(
        default_factory=JWTAuthConfig, description="JWT authentication configuration"
    )
