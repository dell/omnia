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

"""Shared fixtures for Jobs API integration tests."""

import os
from typing import Dict, Optional

import pytest
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.testclient import TestClient

from main import app
from api.dependencies import verify_token
from infra.id_generator import UUIDv4Generator

_bearer = HTTPBearer(auto_error=False)


def _mock_verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    """Mock verify_token that uses the token value as client_id."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "missing_token", "error_description": "Authorization header is required"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    return {
        "client_id": token,
        "client_name": token,
        "scopes": ["job:write", "job:read"],
        "token_id": "test-token-id",
    }


@pytest.fixture(scope="function")
def client(tmp_path):
    """Create test client with mocked JWT auth and fresh DB for each test."""
    os.environ["ENV"] = "dev"
    db_file = tmp_path / "test.db"
    db_url = f"sqlite:///{db_file}"
    os.environ["DATABASE_URL"] = db_url

    import infra.db.config as config_module  # pylint: disable=import-outside-toplevel
    import importlib  # pylint: disable=import-outside-toplevel

    config_module.db_config = config_module.DatabaseConfig()

    import infra.db.session  # pylint: disable=import-outside-toplevel
    importlib.reload(infra.db.session)
    session_module = infra.db.session

    from sqlalchemy import create_engine  # pylint: disable=import-outside-toplevel
    engine = create_engine(db_url)
    session_module._engine = engine  # pylint: disable=protected-access
    session_module._session_factory = None  # pylint: disable=protected-access

    from infra.db.models import Base  # pylint: disable=import-outside-toplevel
    Base.metadata.create_all(engine)

    app.dependency_overrides[verify_token] = _mock_verify_token
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def unauth_client():
    """Create test client without auth mock for testing real auth behaviour."""
    return TestClient(app)


@pytest.fixture(name="uuid_generator")
def uuid_generator_fixture():
    """UUID generator for test fixtures."""
    return UUIDv4Generator()


@pytest.fixture
def auth_headers(uuid_generator) -> Dict[str, str]:
    """Standard authentication headers for testing."""
    return {
        "Authorization": "Bearer test-client-123",
        "X-Correlation-Id": str(uuid_generator.generate()),
        "Idempotency-Key": f"test-key-{uuid_generator.generate()}",
    }


@pytest.fixture
def unique_idempotency_key(uuid_generator) -> str:
    """Generate unique idempotency key for each test."""
    return f"test-key-{uuid_generator.generate()}"


@pytest.fixture
def unique_correlation_id(uuid_generator) -> str:
    """Generate unique correlation ID for each test."""
    return str(uuid_generator.generate())
