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

    def test_create_build_image_success_x86_64(self, client, auth_headers, job_with_completed_parse_catalog):
        """Test successful build image creation for x86_64."""
        job_id = job_with_completed_parse_catalog

        # Now trigger build image stage
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image",
            json={
                "architecture": "x86_64",
                "image_key": "test-image",
                "functional_groups": ["slurm_control_node_x86_64", "slurm_node_x86_64"]
            },
            headers=auth_headers
        )

        assert response.status_code == 202
        data = response.json()
        assert data["job_id"] == job_id
        assert data["stage"] == "build-image-x86_64"
        assert data["status"] == "accepted"
        assert data["architecture"] == "x86_64"
        assert data["image_key"] == "test-image"
        assert data["functional_groups"] == ["slurm_control_node_x86_64", "slurm_node_x86_64"]
        assert "correlation_id" in data
        assert "submitted_at" in data

    @pytest.mark.skip(reason="Requires complex config file mocking for aarch64 inventory_host")
    def test_create_build_image_success_aarch64(self, client, auth_headers, job_with_completed_parse_catalog):
        """Test successful build image creation for aarch64."""
        job_id = job_with_completed_parse_catalog

        # Trigger build image stage with inventory_host parameter
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image",
            json={
                "architecture": "aarch64",
                "image_key": "test-image",
                "functional_groups": ["slurm_control_node_aarch64"],
                "inventory_host": "172.16.0.100"
            },
            headers=auth_headers
        )

        assert response.status_code == 202
        data = response.json()
        assert data["stage"] == "build-image-aarch64"
        assert data["architecture"] == "aarch64"

    def test_create_build_image_invalid_architecture(self, client, auth_headers, job_with_completed_parse_catalog):
        """Test build image creation with invalid architecture."""
        job_id = job_with_completed_parse_catalog

        # Try with invalid architecture
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image",
            json={
                "architecture": "invalid_arch",
                "image_key": "test-image",
                "functional_groups": ["group1"]
            },
            headers=auth_headers
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_build_image_invalid_image_key(self, client, auth_headers, job_with_completed_parse_catalog):
        """Test build image creation with invalid image key."""
        job_id = job_with_completed_parse_catalog

        # Try with invalid image key
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image",
            json={
                "architecture": "x86_64",
                "image_key": "invalid@key",
                "functional_groups": ["group1"]
            },
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_create_build_image_aarch64_missing_inventory_host(self, client, auth_headers, job_with_completed_parse_catalog):
        """Test aarch64 build image creation without inventory host."""
        job_id = job_with_completed_parse_catalog

        # Try aarch64 without inventory host
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image",
            json={
                "architecture": "aarch64",
                "image_key": "test-image",
                "functional_groups": ["slurm_control_node_aarch64"]
            },
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_create_build_image_unauthorized(self, client):
        """Test build image creation without authorization."""
        response = client.post(
            "/api/v1/jobs/test-job/stages/build-image",
            json={
                "architecture": "x86_64",
                "image_key": "test-image",
                "functional_groups": ["group1"]
            }
        )
        # Without auth header, may get 400 for invalid job or 401
        assert response.status_code in [400, 401]

    def test_create_build_image_job_not_found(self, client, auth_headers):
        """Test build image creation for non-existent job."""
        response = client.post(
            "/api/v1/jobs/non-existent-job/stages/build-image",
            json={
                "architecture": "x86_64",
                "image_key": "test-image",
                "functional_groups": ["group1"]
            },
            headers=auth_headers
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    @pytest.mark.skip(reason="Requires complex file system mocking for queue directory")
    def test_create_build_image_queue_submission(self, client, auth_headers, job_with_completed_parse_catalog):
        """Test that build image request is submitted to queue."""
        job_id = job_with_completed_parse_catalog

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
                    headers=auth_headers
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
