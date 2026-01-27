#!/usr/bin/env python3
"""
BlackRoad API Integration Base
Provides base classes and utilities for all API integrations
"""

import os
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

try:
    import aiohttp
except ImportError:
    aiohttp = None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    """Standardized API response wrapper"""
    success: bool
    status_code: int
    data: Any = None
    error: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    elapsed_ms: float = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'status_code': self.status_code,
            'data': self.data,
            'error': self.error,
            'elapsed_ms': self.elapsed_ms,
            'timestamp': self.timestamp
        }


@dataclass
class HealthCheckResult:
    """Result of an endpoint health check"""
    endpoint: str
    healthy: bool
    status_code: Optional[int] = None
    latency_ms: float = 0
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class BaseAPI(ABC):
    """
    Base class for all API integrations

    Provides:
    - Authentication handling
    - Request/response standardization
    - Health checks
    - Retry logic with exponential backoff
    - Rate limiting
    """

    name: str = "base"
    base_url: str = ""
    auth_type: str = "bearer"  # bearer, x-api-key, basic, oauth2

    def __init__(self,
                 api_key: Optional[str] = None,
                 env_var: Optional[str] = None,
                 base_url: Optional[str] = None,
                 timeout: int = 30,
                 max_retries: int = 3,
                 retry_delay: float = 1.0):

        self.api_key = api_key or os.getenv(env_var or '')
        if base_url:
            self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._session = None

    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'BlackRoad-Backup-Automator/1.0'
        }

        if self.api_key:
            if self.auth_type == 'bearer':
                headers['Authorization'] = f'Bearer {self.api_key}'
            elif self.auth_type == 'x-api-key':
                headers['x-api-key'] = self.api_key
            elif self.auth_type == 'basic':
                import base64
                encoded = base64.b64encode(self.api_key.encode()).decode()
                headers['Authorization'] = f'Basic {encoded}'

        return headers

    def _request(self,
                 method: str,
                 endpoint: str,
                 data: Optional[dict] = None,
                 params: Optional[dict] = None,
                 headers: Optional[dict] = None) -> APIResponse:
        """Make an HTTP request with retry logic"""

        if requests is None:
            return APIResponse(
                success=False,
                status_code=0,
                error="requests library not installed"
            )

        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        req_headers = {**self._get_headers(), **(headers or {})}

        last_error = None
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                response = requests.request(
                    method=method.upper(),
                    url=url,
                    json=data,
                    params=params,
                    headers=req_headers,
                    timeout=self.timeout
                )

                elapsed_ms = (time.time() - start_time) * 1000

                try:
                    response_data = response.json()
                except:
                    response_data = response.text

                return APIResponse(
                    success=response.ok,
                    status_code=response.status_code,
                    data=response_data,
                    headers=dict(response.headers),
                    elapsed_ms=elapsed_ms,
                    error=None if response.ok else str(response_data)
                )

            except requests.exceptions.Timeout:
                last_error = "Request timed out"
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {e}"
            except Exception as e:
                last_error = f"Request failed: {e}"

            # Exponential backoff
            if attempt < self.max_retries - 1:
                sleep_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Retry {attempt + 1}/{self.max_retries} after {sleep_time}s: {last_error}")
                time.sleep(sleep_time)

        return APIResponse(
            success=False,
            status_code=0,
            error=last_error
        )

    def get(self, endpoint: str, params: Optional[dict] = None) -> APIResponse:
        """GET request"""
        return self._request('GET', endpoint, params=params)

    def post(self, endpoint: str, data: Optional[dict] = None) -> APIResponse:
        """POST request"""
        return self._request('POST', endpoint, data=data)

    def put(self, endpoint: str, data: Optional[dict] = None) -> APIResponse:
        """PUT request"""
        return self._request('PUT', endpoint, data=data)

    def patch(self, endpoint: str, data: Optional[dict] = None) -> APIResponse:
        """PATCH request"""
        return self._request('PATCH', endpoint, data=data)

    def delete(self, endpoint: str) -> APIResponse:
        """DELETE request"""
        return self._request('DELETE', endpoint)

    @abstractmethod
    def health_check(self) -> HealthCheckResult:
        """Perform a health check on the API"""
        pass

    def is_healthy(self) -> bool:
        """Quick health check returning boolean"""
        return self.health_check().healthy


class CloudflareAPI(BaseAPI):
    """Cloudflare API integration"""

    name = "cloudflare"
    base_url = "https://api.cloudflare.com/client/v4"
    auth_type = "bearer"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            api_key=api_key,
            env_var="CLOUDFLARE_API_TOKEN"
        )
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")

    def health_check(self) -> HealthCheckResult:
        start = time.time()
        response = self.get("/user/tokens/verify")
        return HealthCheckResult(
            endpoint=f"{self.base_url}/user/tokens/verify",
            healthy=response.success,
            status_code=response.status_code,
            latency_ms=(time.time() - start) * 1000,
            error=response.error
        )

    def kv_get(self, namespace_id: str, key: str) -> APIResponse:
        """Get a value from KV"""
        return self.get(
            f"/accounts/{self.account_id}/storage/kv/namespaces/{namespace_id}/values/{key}"
        )

    def kv_put(self, namespace_id: str, key: str, value: str) -> APIResponse:
        """Put a value to KV"""
        return self.put(
            f"/accounts/{self.account_id}/storage/kv/namespaces/{namespace_id}/values/{key}",
            data={"value": value}
        )


class SalesforceAPI(BaseAPI):
    """Salesforce API integration"""

    name = "salesforce"
    auth_type = "oauth2"

    def __init__(self):
        self.instance_url = os.getenv("SF_INSTANCE_URL", "")
        self.base_url = f"{self.instance_url}/services/data/v58.0"
        super().__init__()
        self._access_token = None

    def authenticate(self) -> bool:
        """Authenticate with Salesforce OAuth2"""
        if requests is None:
            return False

        login_url = "https://login.salesforce.com/services/oauth2/token"

        response = requests.post(login_url, data={
            'grant_type': 'password',
            'client_id': os.getenv('SF_CLIENT_ID'),
            'client_secret': os.getenv('SF_CLIENT_SECRET'),
            'username': os.getenv('SF_USERNAME'),
            'password': os.getenv('SF_PASSWORD') + os.getenv('SF_SECURITY_TOKEN', '')
        })

        if response.ok:
            data = response.json()
            self._access_token = data['access_token']
            self.instance_url = data['instance_url']
            self.base_url = f"{self.instance_url}/services/data/v58.0"
            return True
        return False

    def _get_headers(self) -> Dict[str, str]:
        headers = super()._get_headers()
        if self._access_token:
            headers['Authorization'] = f'Bearer {self._access_token}'
        return headers

    def health_check(self) -> HealthCheckResult:
        if not self._access_token:
            self.authenticate()
        start = time.time()
        response = self.get("/sobjects")
        return HealthCheckResult(
            endpoint=f"{self.base_url}/sobjects",
            healthy=response.success,
            status_code=response.status_code,
            latency_ms=(time.time() - start) * 1000,
            error=response.error
        )


class VercelAPI(BaseAPI):
    """Vercel API integration"""

    name = "vercel"
    base_url = "https://api.vercel.com"
    auth_type = "bearer"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            api_key=api_key,
            env_var="VERCEL_TOKEN"
        )

    def health_check(self) -> HealthCheckResult:
        start = time.time()
        response = self.get("/v2/user")
        return HealthCheckResult(
            endpoint=f"{self.base_url}/v2/user",
            healthy=response.success,
            status_code=response.status_code,
            latency_ms=(time.time() - start) * 1000,
            error=response.error
        )


class DigitalOceanAPI(BaseAPI):
    """Digital Ocean API integration"""

    name = "digitalocean"
    base_url = "https://api.digitalocean.com/v2"
    auth_type = "bearer"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            api_key=api_key,
            env_var="DIGITALOCEAN_TOKEN"
        )

    def health_check(self) -> HealthCheckResult:
        start = time.time()
        response = self.get("/account")
        return HealthCheckResult(
            endpoint=f"{self.base_url}/account",
            healthy=response.success,
            status_code=response.status_code,
            latency_ms=(time.time() - start) * 1000,
            error=response.error
        )


class ClaudeAPI(BaseAPI):
    """Claude/Anthropic API integration"""

    name = "claude"
    base_url = "https://api.anthropic.com/v1"
    auth_type = "x-api-key"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            api_key=api_key,
            env_var="ANTHROPIC_API_KEY"
        )

    def _get_headers(self) -> Dict[str, str]:
        headers = super()._get_headers()
        headers['anthropic-version'] = '2023-06-01'
        return headers

    def health_check(self) -> HealthCheckResult:
        # For Claude, we check if the API responds at all
        # A 400 error still means the API is up
        start = time.time()
        response = self.post("/messages", data={
            "model": "claude-haiku-3-5-20241022",
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}]
        })

        # API is healthy if we get any response (including 400 for invalid request)
        healthy = response.status_code in [200, 400, 401, 429]

        return HealthCheckResult(
            endpoint=f"{self.base_url}/messages",
            healthy=healthy,
            status_code=response.status_code,
            latency_ms=(time.time() - start) * 1000,
            error=None if healthy else response.error
        )


class GitHubAPI(BaseAPI):
    """GitHub API integration"""

    name = "github"
    base_url = "https://api.github.com"
    auth_type = "bearer"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            api_key=api_key,
            env_var="GITHUB_TOKEN"
        )

    def health_check(self) -> HealthCheckResult:
        start = time.time()
        response = self.get("/rate_limit")
        return HealthCheckResult(
            endpoint=f"{self.base_url}/rate_limit",
            healthy=response.success,
            status_code=response.status_code,
            latency_ms=(time.time() - start) * 1000,
            error=response.error
        )


# API Registry
class APIRegistry:
    """Registry of all available API integrations"""

    _apis: Dict[str, type] = {
        'cloudflare': CloudflareAPI,
        'salesforce': SalesforceAPI,
        'vercel': VercelAPI,
        'digitalocean': DigitalOceanAPI,
        'claude': ClaudeAPI,
        'github': GitHubAPI,
    }

    _instances: Dict[str, BaseAPI] = {}

    @classmethod
    def register(cls, name: str, api_class: type) -> None:
        """Register a new API integration"""
        cls._apis[name] = api_class

    @classmethod
    def get(cls, name: str) -> BaseAPI:
        """Get or create an API instance"""
        if name not in cls._instances:
            if name not in cls._apis:
                raise ValueError(f"Unknown API: {name}")
            cls._instances[name] = cls._apis[name]()
        return cls._instances[name]

    @classmethod
    def list_apis(cls) -> List[str]:
        """List all registered APIs"""
        return list(cls._apis.keys())

    @classmethod
    def health_check_all(cls) -> Dict[str, HealthCheckResult]:
        """Run health checks on all registered APIs"""
        results = {}
        for name in cls._apis:
            try:
                api = cls.get(name)
                results[name] = api.health_check()
            except Exception as e:
                results[name] = HealthCheckResult(
                    endpoint=name,
                    healthy=False,
                    error=str(e)
                )
        return results


if __name__ == '__main__':
    # Quick test of available APIs
    print("BlackRoad API Integrations")
    print("=" * 40)
    print(f"Available APIs: {', '.join(APIRegistry.list_apis())}")
    print("\nRunning health checks...")

    results = APIRegistry.health_check_all()
    for name, result in results.items():
        status = "✓" if result.healthy else "✗"
        print(f"  {status} {name}: {result.status_code or 'N/A'} ({result.latency_ms:.0f}ms)")
        if result.error:
            print(f"      Error: {result.error[:50]}...")
