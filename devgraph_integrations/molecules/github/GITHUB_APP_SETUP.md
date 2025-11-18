# GitHub App Setup for Higher Rate Limits

The GitHub provider now supports GitHub App authentication, which provides **3x higher rate limits** (15,000 requests/hour vs 5,000 for PATs).

## Rate Limit Comparison

| Authentication Method | Rate Limit | Best For |
|----------------------|------------|----------|
| Personal Access Token (PAT) | 5,000/hour | Small deployments, single org |
| GitHub App | 15,000/hour per installation | Production, multiple orgs |

## Creating a GitHub App

### 1. Create the App

1. Go to your organization settings: `https://github.com/organizations/YOUR_ORG/settings/apps`
2. Click "New GitHub App"
3. Fill in the details:
   - **Name**: `Devgraph Discovery` (or your preferred name)
   - **Homepage URL**: Your devgraph instance URL
   - **Webhook**: Uncheck "Active" (not needed for discovery)

### 2. Set Permissions

Under "Repository permissions":
- **Contents**: Read-only (to read repository files)
- **Metadata**: Read-only (automatically selected, for repo metadata)

### 3. Installation

- **Where can this GitHub App be installed?**: Choose based on your needs
  - "Only on this account" - For single org
  - "Any account" - If you want to use across multiple orgs

### 4. Create the App

Click "Create GitHub App"

### 5. Generate Private Key

1. On the app settings page, scroll to "Private keys"
2. Click "Generate a private key"
3. Save the downloaded `.pem` file securely

### 6. Install the App

1. Go to "Install App" in the left sidebar
2. Click "Install" next to your organization
3. Choose:
   - "All repositories" - Discover all repos
   - "Only select repositories" - Choose specific repos
4. Click "Install"

### 7. Get the Installation ID

After installation, the URL will look like:
```
https://github.com/organizations/YOUR_ORG/settings/installations/12345678
```

The number at the end (`12345678`) is your **installation_id**.

### 8. Get the App ID

1. Go back to the app settings page
2. The **App ID** is shown at the top

## Configuration

### Option 1: GitHub App (Recommended - 15,000 requests/hour)

```yaml
providers:
  - name: github
    provider: github
    every: 3600
    config:
      namespace: default
      app_id: 123456  # Your App ID
      app_private_key: |
        -----BEGIN RSA PRIVATE KEY-----
        YOUR_PRIVATE_KEY_CONTENT_HERE
        -----END RSA PRIVATE KEY-----
      installation_id: 12345678  # Installation ID from URL
      selectors:
        - organization: your-org
          repo_name: ".*"
          graph_files:
            - .devgraph.yaml
```

### Option 2: Personal Access Token (Fallback - 5,000 requests/hour)

```yaml
providers:
  - name: github
    provider: github
    every: 3600
    config:
      namespace: default
      token: ghp_your_token_here
      selectors:
        - organization: your-org
          repo_name: ".*"
          graph_files:
            - .devgraph.yaml
```

## Benefits of GitHub App

✅ **3x higher rate limits** (15,000 vs 5,000/hour)
✅ **Per-installation limits** - Install on multiple orgs for separate rate limit buckets
✅ **Better security** - Fine-grained permissions, short-lived tokens
✅ **Audit trail** - Actions show as "app" in GitHub logs
✅ **Automatic token rotation** - Tokens refresh automatically

## Troubleshooting

### "Bad credentials" error
- Verify the private key is correctly formatted (includes BEGIN/END lines)
- Check the App ID is correct
- Ensure the app is installed on the organization

### "Resource not accessible by integration"
- Check the app has "Contents: Read" permission
- Verify the app is installed on the specific repositories

### Rate limit still showing 5,000/hour
- Confirm you're using `app_id` + `app_private_key`, not `token`
- Check logs for "Using GitHub App installation" message
