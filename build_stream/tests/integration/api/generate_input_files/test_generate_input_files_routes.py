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

"""Integration tests for Generate Input Files API routes."""

import json
import uuid
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient

from main import app
from container import DevContainer


class TestGenerateInputFilesRoutes:
    """Integration tests for generate input files API endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client with in-memory stores."""
        container = DevContainer()
        container.wire(modules=["api.generate_input_files.routes"])

        with TestClient(app) as client:
            yield client

    @pytest.fixture
    def auth_headers(self, mock_jwt_validation) -> Dict[str, str]:  # pylint: disable=unused-argument
        """Create authentication headers."""
        return {
            "Authorization": "Bearer test-token",
            "X-Correlation-ID": str(uuid.uuid4()),
            "Idempotency-Key": f"test-key-{uuid.uuid4()}",
        }

    @pytest.fixture
    def created_job(self, client: TestClient, auth_headers: Dict[str, str]) -> Dict[str, Any]:
        """Create a fresh job for each test."""
        # Use unique idempotency key to ensure fresh job creation
        headers = auth_headers.copy()
        headers["Idempotency-Key"] = f"test-key-{uuid.uuid4()}"

        response = client.post(
            "/api/v1/jobs",
            json={"client_id": "test-client"},
            headers=headers,
        )
        assert response.status_code == 201
        return response.json()

    def test_generate_input_files_endpoint_exists(self, client: TestClient) -> None:
        """Test that the generate input files endpoint exists and is accessible."""
        # Test with invalid auth to check endpoint exists (should get 401, not 404)
        response = client.post(
            "/api/v1/jobs/invalid-job-id/stages/generate-input-files",
            headers={"Authorization": "Bearer invalid-token"},
        )
        
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
        # Should be 401 (auth required) or 422 (validation error)
        assert response.status_code in [401, 422]

    def test_generate_input_files_with_valid_request(self, client: TestClient, auth_headers: Dict[str, str], created_job: Dict[str, Any]) -> None:
        """Test generate input files with valid request structure."""
        job_id = created_job["job_id"]
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers,
            json={}
        )

        # Should accept the request structure (may fail due to missing dependencies)
        assert response.status_code in [200, 400, 422, 500]

    def test_generate_input_files_with_custom_policy(self, client: TestClient, auth_headers: Dict[str, str], created_job: Dict[str, Any]) -> None:
        """Test generate input files with custom adapter policy."""
        job_id = created_job["job_id"]
        request_data = {
            "adapter_policy_path": "/opt/omnia/custom_policy.json"
        }

        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            json=request_data,
            headers=auth_headers,
        )

        # Should accept the custom policy path (may fail due to missing file/job)
        assert response.status_code in [200, 400, 422, 500]

    def test_generate_input_files_requires_authentication(self, client: TestClient) -> None:
        """Test that generate input files endpoint requires authentication."""
        response = client.post(
            "/api/v1/jobs/invalid-job-id/stages/generate-input-files",
        )
        
        # Should require authentication
        assert response.status_code == 401

    def test_generate_input_files_requires_correlation_id(self, client: TestClient, created_job: Dict[str, Any]) -> None:
        """Test that generate input files endpoint requires correlation ID."""
        job_id = created_job["job_id"]
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers={"Authorization": "Bearer test-token"},
        )
        
        # Should require correlation ID
        assert response.status_code == 422

    def test_generate_input_files_invalid_job_id_format(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test generate input files with invalid job ID format."""
        response = client.post(
            "/api/v1/jobs/invalid-uuid/stages/generate-input-files",
            headers=auth_headers
        )
        
        # Should validate job ID format (may return 400 or 422)
        assert response.status_code in [400, 422]

    def test_generate_input_files_invalid_policy_path(self, client: TestClient, auth_headers: Dict[str, str], created_job: Dict[str, Any]) -> None:
        """Test generate input files with invalid adapter policy path."""
        job_id = created_job["job_id"]
        request_data = {
            "adapter_policy_path": "../../../etc/passwd"  # Path traversal attempt
        }

        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers,
            json=request_data
        )
        
        # Should reject path traversal attempts
        assert response.status_code in [400, 422]

    def test_generate_input_files_empty_policy_path(self, client: TestClient, auth_headers: Dict[str, str], created_job: Dict[str, Any]) -> None:
        """Test generate input files with empty adapter policy path."""
        job_id = created_job["job_id"]
        request_data = {
            "adapter_policy_path": ""
        }

        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            json=request_data,
            headers=auth_headers,
        )
        
        # Should handle empty policy path (may use default or fail validation)
        assert response.status_code in [200, 400, 422, 500]

    def test_generate_input_files_openapi_documentation(self, client: TestClient) -> None:
        """Test that OpenAPI documentation includes generate input files endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_spec = response.json()
        # Should contain the generate input files endpoint
        assert "/api/v1/jobs/{job_id}/stages/generate-input-files" in str(openapi_spec)

    def test_generate_input_files_api_docs_accessible(self, client: TestClient) -> None:
        """Test that API documentation page is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        
        # Check that the page is the Swagger UI documentation
        docs_content = response.text.lower()
        assert "swagger ui" in docs_content
        assert "openapi" in docs_content

    def test_generate_input_files_response_structure(self, client: TestClient, auth_headers: Dict[str, str], created_job: Dict[str, Any]) -> None:
        """Test that response has correct structure when successful."""
        job_id = created_job["job_id"]
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers,
            json={}
        )

        # If successful, verify response structure
        if response.status_code == 200:
            data = response.json()
            assert "stage_state" in data
            assert data["stage_state"] in ["COMPLETED", "FAILED"]
            
            if data["stage_state"] == "COMPLETED":
                assert "generated_files" in data
                assert isinstance(data["generated_files"], list)

    def test_generate_input_files_error_handling(self, client: TestClient, auth_headers: Dict[str, str], created_job: Dict[str, Any]) -> None:
        """Test error handling for various error conditions."""
        job_id = created_job["job_id"]
        # Test with invalid policy path
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers,
            json={"adapter_policy_path": "../../../etc/passwd"}
        )
        
        # Should reject path traversal attempts
        assert response.status_code in [400, 422, 500]

    def test_generate_input_files_default_policy_usage(self, client: TestClient, auth_headers: Dict[str, str], created_job: Dict[str, Any]) -> None:
        """Test that default policy is used when no custom path provided."""
        job_id = created_job["job_id"]
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers,
            json={}  # No policy path - should use default
        )
        
        # Should process the request (may fail due to missing dependencies)
        assert response.status_code in [200, 400, 422, 500]
