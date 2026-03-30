# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared fixtures for User Acceptance Tests (UAT).

These fixtures assume the Build Stream API server is already running and configured.
Tests focus on API contract validation and user workflows without infrastructure setup.
"""

import os
import uuid
from typing import Dict, Generator
from unittest.mock import patch
from pathlib import Path

import httpx
import pytest

# UAT Configuration
# Direct mapping of environment variables to their default values
UAT_CONFIG = {
    "BUILD_STREAM_BASE_URL": "http://localhost:8000",
    "BUILD_STREAM_AUTH_USERNAME": "build_stream_registrar",
    "BUILD_STREAM_CLIENT_NAME": "uat-test-client",
    "BUILD_STREAM_CLIENT_SCOPES": ["catalog:read", "catalog:write", "job:read", "job:write"],
    # Required variables (no defaults - must be set in environment)
    "BUILD_STREAM_AUTH_PASSWORD": None,  # Required
    "BUILD_STREAM_CLIENT_ID": None,      # Required
    "BUILD_STREAM_CLIENT_SECRET": None,  # Required
}

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    
    # Try multiple paths for .env file
    env_paths = [
        # Relative to conftest.py (most reliable)
        Path(__file__).parent.parent.parent / ".env",
        # Current working directory
        Path.cwd() / ".env",
        # One level up from current directory
        Path.cwd().parent / ".env"
    ]
    
    env_loaded = False
    for env_file in env_paths:
        print(f"\nChecking for .env file at: {env_file}")
        if env_file.exists():
            load_dotenv(env_file)
            print(f"Loaded environment variables from {env_file}")
            env_loaded = True
            break
    
    if not env_loaded:
        print("⚠️ No .env file found in any of the expected locations")
        
except ImportError:
    # python-dotenv not available, continue without it
    print("⚠️ python-dotenv not available, environment variables not loaded from .env")
    pass

@pytest.fixture(scope="session")
def base_url() -> str:
    """Get the API server base URL from environment variable or default.
    
    Returns:
        Base URL for API requests.
    """
    return os.getenv("BUILD_STREAM_BASE_URL", UAT_CONFIG["BUILD_STREAM_BASE_URL"])


@pytest.fixture(scope="session")
def auth_username() -> str:
    """Get the auth username from environment variable or default.
    
    Returns:
        Username for OAuth registration.
    """
    return os.getenv("BUILD_STREAM_AUTH_USERNAME", UAT_CONFIG["BUILD_STREAM_AUTH_USERNAME"])


@pytest.fixture(scope="session")
def auth_password() -> str:
    """Get the auth password from environment variable.
    
    Returns:
        Password for OAuth registration.
        
    Raises:
        ValueError: If BUILD_STREAM_AUTH_PASSWORD is not set.
    """
    password = os.getenv("BUILD_STREAM_AUTH_PASSWORD")
    if not password:
        raise ValueError(
            "BUILD_STREAM_AUTH_PASSWORD environment variable is required for UAT tests. "
            "Set it to the registration password for the Build Stream API."
        )
    return password


@pytest.fixture(scope="session")
def client_name() -> str:
    """Get the client name from environment variable or use default with unique suffix.
    
    Returns:
        Client name for OAuth registration.
    """
    # Environment variable has highest priority
    env_name = os.getenv("BUILD_STREAM_CLIENT_NAME")
    if env_name:
        return env_name
    
    # Use default with unique suffix to avoid conflicts
    base_name = UAT_CONFIG["BUILD_STREAM_CLIENT_NAME"]
    unique_suffix = str(uuid.uuid4())[:8]
    return f"{base_name}-{unique_suffix}"


@pytest.fixture(scope="session")
def client_scopes() -> list:
    """Get the client scopes from environment variable or use default.
    
    Returns:
        List of scopes for OAuth registration.
    """
    # Environment variable has highest priority
    env_scopes = os.getenv("BUILD_STREAM_CLIENT_SCOPES")
    if env_scopes:
        return [scope.strip() for scope in env_scopes.split(',')]
    
    return UAT_CONFIG["BUILD_STREAM_CLIENT_SCOPES"]


@pytest.fixture(scope="session")
def client_id() -> str:
    """Get the client ID from environment variable.
    
    Returns:
        Client ID for OAuth authentication.
    """
    client_id = os.getenv("BUILD_STREAM_CLIENT_ID")
    if not client_id:
        raise ValueError(
            "BUILD_STREAM_CLIENT_ID environment variable is required for UAT tests. "
            "Set it to the existing client ID or use client registration flow."
        )
    return client_id


@pytest.fixture(scope="session")
def client_secret() -> str:
    """Get the client secret from environment variable.
    
    Returns:
        Client secret for OAuth authentication.
    """
    client_secret = os.getenv("BUILD_STREAM_CLIENT_SECRET")
    if not client_secret:
        raise ValueError(
            "BUILD_STREAM_CLIENT_SECRET environment variable is required for UAT tests. "
            "Set it to the existing client secret or use client registration flow."
        )
    return client_secret


@pytest.fixture(scope="session")
def http_client(base_url: str) -> Generator[httpx.Client, None, None]:
    """Create httpx client configured for API requests.
    
    Args:
        base_url: Base URL for API requests.
        
    Yields:
        Configured httpx.Client instance.
    """
    # Disable SSL verification for development environments with self-signed certificates
    # For HTTPS URLs in development, we often have self-signed certificates
    verify_ssl = not base_url.startswith("https://")  # Disable SSL for HTTPS in dev
    
    with httpx.Client(
        base_url=base_url,
        timeout=30.0,
        headers={"User-Agent": "UAT-Tests/1.0"},
        verify=verify_ssl
    ) as client:
        yield client


@pytest.fixture(scope="session")
def registered_client(http_client: httpx.Client, auth_username: str, auth_password: str,
                      client_name: str, client_scopes: list) -> Dict[str, str]:
    """Get OAuth client credentials for UAT tests with registration fallback.
    
    This fixture first tries to use existing client credentials from environment variables.
    If that fails, it attempts to register a new client using auth credentials.
    
    Args:
        http_client: httpx client for API requests.
        auth_username: Registration username.
        auth_password: Registration password.
        client_name: OAuth client name.
        client_scopes: OAuth client scopes.
        
    Returns:
        Dictionary containing client credentials and access token.
    """
    import base64
    
    # Try to use existing client credentials from environment first
    env_client_id = os.getenv("BUILD_STREAM_CLIENT_ID")
    env_client_secret = os.getenv("BUILD_STREAM_CLIENT_SECRET")
    
    if env_client_id and env_client_secret:
        print("🔑 Using existing client credentials from environment")
        try:
            # Try to get token with existing credentials
            token_data = {
                "grant_type": "client_credentials",
                "client_id": env_client_id,
                "client_secret": env_client_secret,
                "scope": " ".join(client_scopes),
            }
            
            credentials = base64.b64encode(f"{env_client_id}:{env_client_secret}".encode()).decode()
            token_headers = {
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            
            token_response = http_client.post(
                "/api/v1/auth/token", 
                data=token_data,
                headers=token_headers
            )
            
            if token_response.status_code == 200:
                token_result = token_response.json()
                print("✅ Successfully authenticated with existing client")
                return {
                    "client_id": env_client_id,
                    "client_secret": env_client_secret,
                    "access_token": token_result["access_token"],
                    "token_type": "Bearer",
                }
            else:
                print(f"⚠️ Existing client authentication failed: {token_response.status_code}")
        except Exception as e:
            print(f"⚠️ Failed to use existing client: {e}")
    
    # Fallback: Register a new client
    print("🔄 Attempting to register new client...")
    
    registration_data = {
        "client_name": client_name,
        "allowed_scopes": client_scopes,
    }
    
    # Basic auth for registration
    reg_credentials = base64.b64encode(f"{auth_username}:{auth_password}".encode()).decode()
    reg_headers = {
        "Authorization": f"Basic {reg_credentials}",
        "Content-Type": "application/json",
    }
    
    try:
        reg_response = http_client.post("/api/v1/auth/register", json=registration_data, headers=reg_headers)
        if reg_response.status_code == 201:
            # Registration successful
            reg_result = reg_response.json()
            client_id = reg_result["client_id"]
            client_secret = reg_result["client_secret"]
            print(f"✅ Successfully registered new client: {client_id}")
        elif reg_response.status_code == 409:
            # Client already exists - this shouldn't happen with unique names
            raise ValueError(f"Client '{client_name}' already exists. Try a different client name.")
        else:
            raise RuntimeError(f"Client registration failed: {reg_response.status_code} - {reg_response.text}")
    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to connect to API server for registration: {e}")
    
    # Get access token with newly registered client
    token_data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": " ".join(client_scopes),
    }
    
    token_headers = {
        "Authorization": f"Basic {reg_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    try:
        token_response = http_client.post(
            "/api/v1/auth/token", 
            data=token_data,
            headers=token_headers
        )
        if token_response.status_code == 200:
            token_result = token_response.json()
            print("✅ Successfully obtained access token")
        else:
            raise RuntimeError(f"Token generation failed: {token_response.status_code} - {token_response.text}")
    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to get access token: {e}")
    
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "access_token": token_result["access_token"],
        "token_type": "Bearer",
    }


@pytest.fixture(scope="function")
def auth_headers(registered_client: Dict[str, str]) -> Dict[str, str]:
    """Get authorization headers with Bearer token.
    
    Args:
        registered_client: Registered client credentials.
        
    Returns:
        Dictionary with Authorization header.
    """
    return {
        "Authorization": f"Bearer {registered_client['access_token']}",
        "Content-Type": "application/json",
    }


@pytest.fixture(scope="function")
def unique_idempotency_key() -> str:
    """Generate unique idempotency key for each test.
    
    Returns:
        Unique idempotency key.
    """
    return f"uat-test-{uuid.uuid4()}"


@pytest.fixture(scope="function")
def unique_correlation_id() -> str:
    """Generate unique correlation ID for each test.
    
    Returns:
        Unique correlation ID.
    """
    return str(uuid.uuid4())


@pytest.fixture(scope="function")
def auth_headers_with_ids(auth_headers: Dict[str, str], unique_idempotency_key: str, 
                         unique_correlation_id: str) -> Dict[str, str]:
    """Get authorization headers with unique IDs.
    
    Args:
        auth_headers: Base authorization headers.
        unique_idempotency_key: Unique idempotency key.
        unique_correlation_id: Unique correlation ID.
        
    Returns:
        Headers with Authorization, Idempotency-Key, and X-Correlation-Id.
    """
    headers = auth_headers.copy()
    headers["Idempotency-Key"] = unique_idempotency_key
    headers["X-Correlation-Id"] = unique_correlation_id
    return headers


@pytest.fixture(scope="function")
def invalid_job_id() -> str:
    """Generate invalid job ID for testing error scenarios.
    
    Returns:
        Invalid job ID that doesn't exist.
    """
    return "00000000-0000-0000-0000-000000000000"


@pytest.fixture(scope="function")
def sample_catalog_content() -> bytes:
    """Get sample catalog content for testing parse catalog.
    
    Returns:
        Sample catalog JSON as bytes.
    """
    import json
    catalog_data = {
        "metadata": {
            "name": "test-catalog",
            "version": "1.0.0",
            "description": "Test catalog for UAT",
        },
        "software": [
            {
                "name": "test-package",
                "version": "1.0.0",
                "arch": "x86_64",
                "repository": "test-repo",
            }
        ],
    }
    return json.dumps(catalog_data, indent=2).encode('utf-8')


@pytest.fixture(scope="session")
def real_catalog_content() -> bytes:
    """Load real RHEL catalog content for testing.
    
    Returns:
        Real catalog JSON content as bytes for file upload testing.
    """
    from pathlib import Path
    catalog_path = Path(__file__).parent.parent.parent.parent / "examples" / "catalog" / "catalog_rhel.json"
    with open(catalog_path, "rb") as f:
        return f.read()
