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

import os
from typing import Dict

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
from nft.mocks.mock_vault_client import MockVaultClient


@pytest.fixture
def mock_vault_client() -> MockVaultClient:
    """Create a mock vault client for testing."""
    return MockVaultClient()


@pytest.fixture
def auth_service(mock_vault_client: MockVaultClient) -> AuthService:
    """Create an auth service instance with mock vault client."""
    return AuthService(vault_client=mock_vault_client)


@pytest.fixture(scope="function")
def test_client(tmp_path):
    """Create test client with fresh container for each test."""
    # Register JSONB type compiler for SQLite before importing app
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # pylint: disable=import-outside-toplevel

    # Add visit_JSONB method to SQLiteTypeCompiler
    def visit_JSONB(self, type_, **kw):
        return self.visit_JSON(type_, **kw)

    SQLiteTypeCompiler.visit_JSONB = visit_JSONB

    os.environ["ENV"] = "dev"
    # Use file-based SQLite database for these tests
    db_file = tmp_path / "test.db"
    db_url = f"sqlite:///{db_file}"
    os.environ["DATABASE_URL"] = db_url

    from main import app  # pylint: disable=import-outside-toplevel
    from container import DevContainer  # pylint: disable=import-outside-toplevel

    container = DevContainer()
    container.init_resources()
    app.container = container

    return TestClient(app)


@pytest.fixture
def valid_auth_header() -> Dict[str, str]:
    """Create a valid authorization header for testing."""
    return {"Authorization": "Bearer test_token"}


@pytest.fixture
def valid_registration_request() -> Dict:
    """Create a valid registration request for testing."""
    return {
        "client_name": "test_client",
        "description": "Test client for unit tests"
    }
