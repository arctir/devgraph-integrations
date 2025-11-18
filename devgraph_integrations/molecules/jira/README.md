# Jira Molecule

Integration with Atlassian Jira for issue tracking and project management.

## Features

- **MCP Tools**: Create, update, search, and manage Jira issues and projects
- **Ontology Integration**: Sync Jira issues and projects as entities
- **Relationships**: Link issues to projects, users, and other entities

## Configuration

### Jira Cloud (Recommended)

```yaml
jira:
  namespace: default
  base_url: https://your-company.atlassian.net
  email: your-email@company.com
  api_token: your-api-token
  cloud: true
  selectors:
    - project_keys: ["PROJ", "DEV"]
      include_archived: false
```

### Jira Server/Data Center

```yaml
jira:
  namespace: default
  base_url: https://jira.company.com
  username: your-username
  password: your-password
  cloud: false
  selectors:
    - project_keys: ["PROJ"]
```

## Authentication

### Jira Cloud

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a label (e.g., "Devgraph Integration")
4. Copy the token
5. Use your Atlassian email and the API token in the configuration

### Jira Server/Data Center

Use your regular username and password for authentication.

## MCP Tools

### Issue Management

- `jira_create_issue` - Create a new issue
- `jira_get_issue` - Get issue details
- `jira_update_issue` - Update an issue
- `jira_search_issues` - Search using JQL
- `jira_add_comment` - Add a comment to an issue
- `jira_transition_issue` - Transition issue status

### Project Management

- `jira_get_project` - Get project details
- `jira_list_projects` - List all accessible projects

## Example Usage

### Create an Issue

```python
result = jira_create_issue(
    project="PROJ",
    summary="Implement new feature",
    issue_type="Task",
    description="Detailed description here",
    assignee="john.doe",
    labels=["backend", "api"],
    priority="High"
)
```

### Search Issues

```python
result = jira_search_issues(
    jql="project = PROJ AND status = 'In Progress'",
    max_results=50
)
```

### Transition Issue

```python
result = jira_transition_issue(
    issue_key="PROJ-123",
    transition="Done",
    comment="Completed the task"
)
```

## Entity Types

### JiraIssue

Represents a work item in Jira.

**Key fields:**
- `key` - Issue key (e.g., "PROJ-123")
- `project_key` - Project the issue belongs to
- `summary` - Issue title
- `issue_type` - Task, Bug, Story, Epic, etc.
- `status` - Current status
- `assignee` - Assigned user

### JiraProject

Represents a Jira project containing issues.

**Key fields:**
- `key` - Project key (e.g., "PROJ")
- `name` - Project name
- `description` - Project description
- `lead` - Project lead

## Relationships

- **in_project** - Issue belongs to project
- **assigned_to** - Issue assigned to user
- **blocks** - Issue blocks another issue
- **related_to** - Issue related to other entities

## JQL Examples

```jql
# Find open bugs
project = PROJ AND type = Bug AND status = Open

# Find your assigned tasks
assignee = currentUser() AND status != Done

# Find recently updated issues
project = PROJ AND updated >= -7d

# Find high priority issues
priority = High AND status in ("To Do", "In Progress")
```

## Rate Limits

- **Jira Cloud**: 10,000 requests per hour per user
- **Jira Server**: Depends on server configuration

## Dependencies

```bash
pip install jira
```

## Troubleshooting

### Authentication Failed

- **Cloud**: Verify email and API token are correct
- **Server**: Check username and password
- Ensure the base URL is correct (include https://)

### Permission Denied

- Verify the user has access to the projects
- Check Jira permission scheme for the project
- Ensure API token/credentials have not expired

### Transition Not Found

Use `jira_get_issue` to see available transitions for the current status.
