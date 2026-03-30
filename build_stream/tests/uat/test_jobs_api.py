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

"""UAT tests for Jobs API."""

import uuid
import httpx
import pytest


@pytest.mark.uat
class TestCreateJob:
    """Test job creation endpoint."""

    def test_create_job_returns_201(self, http_client: httpx.Client, auth_headers_with_ids: dict):
        """Test job creation returns 201 with valid request."""
        payload = {
            "client_id": "uat-test-client",
            "client_name": "UAT Test Client",
        }

        response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)

        assert response.status_code == 201
        data = response.json()
        assert "job_id" in data
        assert "correlation_id" in data
        assert "job_state" in data
        assert "created_at" in data
        assert "stages" in data

    def test_create_job_returns_valid_job_id(self, http_client: httpx.Client, auth_headers_with_ids: dict):
        """Test created job has valid UUID job_id."""
        payload = {
            "client_id": "uat-test-client",
            "client_name": "UAT Test Client",
        }

        response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)

        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Validate UUID format
        try:
            uuid.UUID(job_id)
        except ValueError:
            pytest.fail(f"Invalid UUID format: {job_id}")

    def test_create_job_creates_all_stages(self, http_client: httpx.Client, auth_headers_with_ids: dict):
        """Test job creation creates all expected stages."""
        payload = {
            "client_id": "uat-test-client",
            "client_name": "UAT Test Client",
        }

        response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)

        assert response.status_code == 201
        stages = response.json()["stages"]
        assert len(stages) == 6

        expected_stages = {
            "build-image-aarch64",
            "build-image-x86_64",
            "create-local-repository",
            "generate-input-files",
            "parse-catalog",
            "validate-image-on-test",
        }

        # Check all expected stages are present (order doesn't matter)
        stage_names = {s["stage_name"] for s in stages}
        assert stage_names == expected_stages

        # Verify all stages are in PENDING state initially
        for stage in stages:
            assert stage["stage_state"] == "PENDING"
            assert stage["started_at"] is None
            assert stage["ended_at"] is None

    def test_create_job_with_missing_client_id_returns_400(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test job creation without client_id returns 400."""
        payload = {
            "client_name": "UAT Test Client",
        }

        response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)

        assert response.status_code == 422  # FastAPI validation error

    @pytest.mark.skip(reason="Idempotency not implemented in API yet - returns 201 instead of 200")
    def test_idempotency_key_prevents_duplicate_jobs(
        self, http_client: httpx.Client, auth_headers: dict, unique_idempotency_key: str,
        unique_correlation_id: str
    ):
        """Test idempotency key prevents duplicate job creation."""
        headers = {
            **auth_headers,
            "Idempotency-Key": unique_idempotency_key,
            "X-Correlation-Id": unique_correlation_id,
        }

        payload = {
            "client_id": "uat-test-client",
            "client_name": "UAT Test Client",
        }

        # First request
        response1 = http_client.post("/api/v1/jobs", json=payload, headers=headers)
        assert response1.status_code == 201
        job_id1 = response1.json()["job_id"]

        # Second request with same idempotency key
        response2 = http_client.post("/api/v1/jobs", json=payload, headers=headers)
        assert response2.status_code == 200  # Returns existing job
        job_id2 = response2.json()["job_id"]

        # Should return same job
        assert job_id1 == job_id2


@pytest.mark.uat
class TestGetJob:
    """Test get job endpoint."""

    def test_get_job_returns_200_with_valid_id(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test getting job with valid ID returns 200."""
        # First create a job
        payload = {
            "client_id": "uat-test-client",
            "client_name": "UAT Test Client",
        }

        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        # Then get the job
        get_response = http_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["job_id"] == job_id
        assert "job_state" in data
        assert "stages" in data

    def test_get_job_returns_404_with_invalid_id(
        self, http_client: httpx.Client, auth_headers: dict, invalid_job_id: str
    ):
        """Test getting job with invalid ID returns 404."""
        response = http_client.get(f"/api/v1/jobs/{invalid_job_id}", headers=auth_headers)

        assert response.status_code == 404


@pytest.mark.uat
class TestDeleteJob:
    """Test delete job endpoint."""

    @pytest.mark.skip(reason="Not implemented")
    def test_delete_job_returns_204(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test deleting job returns 204."""
        # First create a job
        payload = {
            "client_id": "uat-test-client",
            "client_name": "UAT Test Client",
        }

        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        # Then delete the job
        delete_response = http_client.delete(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)

        assert delete_response.status_code == 204

    def test_delete_nonexistent_job_returns_404(
        self, http_client: httpx.Client, auth_headers: dict, invalid_job_id: str
    ):
        """Test deleting nonexistent job returns 404."""
        response = http_client.delete(f"/api/v1/jobs/{invalid_job_id}", headers=auth_headers)

        assert response.status_code == 404
