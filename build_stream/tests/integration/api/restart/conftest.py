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

"""Shared fixtures for Restart API integration tests."""

import os
from typing import Dict

import pytest


@pytest.fixture(scope="function")
def client(tmp_path):
    """Create test client with fresh container for each test."""
    os.environ["ENV"] = "dev"
    db_file = tmp_path / "test.db"
    db_url = f"sqlite:///{db_file}"
    os.environ["DATABASE_URL"] = db_url

    from main import app

    def mock_verify_token():
        return {
            "sub": "test-client-123",
            "client_id": "test-client-123",
            "scopes": ["job:write", "job:read"]
        }

    from api.dependencies import verify_token
    app.dependency_overrides[verify_token] = mock_verify_token

    from infra.db.models import Base
    import infra.db.config as config_module
    import importlib

    config_module.db_config = config_module.DatabaseConfig()

    import infra.db.session
    importlib.reload(infra.db.session)
    session_module = infra.db.session

    from sqlalchemy import create_engine
    engine = create_engine(db_url)
    session_module._engine = engine
    session_module._session_factory = None
    Base.metadata.create_all(engine)

    from fastapi.testclient import TestClient
    with TestClient(app) as test_client:
        yield test_client

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
def created_job(client, auth_headers) -> str:
    """Create a job and return its job_id."""
    payload = {"client_id": "test-client-123", "client_name": "test-client"}
    response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)
    assert response.status_code == 201
    return response.json()["job_id"]


@pytest.fixture
def job_with_pending_restart(client, auth_headers, created_job, monkeypatch) -> str:
    """Create a job with a PENDING restart stage."""
    from core.jobs.entities import Stage
    from core.jobs.value_objects import JobId, StageName, StageState, StageType

    def mock_find_by_job_and_name(self, job_id, stage_name):
        job_id_str = str(job_id)

        if stage_name.value == StageType.RESTART.value:
            stage = Stage(
                job_id=JobId(job_id_str),
                stage_name=StageName(StageType.RESTART.value),
                stage_state=StageState.PENDING,
                attempt=1
            )
            return stage
        return None

    from container import container
    monkeypatch.setattr(
        container.stage_repository().__class__,
        "find_by_job_and_name",
        mock_find_by_job_and_name
    )

    return created_job
