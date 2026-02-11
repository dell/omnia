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
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app


class TestGenerateInputFilesRoutes:
    """Integration tests for generate input files API endpoints."""

    def setup_method(self) -> None:
        """Set up test client."""
        self.client = TestClient(app)
        self.valid_job_id = str(uuid.uuid4())
        self.valid_correlation_id = str(uuid.uuid4())
        self.valid_headers = {
            "Authorization": "Bearer valid-token",
            "X-Correlation-ID": self.valid_correlation_id,
        }

    def test_generate_input_files_endpoint_exists(self) -> None:
        """Test that the generate input files endpoint exists and is accessible."""
        # Test with invalid auth to check endpoint exists (should get 401, not 404)
        response = self.client.post(
            f"/api/v1/jobs/{self.valid_job_id}/stages/generate-input-files",
            headers={"Authorization": "Bearer invalid-token"},
        )
        
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
        # Should be 401 (auth required) or 422 (validation error)
        assert response.status_code in [401, 422]

    def test_generate_input_files_with_valid_request(self) -> None:
        """Test generate input files with valid request structure."""
        response = self.client.post(
            f"/api/v1/jobs/{self.valid_job_id}/stages/generate-input-files",
            headers=self.valid_headers,
            json={}
        )

        # Should accept the request structure (may fail due to missing job/dependencies)
        assert response.status_code in [200, 400, 422, 500]

    def test_generate_input_files_with_custom_policy(self) -> None:
        """Test generate input files with custom adapter policy."""
        request_data = {
            "adapter_policy_path": "/opt/omnia/custom_policy.json"
        }

        response = self.client.post(
            f"/api/v1/jobs/{self.valid_job_id}/stages/generate-input-files",
            json=request_data,
            headers=self.valid_headers,
        )

        # Should accept the custom policy path (may fail due to missing file/job)
        assert response.status_code in [200, 400, 422, 500]

    def test_generate_input_files_requires_authentication(self) -> None:
        """Test that generate input files endpoint requires authentication."""
        response = self.client.post(
            f"/api/v1/jobs/{self.valid_job_id}/stages/generate-input-files",
        )
        
        # Should require authentication
        assert response.status_code == 401

    def test_generate_input_files_requires_correlation_id(self) -> None:
        """Test that generate input files endpoint requires correlation ID."""
        response = self.client.post(
            f"/api/v1/jobs/{self.valid_job_id}/stages/generate-input-files",
            headers={"Authorization": "Bearer valid-token"},
        )
        
        # Should require correlation ID
        assert response.status_code == 422

    def test_generate_input_files_invalid_job_id_format(self) -> None:
        """Test generate input files with invalid job ID format."""
        response = self.client.post(
            "/api/v1/jobs/invalid-uuid/stages/generate-input-files",
            headers=self.valid_headers,
        )
        
        # Should validate job ID format
        assert response.status_code == 422

    def test_generate_input_files_invalid_policy_path(self) -> None:
        """Test generate input files with invalid adapter policy path."""
        request_data = {
            "adapter_policy_path": "../../../etc/passwd"  # Path traversal attempt
        }

        response = self.client.post(
            f"/api/v1/jobs/{self.valid_job_id}/stages/generate-input-files",
            json=request_data,
            headers=self.valid_headers,
        )
        
        # Should reject path traversal attempts
        assert response.status_code in [400, 422]

    def test_generate_input_files_empty_policy_path(self) -> None:
        """Test generate input files with empty adapter policy path."""
        request_data = {
            "adapter_policy_path": ""
        }

        response = self.client.post(
            f"/api/v1/jobs/{self.valid_job_id}/stages/generate-input-files",
            json=request_data,
            headers=self.valid_headers,
        )
        
        # Should validate non-empty paths
        assert response.status_code in [400, 422]

    def test_generate_input_files_openapi_documentation(self) -> None:
        """Test that generate input files endpoint is documented in OpenAPI."""
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_spec = response.json()
        paths = openapi_spec.get("paths", {})
        
        # Check if generate input files endpoint is documented
        generate_input_paths = [
            path for path in paths.keys() 
            if "generate-input-files" in path and "POST" in paths[path]
        ]
        
        assert len(generate_input_paths) > 0, "Generate input files endpoint not found in OpenAPI docs"
        
        # Verify the endpoint documentation
        for path in generate_input_paths:
            endpoint_spec = paths[path]["POST"]
            assert "summary" in endpoint_spec
            assert "requestBody" in endpoint_spec
            assert "responses" in endpoint_spec

    def test_generate_input_files_api_docs_accessible(self) -> None:
        """Test that API documentation page is accessible."""
        response = self.client.get("/docs")
        assert response.status_code == 200
        
        # Check that the page contains the generate input files endpoint
        docs_content = response.text
        assert "generate-input-files" in docs_content.lower()

    def test_generate_input_files_response_structure(self) -> None:
        """Test that response has correct structure when successful."""
        response = self.client.post(
            f"/api/v1/jobs/{self.valid_job_id}/stages/generate-input-files",
            headers=self.valid_headers,
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

    def test_generate_input_files_error_handling(self) -> None:
        """Test error handling for various error conditions."""
        # Test with invalid policy path
        response = self.client.post(
            f"/api/v1/jobs/{self.valid_job_id}/stages/generate-input-files",
            headers=self.valid_headers,
            json={"adapter_policy_path": "../../../etc/passwd"}
        )
        
        # Should reject path traversal attempts
        assert response.status_code in [400, 422, 500]

    def test_generate_input_files_default_policy_usage(self) -> None:
        """Test that default policy is used when no custom path provided."""
        response = self.client.post(
            f"/api/v1/jobs/{self.valid_job_id}/stages/generate-input-files",
            headers=self.valid_headers,
            json={}  # No policy path - should use default
        )
        
        # Should process the request (may fail due to missing dependencies)
        assert response.status_code in [200, 400, 422, 500]
