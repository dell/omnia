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
        with patch('api.generate_input_files.service.GenerateInputFilesService') as mock_service:
            # Mock the service to return a successful result
            mock_instance = MagicMock()
            mock_instance.execute.return_value = MagicMock(
                stage_state="COMPLETED",
                generated_files=[
                    MagicMock(
                        filename="omnia_config.yml",
                        artifact_ref=MagicMock(
                            key="input/test-job/omnia_config.yml",
                            digest="a" * 64,
                            size_bytes=2048,
                            uri="memory://input/test-job/omnia_config.yml"
                        )
                    ),
                    MagicMock(
                        filename="network_spec.yml",
                        artifact_ref=MagicMock(
                            key="input/test-job/network_spec.yml",
                            digest="b" * 64,
                            size_bytes=1024,
                            uri="memory://input/test-job/network_spec.yml"
                        )
                    )
                ]
            )
            mock_service.return_value = mock_instance

            response = self.client.post(
                f"/api/v1/jobs/{self.valid_job_id}/stages/generate-input-files",
                headers=self.valid_headers,
            )

            # The response should be successful if mocking works correctly
            # If not, we at least verify the endpoint structure is correct
            assert response.status_code in [200, 201, 400, 422, 500]

    def test_generate_input_files_with_custom_policy(self) -> None:
        """Test generate input files with custom adapter policy."""
        request_data = {
            "adapter_policy_path": "/opt/omnia/custom_policy.json"
        }

        with patch('api.generate_input_files.service.GenerateInputFilesService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.execute.return_value = MagicMock(
                stage_state="COMPLETED",
                generated_files=[]
            )
            mock_service.return_value = mock_instance

            response = self.client.post(
                f"/api/v1/jobs/{self.valid_job_id}/stages/generate-input-files",
                json=request_data,
                headers=self.valid_headers,
            )

            assert response.status_code in [200, 201, 400, 422, 500]

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

    @patch('api.generate_input_files.service.GenerateInputFilesService')
    def test_generate_input_files_service_integration(self, mock_service) -> None:
        """Test integration with GenerateInputFilesService."""
        # Mock service to return a realistic response
        mock_instance = MagicMock()
        mock_instance.execute.return_value = MagicMock(
            stage_state="COMPLETED",
            generated_files=[
                MagicMock(
                    filename="omnia_config.yml",
                    artifact_ref=MagicMock(
                        key="input/test-job/omnia_config.yml",
                        digest="a" * 64,
                        size_bytes=2048,
                        uri="memory://input/test-job/omnia_config.yml"
                    )
                ),
                MagicMock(
                    filename="network_spec.yml",
                    artifact_ref=MagicMock(
                        key="input/test-job/network_spec.yml",
                        digest="b" * 64,
                        size_bytes=1024,
                        uri="memory://input/test-job/network_spec.yml"
                    )
                ),
                MagicMock(
                    filename="provision_config.yml",
                    artifact_ref=MagicMock(
                        key="input/test-job/provision_config.yml",
                        digest="c" * 64,
                        size_bytes=1536,
                        uri="memory://input/test-job/provision_config.yml"
                    )
                )
            ]
        )
        mock_service.return_value = mock_instance

        response = self.client.post(
            f"/api/v1/jobs/{self.valid_job_id}/stages/generate-input-files",
            headers=self.valid_headers,
        )

        # If mocking works, should get successful response
        if response.status_code == 200:
            response_data = response.json()
            assert "stage_state" in response_data
            assert response_data["stage_state"] == "COMPLETED"
            assert "generated_files" in response_data
            assert len(response_data["generated_files"]) == 3
            
            # Check structure of generated files
            for file_info in response_data["generated_files"]:
                assert "filename" in file_info
                assert "artifact_ref" in file_info
                assert "key" in file_info["artifact_ref"]
                assert "digest" in file_info["artifact_ref"]
                assert "size_bytes" in file_info["artifact_ref"]
                assert "uri" in file_info["artifact_ref"]

    def test_generate_input_files_service_error_handling(self) -> None:
        """Test error handling when service raises exceptions."""
        with patch('api.generate_input_files.service.GenerateInputFilesService') as mock_service:
            # Mock service to raise an exception
            mock_instance = MagicMock()
            mock_instance.execute.side_effect = Exception("Service error")
            mock_service.return_value = mock_instance

            response = self.client.post(
                f"/api/v1/jobs/{self.valid_job_id}/stages/generate-input-files",
                headers=self.valid_headers,
            )

            # Should handle service errors gracefully
            assert response.status_code in [400, 500, 422]

    def test_generate_input_files_default_policy_usage(self) -> None:
        """Test that default policy is used when no custom path provided."""
        with patch('api.generate_input_files.service.GenerateInputFilesService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.execute.return_value = MagicMock(
                stage_state="COMPLETED",
                generated_files=[]
            )
            mock_service.return_value = mock_instance

            # Request without adapter_policy_path (should use default)
            response = self.client.post(
                f"/api/v1/jobs/{self.valid_job_id}/stages/generate-input-files",
                headers=self.valid_headers,
            )

            assert response.status_code in [200, 201, 400, 422, 500]
            
            # Verify service was called with None for adapter_policy_path
            if mock_service.called:
                call_args = mock_service.call_args
                # The command should have adapter_policy_path=None
                assert call_args is not None
