# FOSSA MCP Molecule

The FOSSA molecule provides Model Context Protocol (MCP) integration for retrieving Software Bill of Materials (SBOM) and license compliance data from FOSSA.

## Overview

This MCP-only molecule allows AI assistants like Claude to query FOSSA for:
- Software Bill of Materials (SBOM) in multiple formats
- License compliance information
- Project dependencies and vulnerability data
- Issue tracking for security and compliance

## Features

- **SBOM Generation**: Download SBOMs in CycloneDX or SPDX formats
- **License Data**: Retrieve comprehensive license and attribution reports
- **Dependency Analysis**: Get detailed dependency trees with license information
- **Issue Tracking**: Query security vulnerabilities and compliance issues
- **Project Management**: List and filter FOSSA projects

## Configuration

Configure the FOSSA MCP server in your MCP configuration:

```yaml
mcp:
  fossa:
    api_token: ${FOSSA_API_TOKEN}
    base_url: https://app.fossa.com/api  # Optional, defaults to FOSSA cloud
```

### Getting a FOSSA API Token

1. Log in to your FOSSA account
2. Navigate to Settings → API Tokens
3. Create a new API token with appropriate permissions
4. Store the token securely (e.g., in environment variables)

## Available MCP Tools

### list_projects

List all FOSSA projects with optional filtering.

```python
list_projects(
    filter_title: Optional[str] = None,  # Filter by project title
    limit: int = 100,                    # Max results
    offset: int = 0                      # Pagination offset
)
```

**Example via Claude:**
```
List all FOSSA projects with "backend" in the title
```

### get_project_sbom

Download a Software Bill of Materials for a project revision.

```python
get_project_sbom(
    revision_id: str,                    # e.g., "custom+1/my-project/main"
    format: str = "cyclonedx-json",      # cyclonedx-json, cyclonedx-xml, spdx-json, spdx-tag-value
    include_deep_dependencies: bool = True
)
```

**Supported Formats:**
- `cyclonedx-json` - CycloneDX JSON format
- `cyclonedx-xml` - CycloneDX XML format
- `spdx-json` - SPDX JSON format
- `spdx-tag-value` - SPDX Tag-Value format

**Example via Claude:**
```
Get the SBOM for project "my-app" main branch in CycloneDX JSON format
```

### get_project_licenses

Retrieve license information and attribution data for a project.

```python
get_project_licenses(
    revision_id: str  # e.g., "custom+1/my-project/main"
)
```

**Example via Claude:**
```
What licenses are used in the my-app project?
```

### get_project_dependencies

Get detailed dependency information for a project revision.

```python
get_project_dependencies(
    revision_id: str  # e.g., "custom+1/my-project/main"
)
```

Returns dependency details including:
- Dependency name and version
- Resolved license
- Direct vs. transitive dependencies

**Example via Claude:**
```
Show me all dependencies for my-app including their licenses
```

### get_project_issues

Query security vulnerabilities and compliance issues.

```python
get_project_issues(
    project_id: str,
    issue_type: Optional[str] = None  # "vulnerability", "license", or "quality"
)
```

**Example via Claude:**
```
What security vulnerabilities does my-app have?
```

## Usage Examples

### Via Claude Desktop

After configuring the FOSSA MCP server, you can ask Claude:

**Get SBOM:**
```
Download the SBOM for my-backend-service in SPDX JSON format
```

**Check Licenses:**
```
What licenses are we using in the frontend-app project?
Are there any GPL licenses in our codebase?
```

**Analyze Dependencies:**
```
Show me all npm dependencies in the api-service project
Which dependencies have known vulnerabilities?
```

**Compliance Checking:**
```
Are there any license compliance issues in project X?
List all high-severity security issues across our projects
```

### Revision ID Format

FOSSA revision IDs follow this format:
```
custom+{organization_id}/{project_name}/{branch}
```

Example: `custom+1/my-project/main`

You can find revision IDs by:
1. Listing projects with `list_projects()`
2. Checking project URLs in FOSSA UI
3. Using FOSSA CLI to get project locators

## Integration with Devgraph

The FOSSA molecule integrates seamlessly with Devgraph's MCP ecosystem:

1. **Claude Desktop**: Query FOSSA data directly from Claude
2. **VS Code**: Use with Devgraph VS Code extension
3. **CI/CD**: Automate SBOM generation and compliance checks
4. **Cross-reference**: Combine with GitHub/GitLab molecules to link repos to FOSSA projects

## API Reference

This module uses the FOSSA REST API v2. For detailed API documentation, see:
- [FOSSA API Reference](https://docs.fossa.com/docs/api-reference)
- [FOSSA SBOM Documentation](https://docs.fossa.com/docs/generating-sboms)

## Limitations

- **MCP Only**: This molecule does not include discovery/provider capabilities
- **Authentication**: Requires a valid FOSSA API token
- **Rate Limiting**: Subject to FOSSA API rate limits
- **Cloud vs. On-Premise**: Adjust `base_url` for FOSSA on-premise installations

## Troubleshooting

### Authentication Errors

If you see 401 errors:
- Verify your API token is valid
- Check token permissions in FOSSA settings
- Ensure token is correctly set in environment variable

### Revision Not Found

If you see 404 errors:
- Verify the revision ID format is correct
- Check that the project exists in FOSSA
- Ensure the branch has been analyzed by FOSSA

### SBOM Download Fails

If SBOM downloads fail:
- Verify the project has been analyzed
- Check that the requested format is supported
- Try a different SBOM format

## Development

To extend this module:

1. Add new tools by creating methods with the `@DevgraphMCPPluginManager.mcp_tool` decorator
2. Follow the existing pattern for API calls using `_make_request()`
3. Update this README with new tool documentation

## License

This module is part of Devgraph and follows the same license terms.
