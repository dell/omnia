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

"""Unit tests for wizard API routes."""

# pylint: disable=missing-function-docstring,redefined-outer-name
import time
import pytest
from fastapi.testclient import TestClient

from backend.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as c:
        yield c



def _poll_job(client, job_id, timeout=5.0, interval=0.1):
    """Poll a generation job until it completes or times out."""
    deadline = time.monotonic() + timeout
    last_resp = None
    while time.monotonic() < deadline:
        resp = client.get(
            f"/api/v1/config/generate-all/{job_id}",
        )
        last_resp = resp
        status = resp.json().get("status")
        if resp.status_code == 200 and status in (
            "completed", "failed",
        ):
            return resp
        time.sleep(interval)
    return last_resp


class TestGenerateAllEndpoint:
    """Tests for POST /api/v1/config/generate-all."""

    def test_returns_job_id(self, client, tmp_path, sample_wizard_data):
        sample_wizard_data["output_dir"] = str(tmp_path)
        response = client.post(
            "/api/v1/config/generate-all",
            json=sample_wizard_data,
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"

    def test_get_job_status(self, client, tmp_path, sample_wizard_data):
        sample_wizard_data["output_dir"] = str(tmp_path)
        create_response = client.post(
            "/api/v1/config/generate-all",
            json=sample_wizard_data,
        )
        job_id = create_response.json()["job_id"]

        status_response = _poll_job(client, job_id)
        assert status_response.status_code == 200
        assert "status" in status_response.json()

    def test_get_nonexistent_job_returns_404(self, client):
        response = client.get(
            "/api/v1/config/generate-all/nonexistent-id",
        )
        assert response.status_code == 404


class TestDownloadFiles:
    """Tests for POST /api/v1/config/download-files."""

    def test_returns_404_when_dir_not_exists(self, client):
        response = client.post(
            "/api/v1/config/download-files",
            json={"input_dir": "/nonexistent/path/that/does/not/exist"}
        )
        assert response.status_code == 404
