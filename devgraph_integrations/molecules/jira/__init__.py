"""Jira molecule for Devgraph.

This module provides integration with Atlassian Jira, including:
- Issue management (create, update, search)
- Project and board discovery
- Entity and relationship mapping to ontology
"""

__all__ = []

# MCP server is optional - only import if dependencies are available
try:
    from devgraph_integrations.molecules.jira.mcp import JiraMCP  # noqa: F401

    __all__.append("JiraMCPServer")
except ImportError:
    pass
