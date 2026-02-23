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

"""Shared pytest fixtures for Build Stream API tests.

Note: This conftest is for mock-based unit/integration tests.
E2E integration tests use tests/integration/conftest.py which does not
import the app directly (it runs the server as a subprocess).
"""

# pylint: disable=redefined-outer-name,global-statement,import-outside-toplevel,protected-access

import base64
import sys
from pathlib import Path
from typing import Dict, Generator

import pytest

# Note: pythonpath is set in pytest.ini at project root

# Lazy imports to avoid triggering FastAPI route registration
# when running E2E tests that don't need these fixtures
_APP = None
_AUTH_SERVICE = None
_AUTH_ROUTES = None
_MOCK_VAULT_CLIENT = None


def _get_app():
    """Lazy import of FastAPI app."""
    global _APP
    if _APP is None:
        from main import app  # noqa: PLC0415
        _APP = app
    return _APP


def _get_auth_service():
    """Lazy import of AuthService."""
    global _AUTH_SERVICE
    if _AUTH_SERVICE is None:
        from api.auth.service import AuthService  # noqa: PLC0415
        _AUTH_SERVICE = AuthService
    return _AUTH_SERVICE


def _get_auth_routes():
    """Lazy import of auth routes."""
    global _AUTH_ROUTES
    if _AUTH_ROUTES is None:
        from api.auth import routes as auth_routes  # noqa: PLC0415
        _AUTH_ROUTES = auth_routes
    return _AUTH_ROUTES


def _get_mock_vault_client():
    """Lazy import of MockVaultClient."""
    global _MOCK_VAULT_CLIENT
    if _MOCK_VAULT_CLIENT is None:
        from tests.mocks.mock_vault_client import MockVaultClient  # noqa: PLC0415
        _MOCK_VAULT_CLIENT = MockVaultClient
    return _MOCK_VAULT_CLIENT


_MOCK_JWT_HANDLER = None


def _get_mock_jwt_handler():
    """Lazy import of MockJWTHandler."""
    global _MOCK_JWT_HANDLER
    if _MOCK_JWT_HANDLER is None:
        from tests.mocks.mock_jwt_handler import MockJWTHandler  # noqa: PLC0415
        _MOCK_JWT_HANDLER = MockJWTHandler
    return _MOCK_JWT_HANDLER


@pytest.fixture
def mock_vault_client():
    """Create a fresh MockVaultClient instance.

    Returns:
        MockVaultClient with default test credentials.
    """
    mock_vault_client = _get_mock_vault_client()
    return mock_vault_client()


@pytest.fixture
def mock_vault_with_client(mock_vault_client):  # noqa: W0621
    """Create a MockVaultClient with an existing registered client.

    Args:
        mock_vault_client: Base mock vault client.

    Returns:
        MockVaultClient with one pre-registered client.
    """
    mock_vault_client.add_test_client()
    return mock_vault_client


@pytest.fixture
def auth_service(mock_vault_client):  # noqa: W0621
    """Create an AuthService with mock vault client.

    Args:
        mock_vault_client: Mock vault client fixture.

    Returns:
        AuthService configured with mock vault.
    """
    auth_service_class = _get_auth_service()
    return auth_service_class(vault_client=mock_vault_client)


@pytest.fixture
def mock_jwt_handler():
    """Create a fresh MockJWTHandler instance.

    Returns:
        MockJWTHandler for testing JWT operations.
    """
    mock_jwt_handler = _get_mock_jwt_handler()
    return mock_jwt_handler()


@pytest.fixture
def test_client(mock_vault_client, mock_jwt_handler) -> Generator:  # noqa: W0621
    """Create a FastAPI TestClient with mocked dependencies.

    Args:
        mock_vault_client: Mock vault client fixture.
        mock_jwt_handler: Mock JWT handler fixture.

    Yields:
        TestClient configured for testing.
    """
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from api.auth.routes import get_auth_service  # noqa: PLC0415

    app = _get_app()
    auth_service_class = _get_auth_service()

    test_auth_service = auth_service_class(
        vault_client=mock_vault_client,
        jwt_handler=mock_jwt_handler,
    )

    # Override the dependency injection
    app.dependency_overrides[get_auth_service] = lambda: test_auth_service

    with TestClient(app) as client:
        yield client

    # Clean up dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture
def test_client_with_existing_client(  # noqa: C0301,W0621
        mock_vault_with_client, mock_jwt_handler
    ) -> Generator:
    """Create a TestClient with a pre-registered client in vault.

    Args:
        mock_vault_with_client: Mock vault with existing client.
        mock_jwt_handler: Mock JWT handler fixture.

    Yields:
        TestClient configured for testing max client scenarios.
    """
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from api.auth.routes import get_auth_service  # noqa: PLC0415

    app = _get_app()
    auth_service_class = _get_auth_service()

    test_auth_service = auth_service_class(
        vault_client=mock_vault_with_client,
        jwt_handler=mock_jwt_handler,
    )

    # Override the dependency injection
    app.dependency_overrides[get_auth_service] = lambda: test_auth_service

    with TestClient(app) as client:
        yield client

    # Clean up dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture
def valid_auth_header() -> Dict[str, str]:
    """Create valid Basic Auth header for registration endpoint.

    Returns:
        Dictionary with Authorization header.
    """
    mock_vault_client_class = _get_mock_vault_client()
    username = mock_vault_client_class.DEFAULT_TEST_USERNAME
    password = mock_vault_client_class.DEFAULT_TEST_PASSWORD
    credentials = base64.b64encode(
        f"{username}:{password}".encode()
    ).decode()
    return {"Authorization": f"Basic {credentials}"}


@pytest.fixture
def invalid_auth_header() -> Dict[str, str]:
    """Create invalid Basic Auth header.

    Returns:
        Dictionary with invalid Authorization header.
    """
    credentials = base64.b64encode(b"wrong_user:wrong_password").decode()
    return {"Authorization": f"Basic {credentials}"}


@pytest.fixture
def valid_registration_request() -> Dict:
    """Create a valid client registration request body.

    Returns:
        Dictionary with valid registration data.
    """
    return {
        "client_name": "test-client-01",
        "description": "Test client for unit tests",
        "allowed_scopes": ["catalog:read", "catalog:write"],
    }


@pytest.fixture
def minimal_registration_request() -> Dict:
    """Create a minimal valid registration request (only required fields).

    Returns:
        Dictionary with minimal registration data.
    """
    return {
        "client_name": "minimal-client",
    }


@pytest.fixture
def valid_token_request() -> Dict:
    """Create a valid token request body template.

    Note: client_id and client_secret must be filled in after registration.

    Returns:
        Dictionary with token request template.
    """
    return {
        "grant_type": "client_credentials",
        "client_id": None,
        "client_secret": None,
    }


def generate_test_client_secret() -> str:
    """Generate a test client secret that is different from the valid one.
    
    Returns:
        Invalid client secret string for testing (valid format, wrong value).
    """
    return "bld_s_invalid_test_secret_12345"


def generate_invalid_client_id() -> str:
    """Generate an invalid client ID for testing.
    
    Returns:
        Invalid client ID string (contains invalid characters).
    """
    return "invalid@client#id"


def generate_invalid_client_secret() -> str:
    """Generate an invalid client secret for testing.
    
    Returns:
        Invalid client secret string (too short).
    """
    return "short"
