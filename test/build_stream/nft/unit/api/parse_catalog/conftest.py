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

# JSONB shim for SQLite compatibility - MUST be at the very top before any imports
import sqlalchemy.dialects.sqlite.base as sqlite_base
from sqlalchemy import JSON
if not hasattr(sqlite_base, "JSONB"):
    sqlite_base.JSONB = JSON

# PyJWT compatibility shim for different versions
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

"""Shared fixtures for ParseCatalog API tests."""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Generator
from unittest.mock import patch

import pytest
# pylint: disable=C0114,C0115,C0413,C0411,W0105,C0103,R0914,C0415,W0212,W0611,W0621,W0613,R0903


# pylint: disable=R0914,C0415,W0212
# R0914: Test fixture has many local variables for setup
# C0415: Imports inside function needed for proper test isolation
# W0212: Protected access needed for test setup

@pytest.fixture(scope="function")
def client(tmp_path):
    """Create test client with fresh container for each test."""
    # Import UUIDv4Generator inside fixture to ensure shim is applied first
    from infra.id_generator import UUIDv4Generator  # pylint: disable=import-outside-toplevel

    os.environ["ENV"] = "dev"
    db_file = tmp_path / "test.db"
    db_url = f"sqlite:///{db_file}"
    os.environ["DATABASE_URL"] = db_url

    # Set up config path for tests
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "build_stream.ini"
    config_file.write_text("""
[paths]
build_stream_base_path = /tmp/build_stream_test

[artifact_store]
backend = in_memory
working_dir = /tmp/build_stream_test/artifacts
max_file_size_bytes = 10737418240
max_archive_uncompressed_bytes = 53687091200
max_archive_entries = 1000

[file_store]
base_path = /tmp/build_stream_test/nfs
""")
    os.environ["BUILD_STREAM_CONFIG_PATH"] = str(config_file)

    # Reload config before importing app
    import common.config as config_module  # pylint: disable=import-outside-toplevel
    import importlib  # pylint: disable=import-outside-toplevel
    importlib.reload(config_module)

    # Register JSONB type compiler for SQLite before importing container
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # pylint: disable=import-outside-toplevel
    
    # Add visit_JSONB method to SQLiteTypeCompiler
    def visit_JSONB(self, type_, **kw):
        return self.visit_JSON(type_, **kw)

    SQLiteTypeCompiler.visit_JSONB = visit_JSONB

    # Reload container to pick up new config
    import app.container as container_module  # pylint: disable=import-outside-toplevel
    importlib.reload(container_module)

    from main import app  # pylint: disable=import-outside-toplevel

    def mock_verify_token():
        return {
            "sub": "test-client-123",
            "client_id": "test-client-123",
            "scopes": ["job:write", "job:read", "catalog:read"]
        }

    from api.dependencies import verify_token  # pylint: disable=import-outside-toplevel
    app.dependency_overrides[verify_token] = mock_verify_token

    # Config is loaded from file, no need for mock_config function
    # pylint: disable=import-outside-toplevel,protected-access
    from api.upload import dependencies as upload_deps
    container = upload_deps._get_container()
    app.dependency_overrides[upload_deps.get_upload_files_use_case] = (
        container.upload_files_use_case
    )

    from infra.db.models import Base
    import infra.db.config as db_config_module

    db_config_module.db_config = db_config_module.DatabaseConfig()

    import infra.db.session
    importlib.reload(infra.db.session)
    session_module = infra.db.session

    from sqlalchemy import create_engine, event
    from sqlalchemy.pool import StaticPool

    # Use WAL mode and connection pooling to avoid database locks
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False, "timeout": 30},
        poolclass=StaticPool,
        echo=False,
    )

    # Enable WAL mode for better concurrency
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()
    session_module._engine = engine  # pylint: disable=protected-access
    session_module._session_factory = None  # pylint: disable=protected-access
    Base.metadata.create_all(engine)

    from fastapi.testclient import TestClient  # pylint: disable=import-outside-toplevel
    with TestClient(app) as test_client:
        yield test_client

    # Clean up sessions and connections
    try:
        session_module.get_session_factory().close_all()
    except Exception:  # pylint: disable=broad-except
        pass

    try:
        engine.dispose()
    except Exception:  # pylint: disable=broad-except
        pass

    app.dependency_overrides.clear()


@pytest.fixture(name="uuid_generator")
def uuid_generator_fixture():
    """UUID generator for test fixtures."""
    from infra.id_generator import UUIDv4Generator as UUIDv4Gen  # pylint: disable=import-outside-toplevel
    return UUIDv4Gen()


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(uuid_generator) -> Dict[str, str]:
    """Standard authentication headers for testing."""
    return {
        "Authorization": "Bearer test-client-123",
        "X-Correlation-Id": str(uuid_generator.generate()),
        "Idempotency-Key": f"test-key-{uuid_generator.generate()}",
    }


@pytest.fixture
def unique_correlation_id(uuid_generator) -> str:
    """Generate unique correlation ID for each test."""
    return str(uuid_generator.generate())


@pytest.fixture
def created_job(client, auth_headers) -> str:  # pylint: disable=redefined-outer-name
    """Create a job and return its job_id."""
    payload = {"client_id": "test-client-123", "client_name": "test-client"}
    response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)
    assert response.status_code == 201
    return response.json()["job_id"]


@pytest.fixture
def mock_jwt_validation() -> Generator[None, None, None]:
    """Mock JWT validation for tests that use TestClient(app) directly.

    This fixture bypasses JWT validation to allow testing of API endpoints
    without requiring actual JWT keys.
    """
    with patch("api.auth.jwt_handler.JWTHandler.validate_token") as mock_validate:
        # Mock successful token validation
        from api.auth.jwt_handler import TokenData  # pylint: disable=import-outside-toplevel

        now = datetime.now(timezone.utc)
        mock_validate.return_value = TokenData(
            client_id="test-client",
            client_name="test-client",
            scopes=["catalog:read", "catalog:write"],
            issued_at=now,
            expires_at=now + timedelta(hours=1),
            token_id="test-token-id",
        )
        yield
