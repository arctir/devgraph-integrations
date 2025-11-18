"""Docker registry API client.

This module provides a client for interacting with various Docker registry APIs
including Docker Hub, AWS ECR, Google GCR, Azure ACR, and private registries.
"""

import base64
from typing import Any, Dict, List, Optional

import requests  # type: ignore
from loguru import logger

from ..base.client import HttpApiClient


class DockerRegistryClient(HttpApiClient):
    """Client for Docker registry API operations.

    Supports multiple registry types with appropriate authentication methods.
    """

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        registry_type: str = "docker-hub",
        timeout: int = 30,
    ) -> None:
        """Initialize Docker registry client.

        Args:
            base_url: Base URL of the Docker registry
            token: Registry authentication token
            username: Username for basic authentication
            password: Password for basic authentication
            registry_type: Type of registry (docker-hub, ecr, gcr, acr, private)
            timeout: Request timeout in seconds
        """
        # Store credentials
        self.token = token
        self.username = username
        self.password = password
        self.registry_type = registry_type

        # Initialize headers dict for additional headers
        self.headers = {}
        self.additional_headers = {}

        # Set up authentication before calling parent __init__
        # so that additional_headers are populated
        self._setup_authentication()

        # For GHCR, we need to override the parent's Bearer token auth
        # Initialize parent with appropriate token based on registry type
        parent_token = self._get_parent_token()
        super().__init__(
            base_url,
            parent_token,
            additional_headers=self.additional_headers,
            timeout=timeout,
        )

    def _get_parent_token(self) -> str:
        """Get token to pass to parent HttpApiClient.

        For GHCR with basic auth, we return empty token and handle auth manually.
        For other registries that use bearer tokens, we return the token.
        """
        if (
            self.registry_type == "ghcr"
            and self.username
            and (self.password or self.token)
        ):
            # GHCR with basic auth - parent shouldn't add Bearer token
            return ""
        elif self.token:
            # Use token for other registries
            return self.token
        else:
            return ""

    def _setup_authentication(self) -> None:
        """Set up appropriate authentication headers for the registry type."""
        if self.registry_type == "docker-hub":
            # Docker Hub uses token-based authentication
            if self.token:
                self.headers["Authorization"] = f"Bearer {self.token}"
            elif self.username and self.password:
                # Basic auth for Docker Hub
                credentials = base64.b64encode(
                    f"{self.username}:{self.password}".encode()
                ).decode()
                self.headers["Authorization"] = f"Basic {credentials}"
        elif self.registry_type in ["ecr", "gcr", "acr"]:
            # Cloud registries typically use tokens
            if self.token:
                self.headers["Authorization"] = f"Bearer {self.token}"
        elif self.registry_type == "ghcr":
            # GitHub Container Registry uses basic auth with PAT
            if self.username and self.password:
                credentials = base64.b64encode(
                    f"{self.username}:{self.password}".encode()
                ).decode()
                # Override the parent's Authorization header
                self.additional_headers["Authorization"] = f"Basic {credentials}"
                logger.info(
                    f"GHCR: Using username + password authentication for user: {self.username}"
                )
            elif self.username and self.token:
                # If token is provided instead of password, use it as password
                credentials = base64.b64encode(
                    f"{self.username}:{self.token}".encode()
                ).decode()
                self.additional_headers["Authorization"] = f"Basic {credentials}"
                logger.info(
                    f"GHCR: Using username + token authentication for user: {self.username}"
                )
            elif self.token:
                # Token-only fallback (less common for GHCR)
                logger.warning(
                    "GHCR: Using token-only authentication (no username provided)"
                )
                pass
            else:
                logger.error(
                    "GHCR: No valid credentials provided (need username + token/password)"
                )
        elif self.registry_type == "private":
            # Private registries may use various auth methods
            if self.token:
                self.headers["Authorization"] = f"Bearer {self.token}"
            elif self.username and self.password:
                credentials = base64.b64encode(
                    f"{self.username}:{self.password}".encode()
                ).decode()
                self.headers["Authorization"] = f"Basic {credentials}"

    def _get_ghcr_token(self, scope: str) -> Optional[str]:
        """Get GHCR bearer token for specific scope."""
        if self.registry_type != "ghcr":
            return None

        # Check if we have credentials for GHCR OAuth
        if not (self.username and self.password) and not self.token:
            return None

        try:
            # GHCR token endpoint
            token_url = f"{self.base_url}/token"

            # Prepare authentication for GHCR token request
            if self.username and self.password:
                # Use username/password for basic auth
                credentials = base64.b64encode(
                    f"{self.username}:{self.password}".encode()
                ).decode()
                headers = {"Authorization": f"Basic {credentials}"}
            elif self.token and self.username:
                # Use username with token as password (typical GHCR setup)
                credentials = base64.b64encode(
                    f"{self.username}:{self.token}".encode()
                ).decode()
                headers = {"Authorization": f"Basic {credentials}"}
            elif self.token:
                # Try token-only auth (some registries support this)
                headers = {"Authorization": f"Bearer {self.token}"}
            else:
                logger.error("No valid credentials for GHCR authentication")
                return None

            params = {"service": "ghcr.io", "scope": scope}

            logger.debug(f"Requesting GHCR token from: {token_url}")
            logger.debug(f"Token request params: {params}")
            logger.debug(
                f"Token request headers: {headers.get('Authorization', 'NO_AUTH')[:30]}..."
            )

            response = requests.get(
                token_url, headers=headers, params=params, timeout=30
            )

            logger.debug(f"Token response status: {response.status_code}")
            logger.debug(f"Token response: {response.text[:200]}...")

            if response.status_code == 200:
                token_data = response.json()
                bearer_token = token_data.get("token")
                if bearer_token:
                    logger.debug(
                        f"Successfully got GHCR bearer token: {bearer_token[:30]}..."
                    )
                    return bearer_token
                else:
                    logger.error("No token in GHCR response")
                    return None
            else:
                logger.error(
                    f"Failed to get GHCR token: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error getting GHCR token: {e}")
            return None

    def list_repositories(self, n: Optional[int] = None) -> List[str]:
        """List all repositories in the registry.

        Args:
            n: Number of repositories to return (optional)

        Returns:
            List of repository names
        """
        try:
            params = {}
            if n:
                params["n"] = n

            if self.registry_type == "docker-hub":
                # Docker Hub API v2
                response = self.get("/v2/_catalog", params=params)
            else:
                # Standard registry v2 API
                response = self.get("/v2/_catalog", params=params)

            if response.status_code == 200:
                data = response.json()
                return data.get("repositories", [])
            else:
                logger.warning(f"Failed to list repositories: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error listing repositories: {e}")
            return []

    def list_tags(self, repository: str, n: Optional[int] = None) -> List[str]:
        """List all tags for a repository.

        Args:
            repository: Repository name
            n: Number of tags to return (optional)

        Returns:
            List of tag names
        """
        try:
            params = {}
            if n:
                params["n"] = n

            endpoint = f"/v2/{repository}/tags/list"

            # Use base client's get() method which handles auth headers
            response = self.get(endpoint, params=params)

            if response.status_code == 200:
                data = response.json()
                return data.get("tags", [])
            else:
                logger.warning(
                    f"Failed to list tags for {repository}: {response.status_code}"
                )
                return []

        except Exception as e:
            logger.error(f"Error listing tags for {repository}: {e}")
            return []

    def get_manifest(self, repository: str, tag: str) -> Optional[Dict[str, Any]]:
        """Get manifest for a specific image tag.

        Args:
            repository: Repository name
            tag: Image tag

        Returns:
            Manifest data as dictionary
        """
        try:
            endpoint = f"/v2/{repository}/manifests/{tag}"
            headers = {
                "Accept": "application/vnd.docker.distribution.manifest.v2+json,application/vnd.docker.distribution.manifest.list.v2+json"
            }

            # For GHCR, use basic auth directly (no token exchange needed)
            if self.registry_type == "ghcr":
                # GHCR uses basic auth with PAT for all requests, no token exchange
                if self.username and (self.password or self.token):
                    password = self.password if self.password else self.token
                    credentials = base64.b64encode(
                        f"{self.username}:{password}".encode()
                    ).decode()
                    headers["Authorization"] = f"Basic {credentials}"
                    logger.debug(
                        f"Using basic auth for GHCR manifest request: {repository}"
                    )
                else:
                    logger.error("No credentials available for GHCR manifest request")
                    return None

            response = self.get(endpoint, headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                error_detail = (
                    response.text[:500] if response.text else "No error details"
                )
                logger.warning(
                    f"Failed to get manifest for {repository}:{tag}: {response.status_code} - {error_detail}"
                )
                return None

        except Exception as e:
            logger.error(f"Error getting manifest for {repository}:{tag}: {e}")
            return None

    def get_blob(self, repository: str, digest: str) -> Optional[Dict[str, Any]]:
        """Get blob data for a specific digest.

        Args:
            repository: Repository name
            digest: Blob digest

        Returns:
            Blob data as dictionary
        """
        try:
            endpoint = f"/v2/{repository}/blobs/{digest}"

            # For GHCR, use basic auth directly
            headers = {}
            if self.registry_type == "ghcr":
                if self.username and (self.password or self.token):
                    password = self.password if self.password else self.token
                    credentials = base64.b64encode(
                        f"{self.username}:{password}".encode()
                    ).decode()
                    headers["Authorization"] = f"Basic {credentials}"
                    logger.debug(
                        f"Using basic auth for GHCR blob request: {repository}"
                    )
                else:
                    logger.error("No credentials available for GHCR blob request")
                    return None

            response = self.get(endpoint, headers=headers if headers else None)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    f"Failed to get blob {digest} for {repository}: {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"Error getting blob {digest} for {repository}: {e}")
            return None

    def get_image_config(self, repository: str, tag: str) -> Optional[Dict[str, Any]]:
        """Get the config blob for an image, which contains labels and metadata.

        Args:
            repository: Repository name
            tag: Image tag

        Returns:
            Config data as dictionary, or None if not available
        """
        try:
            # First get the manifest to find the config digest
            manifest = self.get_manifest(repository, tag)
            if not manifest:
                return None

            # Extract config digest from manifest
            config_digest = manifest.get("config", {}).get("digest")
            if not config_digest:
                logger.debug(
                    f"No config digest found in manifest for {repository}:{tag}"
                )
                return None

            # Fetch the config blob
            config = self.get_blob(repository, config_digest)
            return config

        except Exception as e:
            logger.error(f"Error getting image config for {repository}:{tag}: {e}")
            return None

    def get_source_repository(self, repository: str, tag: str) -> Optional[str]:
        """Extract source repository URL from image labels.

        Args:
            repository: Repository name
            tag: Image tag

        Returns:
            Source repository URL if found in OCI labels, None otherwise
        """
        try:
            config = self.get_image_config(repository, tag)
            if not config:
                return None

            # OCI labels are stored in config.Labels
            labels = config.get("config", {}).get("Labels", {})

            # Check common OCI label for source repository
            source_url = labels.get("org.opencontainers.image.source")
            if source_url:
                logger.debug(
                    f"Found source repository for {repository}:{tag}: {source_url}"
                )
                return source_url

            # Fallback: check other common labels
            for label_key in [
                "org.opencontainers.image.url",
                "org.label-schema.vcs-url",
            ]:
                url = labels.get(label_key)
                if url and "github.com" in url:
                    logger.debug(f"Found source repository via {label_key}: {url}")
                    return url

            logger.debug(f"No source repository found in labels for {repository}:{tag}")
            return None

        except Exception as e:
            logger.error(
                f"Error extracting source repository for {repository}:{tag}: {e}"
            )
            return None

    def get_repository_info(self, repository: str) -> Dict[str, Any]:
        """Get detailed information about a repository.

        Args:
            repository: Repository name

        Returns:
            Repository information dictionary
        """
        info = {
            "name": repository,
            "tags": self.list_tags(repository),
            "registry_type": self.registry_type,
            "registry_url": self.base_url,
        }

        # Get additional metadata if available
        if self.registry_type == "docker-hub":
            # Docker Hub has additional API endpoints for repository metadata
            try:
                # Note: This would require Docker Hub's v1 API which might need different authentication
                pass
            except Exception:
                pass

        return info
