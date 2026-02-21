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

"""Integration tests for Jobs create API."""
# pylint: disable=missing-function-docstring

import uuid

class TestCreateJobSuccess:
    """Happy-path create job tests."""

    def test_create_job_returns_201_with_valid_request(self, client, auth_headers):
        payload = {
            "client_id": "client-123",
            "client_name": "test-client",
            "metadata": {"description": "Test job creation"},
        }

        response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)

        assert response.status_code == 201
        data = response.json()
        assert "job_id" in data
        assert "correlation_id" in data
        assert "job_state" in data
        assert "created_at" in data
        assert "stages" in data

    def test_create_job_returns_valid_uuid(self, client, auth_headers):
        payload = {"client_id": "client-123", "client_name": "test-client"}

        response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)

        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Validate via uuid library to allow any standard UUID version
        parsed = uuid.UUID(job_id)
        assert str(parsed) == job_id.lower()

    def test_create_job_returns_created_state(self, client, auth_headers):
        payload = {"client_id": "client-123", "client_name": "test-client"}

        response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)

        assert response.status_code == 201
        assert response.json()["job_state"] == "CREATED"

    def test_create_job_creates_all_nine_stages(self, client, auth_headers):
        payload = {"client_id": "client-123", "client_name": "test-client"}

        response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)

        assert response.status_code == 201
        stages = response.json()["stages"]
        assert len(stages) == 9

        expected_stages = [
            "parse-catalog",
            "generate-input-files",
            "create-local-repository",
            "update-local-repository",
            "create-image-repository",
            "build-image",
            "validate-image",
            "validate-image-on-test",
            "promote"
        ]

        stage_names = [s["stage_name"] for s in stages]
        assert stage_names == expected_stages

    def test_create_job_all_stages_pending(self, client, auth_headers):
        payload = {"client_id": "client-123", "client_name": "test-client"}

        response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)

        assert response.status_code == 201
        stages = response.json()["stages"]

        for stage in stages:
            assert stage["stage_state"] == "PENDING"
            assert stage["started_at"] is None
            assert stage["ended_at"] is None
            assert stage["error_code"] is None
            assert stage["error_summary"] is None

    def test_create_job_returns_correlation_id(
        self, client, unique_correlation_id, unique_idempotency_key
    ):
        headers = {
            "Authorization": "Bearer test-client-123",
            "X-Correlation-Id": unique_correlation_id,
            "Idempotency-Key": unique_idempotency_key,
        }
        payload = {"client_id": "client-123", "client_name": "test-client"}

        response = client.post("/api/v1/jobs", json=payload, headers=headers)

        assert response.status_code == 201
        assert response.json()["correlation_id"] == unique_correlation_id


class TestCreateJobIdempotency:
    """Idempotency behavior tests for create job."""

    def test_idempotent_request_returns_200_with_same_job(
        self, client, unique_idempotency_key, unique_correlation_id
    ):
        headers = {
            "Authorization": "Bearer test-client-123",
            "X-Correlation-Id": unique_correlation_id,
            "Idempotency-Key": unique_idempotency_key,
        }
        payload = {"client_id": "client-123", "client_name": "test-client"}

        response1 = client.post("/api/v1/jobs", json=payload, headers=headers)
        assert response1.status_code == 201
        job_id_1 = response1.json()["job_id"]

        response2 = client.post("/api/v1/jobs", json=payload, headers=headers)
        assert response2.status_code == 200
        job_id_2 = response2.json()["job_id"]

        assert job_id_1 == job_id_2

    def test_idempotency_with_different_correlation_id(
        self, client, unique_idempotency_key
    ):
        payload = {"client_id": "client-123", "client_name": "test-client"}

        headers1 = {
            "Authorization": "Bearer test-client-123",
            "X-Correlation-Id": "019bf590-1111-7890-abcd-ef1234567890",
            "Idempotency-Key": unique_idempotency_key,
        }
        response1 = client.post("/api/v1/jobs", json=payload, headers=headers1)
        assert response1.status_code == 201
        job_id_1 = response1.json()["job_id"]

        headers2 = {
            "Authorization": "Bearer test-client-123",
            "X-Correlation-Id": "019bf590-2222-7890-abcd-ef1234567890",
            "Idempotency-Key": unique_idempotency_key,
        }
        response2 = client.post("/api/v1/jobs", json=payload, headers=headers2)
        assert response2.status_code == 200
        job_id_2 = response2.json()["job_id"]

        assert job_id_1 == job_id_2

    # def test_idempotency_conflict_different_payload(
    #     self, client, unique_idempotency_key, unique_correlation_id
    # ):
    #     headers = {
    #         "Authorization": "Bearer test-client-123",
    #         "X-Correlation-Id": unique_correlation_id,
    #         "Idempotency-Key": unique_idempotency_key,
    #     }
    #
    #     payload1 = {"client_name": "client-one"}
    #     response1 = client.post("/api/v1/jobs", json=payload1, headers=headers)
    #     assert response1.status_code == 201
    #
    #     payload2 = {"client_name": "client-two"}
    #     response2 = client.post("/api/v1/jobs", json=payload2, headers=headers)
    #     assert response2.status_code == 409
    #
    #     error_detail = response2.json()["detail"]
    #     assert "IDEMPOTENCY_CONFLICT" in error_detail["error"]


class TestCreateJobValidation:
    """Validation scenarios for create job."""

    def test_missing_client_id_returns_422(self, client, auth_headers):
        """Missing client_id is required and should fail validation."""
        payload = {"client_name": "test-client"}

        response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)

        assert response.status_code == 422

    def test_missing_client_name_is_allowed(self, client, auth_headers):
        """Missing client_name is allowed (field is optional)."""
        payload = {"client_id": "client-123"}

        response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)

        assert response.status_code in [200, 201]

    def test_empty_client_id_returns_422(self, client, auth_headers):
        """Empty client_id should be rejected."""
        payload = {"client_id": ""}

        response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)

        assert response.status_code in [400, 422]

    def test_empty_client_name_returns_400(self, client, auth_headers):
        """Empty client_name should be rejected."""
        payload = {"client_id": "client-123", "client_name": ""}

        response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)

        assert response.status_code in [400, 422]

    def test_client_id_whitespace_only_returns_422(self, client, auth_headers):
        """Whitespace-only client_id should be rejected."""
        payload = {"client_id": "   "}

        response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)

        assert response.status_code in [400, 422]

    def test_client_name_whitespace_only_returns_400(self, client, auth_headers):
        """Whitespace-only client_name should be rejected."""
        payload = {"client_id": "client-123", "client_name": "   "}

        response = client.post("/api/v1/jobs", json=payload, headers=auth_headers)

        assert response.status_code in [400, 422]


class TestCreateJobAuthentication:
    """Authentication header tests."""

    def test_missing_authorization_header_returns_422(self, client, unique_idempotency_key):
        """Auth header required."""
        headers = {
            "X-Correlation-Id": "019bf590-1234-7890-abcd-ef1234567890",
            "Idempotency-Key": unique_idempotency_key,
        }
        payload = {"client_id": "client-123", "client_name": "test-client"}

        response = client.post("/api/v1/jobs", json=payload, headers=headers)

        assert response.status_code == 422

    def test_invalid_authorization_format_returns_401(
        self, client, unique_idempotency_key
    ):
        """Invalid auth scheme returns 401."""
        headers = {
            "Authorization": "InvalidFormat test-token",
            "X-Correlation-Id": "019bf590-1234-7890-abcd-ef1234567890",
            "Idempotency-Key": unique_idempotency_key,
        }
        payload = {"client_id": "client-123", "client_name": "test-client"}

        response = client.post("/api/v1/jobs", json=payload, headers=headers)

        assert response.status_code == 401

    def test_empty_bearer_token_returns_401(self, client, unique_idempotency_key):
        """Empty bearer token returns 401."""
        headers = {
            "Authorization": "Bearer ",
            "X-Correlation-Id": "019bf590-1234-7890-abcd-ef1234567890",
            "Idempotency-Key": unique_idempotency_key,
        }
        payload = {"client_id": "client-123", "client_name": "test-client"}

        response = client.post("/api/v1/jobs", json=payload, headers=headers)

        assert response.status_code == 401


class TestCreateJobHeaders:
    """Header handling tests."""

    def test_missing_idempotency_key_returns_422(self, client):
        """Idempotency key is required."""
        headers = {
            "Authorization": "Bearer test-client-123",
            "X-Correlation-Id": "019bf590-1234-7890-abcd-ef1234567890",
        }
        payload = {"client_id": "client-123", "client_name": "test-client"}

        response = client.post("/api/v1/jobs", json=payload, headers=headers)

        assert response.status_code == 422

    def test_auto_generates_correlation_id_if_missing(
        self, client, unique_idempotency_key
    ):
        """Server should generate correlation ID when absent."""
        headers = {
            "Authorization": "Bearer test-client-123",
            "Idempotency-Key": unique_idempotency_key,
        }
        payload = {"client_id": "client-123", "client_name": "test-client"}

        response = client.post("/api/v1/jobs", json=payload, headers=headers)

        assert response.status_code == 201
        assert "correlation_id" in response.json()
        correlation_id = response.json()["correlation_id"]
        assert len(correlation_id) == 36
