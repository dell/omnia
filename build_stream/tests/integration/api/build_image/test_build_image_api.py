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

"""Integration tests for Build Image API."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app


class TestBuildImageAPI:
    """Integration tests for build image API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        """Create authorization headers."""
        return {"Authorization": "Bearer test-client-token"}

    @pytest.fixture
    def correlation_id_header(self):
        """Create correlation ID header."""
        return {"X-Correlation-Id": "test-correlation-123"}

    def test_create_build_image_success_x86_64(self, client, auth_headers, correlation_id_header):
        """Test successful build image creation for x86_64."""
        # First create a job
        job_response = client.post(
            "/api/v1/jobs",
            json={
                "stage": "build-image",
                "input_parameters": {
                    "architecture": "x86_64",
                    "image_key": "test-image",
                    "functional_groups": ["slurm_control_node_x86_64", "slurm_node_x86_64"]
                }
            },
            headers={**auth_headers, **correlation_id_header}
        )
        assert job_response.status_code == 201
        job_id = job_response.json()["job_id"]

        # Now trigger build image stage
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image",
            json={
                "architecture": "x86_64",
                "image_key": "test-image",
                "functional_groups": ["slurm_control_node_x86_64", "slurm_node_x86_64"]
            },
            headers={**auth_headers, **correlation_id_header}
        )

        assert response.status_code == 202
        data = response.json()
        assert data["job_id"] == job_id
        assert data["stage"] == "build-image"
        assert data["status"] == "accepted"
        assert data["architecture"] == "x86_64"
        assert data["image_key"] == "test-image"
        assert data["functional_groups"] == ["slurm_control_node_x86_64", "slurm_node_x86_64"]
        assert "correlation_id" in data
        assert "submitted_at" in data

    def test_create_build_image_success_aarch64(self, client, auth_headers, correlation_id_header):
        """Test successful build image creation for aarch64 with inventory host."""
        # Create job
        job_response = client.post(
            "/api/v1/jobs",
            json={
                "stage": "build-image",
                "input_parameters": {
                    "architecture": "aarch64",
                    "image_key": "test-image",
                    "functional_groups": ["slurm_control_node_aarch64"]
                }
            },
            headers={**auth_headers, **correlation_id_header}
        )
        assert job_response.status_code == 201
        job_id = job_response.json()["job_id"]

        # Create mock config file with inventory host
        with tempfile.TemporaryDirectory() as temp_dir:
            job_dir = Path(temp_dir) / "jobs" / job_id / "input"
            job_dir.mkdir(parents=True)
            
            config_file = job_dir / "build_stream_config.yml"
            config_file.write_text("aarch64_inventory_host: 172.16.0.100\n")

            # Mock the config repository path
            with patch("infra.repositories.nfs_input_repository.NfsInputRepository._config_file_path", temp_dir + "/jobs/build_stream_config.yml"):
                # Trigger build image stage
                response = client.post(
                    f"/api/v1/jobs/{job_id}/stages/build-image",
                    json={
                        "architecture": "aarch64",
                        "image_key": "test-image",
                        "functional_groups": ["slurm_control_node_aarch64"]
                    },
                    headers={**auth_headers, **correlation_id_header}
                )

                assert response.status_code == 202
                data = response.json()
                assert data["architecture"] == "aarch64"

    def test_create_build_image_invalid_architecture(self, client, auth_headers, correlation_id_header):
        """Test build image creation with invalid architecture."""
        # Create job
        job_response = client.post(
            "/api/v1/jobs",
            json={
                "stage": "build-image",
                "input_parameters": {
                    "architecture": "x86_64",
                    "image_key": "test-image",
                    "functional_groups": ["group1"]
                }
            },
            headers={**auth_headers, **correlation_id_header}
        )
        job_id = job_response.json()["job_id"]

        # Try with invalid architecture
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image",
            json={
                "architecture": "invalid_arch",
                "image_key": "test-image",
                "functional_groups": ["group1"]
            },
            headers={**auth_headers, **correlation_id_header}
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "INVALID_ARCHITECTURE"
        assert "Invalid architecture" in data["message"]

    def test_create_build_image_invalid_image_key(self, client, auth_headers, correlation_id_header):
        """Test build image creation with invalid image key."""
        # Create job
        job_response = client.post(
            "/api/v1/jobs",
            json={
                "stage": "build-image",
                "input_parameters": {
                    "architecture": "x86_64",
                    "image_key": "test-image",
                    "functional_groups": ["group1"]
                }
            },
            headers={**auth_headers, **correlation_id_header}
        )
        job_id = job_response.json()["job_id"]

        # Try with invalid image key
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image",
            json={
                "architecture": "x86_64",
                "image_key": "invalid@key",
                "functional_groups": ["group1"]
            },
            headers={**auth_headers, **correlation_id_header}
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "INVALID_IMAGE_KEY"

    def test_create_build_image_aarch64_missing_inventory_host(self, client, auth_headers, correlation_id_header):
        """Test aarch64 build image creation without inventory host."""
        # Create job
        job_response = client.post(
            "/api/v1/jobs",
            json={
                "stage": "build-image",
                "input_parameters": {
                    "architecture": "aarch64",
                    "image_key": "test-image",
                    "functional_groups": ["group1"]
                }
            },
            headers={**auth_headers, **correlation_id_header}
        )
        job_id = job_response.json()["job_id"]

        # Create empty config directory (no inventory host)
        with tempfile.TemporaryDirectory() as temp_dir:
            job_dir = Path(temp_dir) / "jobs" / job_id / "input"
            job_dir.mkdir(parents=True)

            # Mock the config repository path
            with patch("infra.repositories.nfs_build_stream_config_repository.NfsBuildStreamConfigRepository._base_path", temp_dir + "/jobs"):
                # Try aarch64 without inventory host
                response = client.post(
                    f"/api/v1/jobs/{job_id}/stages/build-image",
                    json={
                        "architecture": "aarch64",
                        "image_key": "test-image",
                        "functional_groups": ["group1"]
                    },
                    headers={**auth_headers, **correlation_id_header}
                )

                assert response.status_code == 400
                data = response.json()
                assert data["error"] == "INVENTORY_HOST_MISSING"
                assert "Inventory host is required" in data["message"]

    def test_create_build_image_unauthorized(self, client, correlation_id_header):
        """Test build image creation without authorization."""
        response = client.post(
            "/api/v1/jobs/test-job/stages/build-image",
            json={
                "architecture": "x86_64",
                "image_key": "test-image",
                "functional_groups": ["group1"]
            },
            headers=correlation_id_header  # No auth header
        )

        assert response.status_code == 401

    def test_create_build_image_job_not_found(self, client, auth_headers, correlation_id_header):
        """Test build image creation for non-existent job."""
        response = client.post(
            "/api/v1/jobs/non-existent-job/stages/build-image",
            json={
                "architecture": "x86_64",
                "image_key": "test-image",
                "functional_groups": ["group1"]
            },
            headers={**auth_headers, **correlation_id_header}
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "JOB_NOT_FOUND"

    def test_create_build_image_queue_submission(self, client, auth_headers, correlation_id_header):
        """Test that build image request is submitted to queue."""
        # Create job
        job_response = client.post(
            "/api/v1/jobs",
            json={
                "stage": "build-image",
                "input_parameters": {
                    "architecture": "x86_64",
                    "image_key": "test-image",
                    "functional_groups": ["group1"]
                }
            },
            headers={**auth_headers, **correlation_id_header}
        )
        job_id = job_response.json()["job_id"]

        # Create temporary queue directory
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_dir = Path(temp_dir) / "requests"
            queue_dir.mkdir()

            # Mock queue path
            with patch("infra.repositories.nfs_build_image_queue_repository.NfsBuildImageQueueRepository._queue_path", str(queue_dir)):
                # Trigger build image stage
                response = client.post(
                    f"/api/v1/jobs/{job_id}/stages/build-image",
                    json={
                        "architecture": "x86_64",
                        "image_key": "test-image",
                        "functional_groups": ["group1"]
                    },
                    headers={**auth_headers, **correlation_id_header}
                )

                assert response.status_code == 202

                # Check that request file was created in queue
                request_files = list(queue_dir.glob("*.json"))
                assert len(request_files) == 1

                # Verify request file content
                request_data = json.loads(request_files[0].read_text())
                assert request_data["job_id"] == job_id
                assert request_data["stage_name"] == "build-image"
                assert request_data["architecture"] == "x86_64"
                assert request_data["image_key"] == "test-image"
                assert request_data["functional_groups"] == ["group1"]
                assert request_data["playbook_path"] == "/omnia/build_image_x86_64/build_image_x86_64.yml"
                assert "inventory_host" not in request_data  # Not required for x86_64
