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

"""Shared fixtures for Catalog Roles API integration tests."""

import os
from pathlib import Path
from typing import Dict

import pytest

# Use file-based SQLite database for integration tests
@pytest.fixture(scope="function")
def client(tmp_path):
    """Create test client with fresh container for each test."""
    os.environ["ENV"] = "dev"
    # Use file-based SQLite database for integration tests
    db_file = tmp_path / "test.db"
    db_url = f"sqlite:///{db_file}"
    os.environ["DATABASE_URL"] = db_url
    
    # Import app after setting DATABASE_URL
    from main import app

    def mock_verify_token():
        return {
            "sub": "test-client-123",
            "client_id": "test-client-123",
            "scopes": ["job:write", "job:read", "catalog:read"]
        }

    from api.dependencies import verify_token
    app.dependency_overrides[verify_token] = mock_verify_token
    
    # Create database tables before starting test client
    from infra.db.models import Base
    import infra.db.config as config_module
    import importlib
    
    # Refresh db_config to pick up new DATABASE_URL
    config_module.db_config = config_module.DatabaseConfig()
    
    # Re-import session module to pick up new db_config
    import infra.db.session
    importlib.reload(infra.db.session)
    session_module = infra.db.session
    
    engine = session_module._get_engine()
    Base.metadata.create_all(engine)
    
    from fastapi.testclient import TestClient
    with TestClient(app) as test_client:
        yield test_client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture(name="uuid_generator")
def uuid_generator_fixture():
    """UUID generator for test fixtures."""
    from infra.id_generator import UUIDv4Generator
    return UUIDv4Generator()


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
def created_job(client, auth_headers) -> str:
    """Create a job and return its job_id."""
    payload = {"client_id": "test-client-123", "client_name": "test-client"}
    response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)
    assert response.status_code == 201
    return response.json()["job_id"]


@pytest.fixture
def job_with_completed_parse_catalog(client, auth_headers, created_job, monkeypatch) -> str:
    """Create a job with a completed parse-catalog stage."""
    from core.jobs.entities import Stage
    from core.jobs.value_objects import JobId, StageName, StageState, StageType
    
    # Mock the stage repository to return a completed parse-catalog stage
    def mock_find_by_job_and_name(self, job_id, stage_name):
        # Handle JobId objects or string job_id
        job_id_str = str(job_id)
        
        if stage_name.value == StageType.PARSE_CATALOG.value:
            stage = Stage(
                job_id=JobId(job_id_str),
                stage_name=StageName(StageType.PARSE_CATALOG.value),
                stage_state=StageState.COMPLETED,
                attempt=1
            )
            return stage
        return None
    
    # Apply the mock - in dev mode, it uses container's stage repository
    from container import container
    monkeypatch.setattr(
        container.stage_repository().__class__,
        "find_by_job_and_name",
        mock_find_by_job_and_name
    )
    
    return created_job
