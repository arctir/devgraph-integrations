"""Base HTTP API client for molecule providers.

This module provides a common HTTP API client implementation that can be
used across multiple molecule providers to reduce code duplication.
"""

from typing import Any, Dict, Optional

import requests  # type: ignore
from loguru import logger


class HttpApiClient:
    """Base HTTP API client for molecule providers.

    Provides common HTTP request functionality with authentication and
    error handling that can be shared across multiple providers.

    Attributes:
        base_url: Base URL for API endpoints (normalized without trailing slash)
        token: Authentication token for requests
        additional_headers: Additional headers to include in all requests
        timeout: Default timeout for requests in seconds
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        additional_headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> None:
        """Initialize HTTP API client.

        Args:
            base_url: Base URL for API endpoints
            token: Authentication token for requests
            additional_headers: Optional additional headers for all requests
            timeout: Default timeout for requests in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.additional_headers = additional_headers or {}
        self.timeout = timeout

    def _prepare_headers(
        self, headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Prepare headers for request.

        Args:
            headers: Optional request-specific headers

        Returns:
            Combined headers including authentication and additional headers
        """
        prepared_headers = headers.copy() if headers else {}
        if self.token:
            prepared_headers["Authorization"] = f"Bearer {self.token}"
        prepared_headers.update(self.additional_headers)
        auth_header = prepared_headers.get("Authorization", "")
        logger.debug(f"Prepared auth header: {auth_header[:30]}...")
        return prepared_headers

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint.

        Args:
            endpoint: API endpoint path

        Returns:
            Complete URL for the endpoint
        """
        if endpoint.startswith("/"):
            return f"{self.base_url}{endpoint}"
        else:
            return f"{self.base_url}/{endpoint}"

    def request(self, method_func, endpoint: str, *args, **kwargs) -> requests.Response:
        """Make authenticated HTTP request.

        Args:
            method_func: HTTP method function (e.g., requests.get)
            endpoint: API endpoint path
            *args: Positional arguments for HTTP method
            **kwargs: Keyword arguments for HTTP method

        Returns:
            Response object from the API

        Raises:
            requests.HTTPError: If the API request fails
        """
        # Prepare headers
        headers = kwargs.pop("headers", {})
        kwargs["headers"] = self._prepare_headers(headers)

        # Set default timeout if not provided
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout

        # Make request
        url = self._build_url(endpoint)
        logger.debug(f"Making {method_func.__name__.upper()} request to {url}")

        response = method_func(url, *args, **kwargs)
        response.raise_for_status()

        return response

    def get(self, endpoint: str, *args, **kwargs) -> requests.Response:
        """Make GET request to API endpoint.

        Args:
            endpoint: API endpoint path
            *args: Positional arguments for GET request
            **kwargs: Keyword arguments for GET request

        Returns:
            Response object from the API
        """
        return self.request(requests.get, endpoint, *args, **kwargs)

    def post(self, endpoint: str, *args, **kwargs) -> requests.Response:
        """Make POST request to API endpoint.

        Args:
            endpoint: API endpoint path
            *args: Positional arguments for POST request
            **kwargs: Keyword arguments for POST request

        Returns:
            Response object from the API
        """
        return self.request(requests.post, endpoint, *args, **kwargs)

    def put(self, endpoint: str, *args, **kwargs) -> requests.Response:
        """Make PUT request to API endpoint.

        Args:
            endpoint: API endpoint path
            *args: Positional arguments for PUT request
            **kwargs: Keyword arguments for PUT request

        Returns:
            Response object from the API
        """
        return self.request(requests.put, endpoint, *args, **kwargs)

    def delete(self, endpoint: str, *args, **kwargs) -> requests.Response:
        """Make DELETE request to API endpoint.

        Args:
            endpoint: API endpoint path
            *args: Positional arguments for DELETE request
            **kwargs: Keyword arguments for DELETE request

        Returns:
            Response object from the API
        """
        return self.request(requests.delete, endpoint, *args, **kwargs)

    def get_json(
        self, endpoint: str, default_on_error: Any = None, *args, **kwargs
    ) -> Any:
        """Make GET request and return JSON response.

        Convenience method that handles JSON parsing and provides error fallback.

        Args:
            endpoint: API endpoint path
            default_on_error: Value to return if request fails
            *args: Positional arguments for GET request
            **kwargs: Keyword arguments for GET request

        Returns:
            Parsed JSON response or default_on_error on failure
        """
        try:
            response = self.get(endpoint, *args, **kwargs)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch JSON from {endpoint}: {e}")
            return default_on_error


class RestApiClient(HttpApiClient):
    """REST API client with common JSON handling.

    Extends HttpApiClient with JSON-specific functionality commonly
    needed by REST API providers.
    """

    def __init__(self, base_url: str, token: str, timeout: int = 30) -> None:
        """Initialize REST API client.

        Args:
            base_url: Base URL for API endpoints
            token: Authentication token for requests
            timeout: Default timeout for requests in seconds
        """
        super().__init__(
            base_url=base_url,
            token=token,
            additional_headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
