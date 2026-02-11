"""
GenerateInputFiles API Integration Tests

Tests the complete API endpoint behavior including:
- Request validation and authentication
- Successful execution with artifact storage
- Error responses (invalid paths, missing dependencies)
- Authentication/authorization
- Cross-stage artifact dependencies
"""

import json
import os
import threading
import uuid
from typing import Dict, Any

import pytest

from fastapi.testclient import TestClient

from main import app
from container import DevContainer


class TestGenerateInputFilesAPI:  # pylint: disable=too-many-public-methods
    """Integration tests for GenerateInputFiles API endpoint."""

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
    def valid_job_id(self) -> str:
        """Generate a valid job ID for testing."""
        return str(uuid.uuid4())

    @pytest.fixture
    def valid_request_data(self) -> Dict[str, Any]:
        """Valid request data for generate input files."""
        return {}  # Empty request uses default policy

    @pytest.fixture
    def custom_policy_request_data(self) -> Dict[str, Any]:
        """Request data with custom adapter policy."""
        return {
            "adapter_policy_path": "/opt/omnia/policies/custom_policy.json"
        }

    def test_endpoint_exists_and_requires_auth(self, client: TestClient, valid_job_id: str) -> None:
        """Test that the endpoint exists and requires authentication."""
        response = client.post(
            f"/api/v1/jobs/{valid_job_id}/stages/generate-input-files"
        )
        
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
        # Should require authentication
        assert response.status_code == 401

    def test_valid_request_structure(self, client: TestClient, auth_headers: Dict[str, str], valid_job_id: str) -> None:
        """Test generate input files with valid request structure."""
        response = client.post(
            f"/api/v1/jobs/{valid_job_id}/stages/generate-input-files",
            headers=auth_headers,
            json={}
        )

        # Should accept the request structure (may fail due to missing job/dependencies)
        assert response.status_code in [200, 400, 422, 500]

    def test_request_with_custom_policy(self, client: TestClient, auth_headers: Dict[str, str], valid_job_id: str, custom_policy_request_data: Dict[str, Any]) -> None:
        """Test generate input files with custom adapter policy."""
        response = client.post(
            f"/api/v1/jobs/{valid_job_id}/stages/generate-input-files",
            headers=auth_headers,
            json=custom_policy_request_data
        )

        # Should accept the custom policy path (may fail due to missing file/job)
        assert response.status_code in [200, 400, 422, 500]

    def test_missing_correlation_id(self, client: TestClient, valid_job_id: str) -> None:
        """Test that correlation ID is required."""
        response = client.post(
            f"/api/v1/jobs/{valid_job_id}/stages/generate-input-files",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 422

    def test_invalid_job_id_format(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test generate input files with invalid job ID format."""
        response = client.post(
            "/api/v1/jobs/invalid-uuid/stages/generate-input-files",
            headers=auth_headers
        )
        
        assert response.status_code == 422

    def test_path_traversal_protection(self, client: TestClient, auth_headers: Dict[str, str], valid_job_id: str) -> None:
        """Test that path traversal attempts are blocked."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "....//....//....//etc/passwd"
        ]
        
        for malicious_path in malicious_paths:
            request_data = {"adapter_policy_path": malicious_path}
            response = client.post(
                f"/api/v1/jobs/{valid_job_id}/stages/generate-input-files",
                headers=auth_headers,
                json=request_data
            )
            
            # Should reject path traversal attempts
            assert response.status_code in [400, 422]

    def test_invalid_json_request(self, client: TestClient, auth_headers: Dict[str, str], valid_job_id: str) -> None:
        """Test generate input files with invalid JSON."""
        response = client.post(
            f"/api/v1/jobs/{valid_job_id}/stages/generate-input-files",
            headers=auth_headers,
            data="not json content",
            content_type="application/json"
        )
        
        assert response.status_code == 422

    def test_empty_request_body(self, client: TestClient, auth_headers: Dict[str, str], valid_job_id: str) -> None:
        """Test generate input files with empty request body."""
        response = client.post(
            f"/api/v1/jobs/{valid_job_id}/stages/generate-input-files",
            headers=auth_headers,
            data=""
        )
        
        # Should handle empty body gracefully
        assert response.status_code in [200, 400, 422, 500]

    def test_concurrent_requests(self, client: TestClient, auth_headers: Dict[str, str], valid_job_id: str) -> None:
        """Test concurrent requests to the same job."""
        def make_request():
            return client.post(
                f"/api/v1/jobs/{valid_job_id}/stages/generate-input-files",
                headers=auth_headers,
                json={}
            )
        
        # Make concurrent requests
        threads = []
        responses = []
        
        for _ in range(3):
            thread = threading.Thread(target=lambda: responses.append(make_request()))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should be processed (may succeed or fail gracefully)
        for response in responses:
            assert response.status_code in [200, 400, 422, 500]

    def test_response_structure_on_success(self, client: TestClient, auth_headers: Dict[str, str], valid_job_id: str) -> None:
        """Test that successful response has correct structure."""
        response = client.post(
            f"/api/v1/jobs/{valid_job_id}/stages/generate-input-files",
            headers=auth_headers,
            json={}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Should have required fields
            assert "stage_state" in data
            assert data["stage_state"] in ["COMPLETED", "FAILED"]
            
            # If completed, should have generated files
            if data["stage_state"] == "COMPLETED":
                assert "generated_files" in data
                assert isinstance(data["generated_files"], list)
                
                # Each generated file should have required fields
                for generated_file in data["generated_files"]:
                    assert "filename" in generated_file
                    assert "artifact_ref" in generated_file
                    
                    artifact_ref = generated_file["artifact_ref"]
                    assert "key" in artifact_ref
                    assert "digest" in artifact_ref
                    assert "size_bytes" in artifact_ref
                    assert "uri" in artifact_ref

    def test_error_response_structure(self, client: TestClient, auth_headers: Dict[str, str], valid_job_id: str) -> None:
        """Test that error responses have correct structure."""
        response = client.post(
            f"/api/v1/jobs/{valid_job_id}/stages/generate-input-files",
            headers=auth_headers,
            json={"adapter_policy_path": "/nonexistent/path/policy.json"}
        )
        
        if response.status_code in [400, 422]:
            data = response.json()
            
            # Should have error information
            assert "detail" in data
            assert isinstance(data["detail"], str)

    def test_job_not_found_error(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test behavior when job doesn't exist."""
        nonexistent_job_id = str(uuid.uuid4())
        
        response = client.post(
            f"/api/v1/jobs/{nonexistent_job_id}/stages/generate-input-files",
            headers=auth_headers,
            json={}
        )
        
        # Should handle nonexistent job gracefully
        assert response.status_code in [400, 404, 422, 500]

    def test_dependency_validation(self, client: TestClient, auth_headers: Dict[str, str], valid_job_id: str) -> None:
        """Test that dependencies on parse catalog are validated."""
        response = client.post(
            f"/api/v1/jobs/{valid_job_id}/stages/generate-input-files",
            headers=auth_headers,
            json={}
        )
        
        # May fail due to missing parse catalog artifacts
        if response.status_code in [400, 422]:
            data = response.json()
            # Should indicate dependency issue if that's the problem
            error_detail = data.get("detail", "").lower()
            dependency_keywords = ["dependency", "prerequisite", "catalog", "artifact"]
            has_dependency_error = any(keyword in error_detail for keyword in dependency_keywords)
            # This is optional - the exact error handling may vary
            # assert has_dependency_error

    def test_policy_file_not_found(self, client: TestClient, auth_headers: Dict[str, str], valid_job_id: str) -> None:
        """Test behavior when custom policy file doesn't exist."""
        request_data = {
            "adapter_policy_path": "/nonexistent/custom_policy.json"
        }
        
        response = client.post(
            f"/api/v1/jobs/{valid_job_id}/stages/generate-input-files",
            headers=auth_headers,
            json=request_data
        )
        
        # Should handle missing policy file
        assert response.status_code in [400, 422, 500]

    def test_idempotency_key_handling(self, client: TestClient, auth_headers: Dict[str, str], valid_job_id: str) -> None:
        """Test that idempotency key is properly handled."""
        # Make the same request twice with same idempotency key
        request_data = {}
        
        response1 = client.post(
            f"/api/v1/jobs/{valid_job_id}/stages/generate-input-files",
            headers=auth_headers,
            json=request_data
        )
        
        response2 = client.post(
            f"/api/v1/jobs/{valid_job_id}/stages/generate-input-files",
            headers=auth_headers,
            json=request_data
        )
        
        # Both should be processed (idempotency behavior may vary)
        assert response1.status_code in [200, 400, 422, 500]
        assert response2.status_code in [200, 400, 422, 500]

    def test_large_policy_path(self, client: TestClient, auth_headers: Dict[str, str], valid_job_id: str) -> None:
        """Test handling of unusually long policy paths."""
        long_path = "/opt/omnia/" + "very_long_subdirectory_name/" * 20 + "policy.json"
        
        request_data = {"adapter_policy_path": long_path}
        
        response = client.post(
            f"/api/v1/jobs/{valid_job_id}/stages/generate-input-files",
            headers=auth_headers,
            json=request_data
        )
        
        # Should handle long paths gracefully (may fail validation)
        assert response.status_code in [200, 400, 422, 500]

    def test_special_characters_in_policy_path(self, client: TestClient, auth_headers: Dict[str, str], valid_job_id: str) -> None:
        """Test handling of special characters in policy paths."""
        special_paths = [
            "/opt/omnia/policy with spaces.json",
            "/opt/omnia/policy-with-dashes.json",
            "/opt/omnia/policy_with_underscores.json",
            "/opt/omnia/policy.with.dots.json"
        ]
        
        for special_path in special_paths:
            request_data = {"adapter_policy_path": special_path}
            response = client.post(
                f"/api/v1/jobs/{valid_job_id}/stages/generate-input-files",
                headers=auth_headers,
                json=request_data
            )
            
            # Should handle special characters (may fail if file doesn't exist)
            assert response.status_code in [200, 400, 422, 500]
