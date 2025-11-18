# Multi-stage build for devgraph-integrations
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system dependencies (git for pip installs)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install poetry for lock file management
RUN pip install poetry==1.8.3

# Copy package files
COPY . /build/devgraph-integrations

# Install package using pip with MCP extras (more reliable than poetry for Docker)
RUN pip install --no-cache-dir "/build/devgraph-integrations[mcp]"

# Final stage
FROM python:3.12-slim

WORKDIR /app

# No runtime dependencies needed

# Copy Python packages from builder (includes all dependencies and the installed package)
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy pyproject.toml for version/plugin info (needed by release-manifest command)
COPY --from=builder /build/devgraph-integrations/pyproject.toml /usr/local/lib/python3.12/site-packages/pyproject.toml

# Create non-root user
RUN useradd -m -u 1000 integrations && \
    chown -R integrations:integrations /app

USER integrations

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set entrypoint to the CLI command
ENTRYPOINT ["devgraph-integrations"]

# Default command (can be overridden)
CMD ["--help"]
