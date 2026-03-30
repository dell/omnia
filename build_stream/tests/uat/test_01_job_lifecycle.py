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

"""UAT tests for complete job lifecycle (create, get, delete)."""

import uuid
import httpx
import pytest


@pytest.mark.uat
class TestJobLifecycle:
    """Test complete job lifecycle operations."""

    def test_create_job_success(self, http_client: httpx.Client, auth_headers_with_ids: dict):
        """Test successful job creation."""
        payload = {
            "client_id": "uat-lifecycle-client",
            "client_name": "UAT Lifecycle Test",
        }

        response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)

        assert response.status_code == 201
        data = response.json()
        assert "job_id" in data
        assert "correlation_id" in data
        assert "job_state" in data
        assert data["job_state"] == "CREATED"
        assert "created_at" in data
        assert "stages" in data
        assert len(data["stages"]) == 6

    def test_get_job_after_creation(self, http_client: httpx.Client, auth_headers_with_ids: dict):
        """Test retrieving job immediately after creation."""
        payload = {
            "client_id": "uat-lifecycle-client",
            "client_name": "UAT Lifecycle Test",
        }

        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        get_response = http_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["job_id"] == job_id
        assert "job_state" in data
        assert "stages" in data

    def test_get_nonexistent_job_returns_404(
        self, http_client: httpx.Client, auth_headers: dict
    ):
        """Test getting nonexistent job returns 404."""
        nonexistent_id = str(uuid.uuid4())

        response = http_client.get(f"/api/v1/jobs/{nonexistent_id}", headers=auth_headers)

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_get_job_with_invalid_uuid_returns_400(
        self, http_client: httpx.Client, auth_headers: dict
    ):
        """Test getting job with invalid UUID format returns 400."""
        invalid_id = "not-a-valid-uuid"

        response = http_client.get(f"/api/v1/jobs/{invalid_id}", headers=auth_headers)

        assert response.status_code == 400

    @pytest.mark.skip(reason="DELETE endpoint not implemented yet")
    def test_delete_job_success(self, http_client: httpx.Client, auth_headers_with_ids: dict):
        """Test successful job deletion."""
        payload = {
            "client_id": "uat-lifecycle-client",
            "client_name": "UAT Lifecycle Test",
        }

        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        delete_response = http_client.delete(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)

        assert delete_response.status_code == 204

    @pytest.mark.skip(reason="DELETE endpoint not implemented yet")
    def test_get_deleted_job_returns_404(self, http_client: httpx.Client, auth_headers_with_ids: dict):
        """Test getting deleted job returns 404."""
        payload = {
            "client_id": "uat-lifecycle-client",
            "client_name": "UAT Lifecycle Test",
        }

        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        delete_response = http_client.delete(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)
        assert delete_response.status_code == 204

        get_response = http_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)
        assert get_response.status_code == 404

    def test_delete_nonexistent_job_returns_404(
        self, http_client: httpx.Client, auth_headers: dict
    ):
        """Test deleting nonexistent job returns 404."""
        nonexistent_id = str(uuid.uuid4())

        response = http_client.delete(f"/api/v1/jobs/{nonexistent_id}", headers=auth_headers)

        assert response.status_code == 404

    def test_create_job_without_auth_returns_401(self, http_client: httpx.Client):
        """Test job creation without authentication returns 401."""
        payload = {
            "client_id": "uat-lifecycle-client",
            "client_name": "UAT Lifecycle Test",
        }

        response = http_client.post("/api/v1/jobs", json=payload)

        assert response.status_code == 401

    def test_create_job_with_invalid_token_returns_401(self, http_client: httpx.Client):
        """Test job creation with invalid token returns 401."""
        headers = {
            "Authorization": "Bearer invalid-token",
            "Content-Type": "application/json",
        }
        payload = {
            "client_id": "uat-lifecycle-client",
            "client_name": "UAT Lifecycle Test",
        }

        response = http_client.post("/api/v1/jobs", json=payload, headers=headers)

        assert response.status_code == 401

    def test_create_job_with_missing_required_fields_returns_422(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test job creation with missing required fields returns 422."""
        payload = {
            "client_name": "UAT Lifecycle Test",
        }

        response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)

        assert response.status_code == 422

    def test_job_id_is_valid_uuid_v4(self, http_client: httpx.Client, auth_headers_with_ids: dict):
        """Test created job ID is valid UUID v4 format."""
        payload = {
            "client_id": "uat-lifecycle-client",
            "client_name": "UAT Lifecycle Test",
        }

        response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)

        assert response.status_code == 201
        job_id = response.json()["job_id"]

        try:
            parsed_uuid = uuid.UUID(job_id)
            assert parsed_uuid.version == 4
        except (ValueError, AttributeError):
            pytest.fail(f"Job ID is not a valid UUID v4: {job_id}")
