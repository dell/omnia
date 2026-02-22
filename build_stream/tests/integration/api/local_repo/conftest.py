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

"""Shared fixtures for Local Repository API integration tests."""

import os
from pathlib import Path
from typing import Dict

import pytest
from fastapi.testclient import TestClient
from api.dependencies import verify_token

from main import app
from infra.id_generator import UUIDv4Generator


@pytest.fixture(scope="function")
def client():
    """Create test client with fresh container for each test."""
    os.environ["ENV"] = "dev"

    def mock_verify_token():
        return {
            "sub": "test-client-123",
            "client_id": "test-client-123",
            "scopes": ["job:write", "job:read"]
        }

    app.dependency_overrides[verify_token] = mock_verify_token

    test_client = TestClient(app)

    yield test_client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture(name="uuid_generator")
def uuid_generator_fixture():
    """UUID generator for test fixtures."""
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
def nfs_queue_dir(tmp_path):
    """Create temporary NFS queue directory structure."""
    requests_dir = tmp_path / "requests"
    results_dir = tmp_path / "results"
    archive_dir = tmp_path / "archive" / "results"
    processing_dir = tmp_path / "processing"

    requests_dir.mkdir(parents=True)
    results_dir.mkdir(parents=True)
    archive_dir.mkdir(parents=True)
    processing_dir.mkdir(parents=True)

    return tmp_path


@pytest.fixture
def input_dir(tmp_path):
    """Create temporary input directory with sample files."""
    base = tmp_path / "build_stream"
    return base


def setup_input_files(input_dir_path: Path, job_id: str) -> Path:
    """Create input files for a given job_id."""
    job_input = input_dir_path / job_id / "input"
    job_input.mkdir(parents=True, exist_ok=True)
    (job_input / "config.json").write_text('{"cluster_os": "rhel9.2"}')
    return job_input
