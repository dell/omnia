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

"""Integration tests for GET job API endpoint."""

# pylint: disable=too-few-public-methods
# pylint: disable=duplicate-code



class TestGetJobSuccess:
    """Tests for successful job retrieval scenarios."""

    def test_get_existing_job_returns_200(self, client, auth_headers):
        """Get existing job should return 200 OK with job details."""
        create_payload = {"client_id": "client-123", "client_name": "test-client"}
        create_response = client.post("/api/v1/jobs", json=create_payload, headers=auth_headers)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        get_headers = {
            "Authorization": auth_headers["Authorization"],
            "X-Correlation-Id": auth_headers["X-Correlation-Id"],
        }
        get_response = client.get(f"/api/v1/jobs/{job_id}", headers=get_headers)

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["job_id"] == job_id
        assert "job_state" in data
        assert "created_at" in data
        assert "stages" in data

    def test_get_job_returns_all_stages(self, client, auth_headers):
        """Get job should return all associated stages."""
        create_payload = {"client_id": "client-123", "client_name": "test-client"}
        create_response = client.post("/api/v1/jobs", json=create_payload, headers=auth_headers)
        job_id = create_response.json()["job_id"]

        get_headers = {
            "Authorization": auth_headers["Authorization"],
            "X-Correlation-Id": auth_headers["X-Correlation-Id"],
        }
        get_response = client.get(f"/api/v1/jobs/{job_id}", headers=get_headers)

        assert get_response.status_code == 200
        stages = get_response.json()["stages"]
        assert len(stages) == 9

    def test_get_job_returns_correlation_id(self, client, auth_headers, unique_correlation_id):
        """Get job should return correlation ID from headers."""
        create_payload = {"client_id": "client-123", "client_name": "test-client"}
        create_response = client.post("/api/v1/jobs", json=create_payload, headers=auth_headers)
        job_id = create_response.json()["job_id"]

        get_headers = {
            "Authorization": auth_headers["Authorization"],
            "X-Correlation-Id": unique_correlation_id,
        }
        get_response = client.get(f"/api/v1/jobs/{job_id}", headers=get_headers)

        assert get_response.status_code == 200
        assert get_response.json()["correlation_id"] == unique_correlation_id


class TestGetJobNotFound:
    """Tests for job retrieval when job doesn't exist."""

    def test_get_nonexistent_job_returns_404(self, client, auth_headers):
        """Get nonexistent job should return 404 Not Found."""
        nonexistent_job_id = "019bf590-1234-7890-abcd-ef1234567890"

        get_headers = {
            "Authorization": auth_headers["Authorization"],
            "X-Correlation-Id": auth_headers["X-Correlation-Id"],
        }
        response = client.get(f"/api/v1/jobs/{nonexistent_job_id}", headers=get_headers)

        assert response.status_code == 404

    def test_get_job_invalid_uuid_format_returns_400(self, client, auth_headers):
        """Get job with invalid UUID format should return 400 Bad Request."""
        invalid_job_id = "not-a-valid-uuid"

        get_headers = {
            "Authorization": auth_headers["Authorization"],
            "X-Correlation-Id": auth_headers["X-Correlation-Id"],
        }
        response = client.get(f"/api/v1/jobs/{invalid_job_id}", headers=get_headers)

        assert response.status_code == 400


class TestGetJobAuthentication:
    """Tests for authentication in job retrieval."""

    def test_get_job_missing_authorization_returns_422(self, client, unique_correlation_id):
        """Get job without auth header should return 422 Unprocessable Entity."""
        job_id = "019bf590-1234-7890-abcd-ef1234567890"
        headers = {"X-Correlation-Id": unique_correlation_id}

        response = client.get(f"/api/v1/jobs/{job_id}", headers=headers)

        assert response.status_code == 422

    def test_get_job_invalid_authorization_format_returns_401(self, client, unique_correlation_id):
        """Get job with invalid auth format should return 401 Unauthorized."""
        job_id = "019bf590-1234-7890-abcd-ef1234567890"
        headers = {
            "Authorization": "InvalidFormat test-token",
            "X-Correlation-Id": unique_correlation_id,
        }

        response = client.get(f"/api/v1/jobs/{job_id}", headers=headers)

        assert response.status_code == 401


class TestGetJobClientIsolation:
    """Tests for client isolation in job retrieval."""

    def test_different_client_cannot_access_job(
        self, client, unique_idempotency_key, unique_correlation_id
    ):
        """Different client should not be able to access another client's job."""
        create_headers = {
            "Authorization": "Bearer client-a",
            "X-Correlation-Id": unique_correlation_id,
            "Idempotency-Key": unique_idempotency_key,
        }
        create_payload = {"client_id": "client-123", "client_name": "test-client"}
        create_response = client.post("/api/v1/jobs", json=create_payload, headers=create_headers)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        get_headers = {
            "Authorization": "Bearer client-b",
            "X-Correlation-Id": unique_correlation_id,
        }
        get_response = client.get(f"/api/v1/jobs/{job_id}", headers=get_headers)

        assert get_response.status_code in [403, 404]


class TestGetJobStateMapping:
    """Tests for state mapping and timestamps in job retrieval."""

    def test_get_job_returns_mapped_state_names(self, client, auth_headers):
        """Get job should return API state names (PENDING, RUNNING, SUCCEEDED, FAILED, CLEANED)."""
        create_payload = {"client_id": "client-123", "client_name": "test-client"}
        create_response = client.post("/api/v1/jobs", json=create_payload, headers=auth_headers)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        get_headers = {
            "Authorization": auth_headers["Authorization"],
            "X-Correlation-Id": auth_headers["X-Correlation-Id"],
        }
        get_response = client.get(f"/api/v1/jobs/{job_id}", headers=get_headers)

        assert get_response.status_code == 200
        data = get_response.json()
        
        # Verify state is one of the expected API states
        valid_states = ["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "CLEANED"]
        assert data["job_state"] in valid_states

    def test_get_job_returns_state_timestamps(self, client, auth_headers):
        """Get job should return timestamps for state changes."""
        create_payload = {"client_id": "client-123", "client_name": "test-client"}
        create_response = client.post("/api/v1/jobs", json=create_payload, headers=auth_headers)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        get_headers = {
            "Authorization": auth_headers["Authorization"],
            "X-Correlation-Id": auth_headers["X-Correlation-Id"],
        }
        get_response = client.get(f"/api/v1/jobs/{job_id}", headers=get_headers)

        assert get_response.status_code == 200
        data = get_response.json()
        
        # Should include state_timestamps field
        assert "state_timestamps" in data
        
        if data["state_timestamps"]:
            # Should include CREATED timestamp at minimum
            assert "CREATED" in data["state_timestamps"]
            # Verify timestamp format (ISO 8601 with Z suffix)
            assert data["state_timestamps"]["CREATED"].endswith("Z")

    def test_get_job_returns_step_breakdown(self, client, auth_headers):
        """Get job should return detailed step breakdown."""
        create_payload = {"client_id": "client-123", "client_name": "test-client"}
        create_response = client.post("/api/v1/jobs", json=create_payload, headers=auth_headers)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        get_headers = {
            "Authorization": auth_headers["Authorization"],
            "X-Correlation-Id": auth_headers["X-Correlation-Id"],
        }
        get_response = client.get(f"/api/v1/jobs/{job_id}", headers=get_headers)

        assert get_response.status_code == 200
        data = get_response.json()
        
        # Verify stages structure
        assert "stages" in data
        assert isinstance(data["stages"], list)
        
        # Check stage structure
        for stage in data["stages"]:
            assert "stage_name" in stage
            assert "stage_state" in stage
            assert "started_at" in stage
            assert "ended_at" in stage
            assert "error_code" in stage
            assert "error_summary" in stage
