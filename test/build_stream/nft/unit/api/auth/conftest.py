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

# pylint: disable=C0114,C0115,C0413,C0411,W0105,C0103,R0914,C0415,W0212,W0611,W0621,W0613,R0903

"""Shared fixtures for auth service tests."""

import base64
import os
from typing import Dict, Generator

import pytest

# PyJWT compatibility shim for different versions - MUST be at the very top
import jwt.exceptions
# Map newer exception names to older ones or create them
if not hasattr(jwt.exceptions, 'DecodeError'):
    jwt.exceptions.DecodeError = jwt.exceptions.JWTDecodeError
if not hasattr(jwt.exceptions, 'ExpiredSignatureError'):
    class ExpiredSignatureError(jwt.exceptions.JWTException):
        pass
    jwt.exceptions.ExpiredSignatureError = ExpiredSignatureError
if not hasattr(jwt.exceptions, 'InvalidAudienceError'):
    class InvalidAudienceError(jwt.exceptions.JWTException):
        pass
    jwt.exceptions.InvalidAudienceError = InvalidAudienceError
if not hasattr(jwt.exceptions, 'InvalidIssuerError'):
    class InvalidIssuerError(jwt.exceptions.JWTException):
        pass
    jwt.exceptions.InvalidIssuerError = InvalidIssuerError
if not hasattr(jwt.exceptions, 'InvalidSignatureError'):
    class InvalidSignatureError(jwt.exceptions.JWTException):
        pass
    jwt.exceptions.InvalidSignatureError = InvalidSignatureError

from fastapi.testclient import TestClient

from api.auth.service import AuthService
from nft.mocks.mock_jwt_handler import MockJWTHandler
from nft.mocks.mock_vault_client import MockVaultClient


@pytest.fixture
def mock_vault_client() -> MockVaultClient:
    """Create a mock vault client for testing."""
    return MockVaultClient()


@pytest.fixture
def mock_vault_with_client(mock_vault_client: MockVaultClient) -> MockVaultClient:
    """Create a mock vault client that already holds one registered client."""
    mock_vault_client.add_test_client()
    return mock_vault_client


@pytest.fixture
def mock_jwt_handler() -> MockJWTHandler:
    """Create a mock JWT handler for testing."""
    return MockJWTHandler()


@pytest.fixture
def auth_service(mock_vault_client: MockVaultClient) -> AuthService:
    """Create an auth service instance with mock vault client."""
    return AuthService(vault_client=mock_vault_client)


def _auth_test_client(tmp_path, vault_client, jwt_handler) -> Generator[TestClient, None, None]:
    """Yield a TestClient whose auth service uses the given mock vault and JWT handler.

    The app gets a fresh file-based SQLite database and container per test, and
    ``get_auth_service`` is overridden so registration and token requests are
    verified against the mocks instead of the real vault.
    """
    # Register JSONB type compiler for SQLite before importing app
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # pylint: disable=import-outside-toplevel

    def visit_JSONB(self, type_, **kw):
        return self.visit_JSON(type_, **kw)

    SQLiteTypeCompiler.visit_JSONB = visit_JSONB

    os.environ["ENV"] = "dev"
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'test.db'}"

    from main import app  # pylint: disable=import-outside-toplevel
    from container import DevContainer  # pylint: disable=import-outside-toplevel
    from api.auth.routes import get_auth_service  # pylint: disable=import-outside-toplevel

    container = DevContainer()
    container.init_resources()
    app.container = container

    service = AuthService(vault_client=vault_client, jwt_handler=jwt_handler)
    app.dependency_overrides[get_auth_service] = lambda: service
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_client(tmp_path, mock_vault_client, mock_jwt_handler) -> Generator[TestClient, None, None]:
    """Create a test client backed by an empty mock vault."""
    yield from _auth_test_client(tmp_path, mock_vault_client, mock_jwt_handler)


@pytest.fixture(scope="function")
def test_client_with_existing_client(
    tmp_path, mock_vault_with_client, mock_jwt_handler
) -> Generator[TestClient, None, None]:
    """Create a test client whose mock vault already holds one registered client."""
    yield from _auth_test_client(tmp_path, mock_vault_with_client, mock_jwt_handler)


@pytest.fixture
def valid_auth_header() -> Dict[str, str]:
    """Create a valid Basic Auth header for the registration endpoint."""
    credentials = base64.b64encode(
        f"{MockVaultClient.DEFAULT_TEST_USERNAME}:"
        f"{MockVaultClient.DEFAULT_TEST_PASSWORD}".encode()
    ).decode()
    return {"Authorization": f"Basic {credentials}"}


@pytest.fixture
def invalid_auth_header() -> Dict[str, str]:
    """Create a Basic Auth header with wrong credentials."""
    credentials = base64.b64encode(b"wrong_user:wrong_password").decode()
    return {"Authorization": f"Basic {credentials}"}


@pytest.fixture
def valid_registration_request() -> Dict:
    """Create a valid registration request for testing."""
    return {
        "client_name": "test-client-01",
        "description": "Test client for unit tests",
        "allowed_scopes": ["catalog:read", "catalog:write"],
    }


@pytest.fixture
def minimal_registration_request() -> Dict:
    """Create a minimal registration request (only required fields)."""
    return {"client_name": "minimal-client"}
