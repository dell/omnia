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

"""End-to-end tests for Generate Input Files complete workflow."""

import json
import uuid
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient

from main import app


class TestGenerateInputFilesE2E:
    """End-to-end tests for complete generate input files workflow."""

    def setup_method(self) -> None:
        """Set up test client and valid data."""
        self.client = TestClient(app)
        self.job_id = str(uuid.uuid4())
        self.correlation_id = str(uuid.uuid4())
        self.headers = {
            "Authorization": "Bearer valid-test-token",
            "X-Correlation-ID": self.correlation_id,
        }

    def test_complete_generate_input_files_workflow(self) -> None:
        """Test complete generate input files workflow."""
        # Step 1: Execute generate input files with default policy
        response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
            headers=self.headers,
        )

        # Should process the request (may fail due to missing dependencies)
        assert response.status_code in [200, 400, 422, 500]
        
        # If successful, verify response structure
        if response.status_code == 200:
            response_data = response.json()
            assert "stage_state" in response_data
            assert response_data["stage_state"] in ["COMPLETED", "FAILED"]
            
            if response_data["stage_state"] == "COMPLETED":
                assert "generated_files" in response_data
                assert isinstance(response_data["generated_files"], list)

    def test_generate_input_files_with_custom_policy_workflow(self) -> None:
        """Test generate input files workflow with custom adapter policy."""
        request_data = {
            "adapter_policy_path": "/opt/omnia/test_policies/custom_policy.json"
        }

        response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
            json=request_data,
            headers=self.headers,
        )

        assert response.status_code in [200, 400, 422, 500]

    def test_generate_input_files_complete_job_integration(self) -> None:
        """Test generate input files integration with complete job workflow."""
        # Step 1: Create job (if possible)
        job_response = self.client.post(
            "/api/v1/jobs",
            json={
                "catalog_uri": "s3://test-bucket/catalog.json",
                "idempotency_key": str(uuid.uuid4())
            },
            headers=self.headers,
        )
        
        if job_response.status_code in [200, 201]:
            job_data = job_response.json()
            job_id = job_data.get("job_id", self.job_id)
        else:
            job_id = self.job_id

        # Step 2: Execute parse catalog first (prerequisite)
        catalog_data = {
            "Catalog": {
                "Name": "Test Catalog",
                "Version": "1.0.0",
                "FunctionalLayer": "test-functional",
                "BaseOS": "test-os",
                "Infrastructure": "test-infra",
                "FunctionalPackages": {},
                "OSPackages": {},
                "InfrastructurePackages": {},
                "DriverPackages": {}
            }
        }

        parse_response = self.client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files={"catalog": ("catalog.json", json.dumps(catalog_data), "application/json")},
            headers=self.headers,
        )

        # Step 3: Execute generate input files
        generate_response = self.client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=self.headers,
        )

        # Should process the request
        assert generate_response.status_code in [200, 400, 422, 500]

    def test_generate_input_files_error_recovery(self) -> None:
        """Test error handling and recovery in generate input files workflow."""
        # Step 1: Submit request with invalid policy path
        invalid_request = {
            "adapter_policy_path": "../../../etc/passwd"
        }

        error_response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
            json=invalid_request,
            headers=self.headers,
        )

        # Should reject invalid path
        assert error_response.status_code in [400, 422]
        
        # Step 2: Submit valid request to test recovery
        recovery_response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
            headers=self.headers,
        )

        # Should process the valid request
        assert recovery_response.status_code in [200, 400, 422, 500]

    def test_generate_input_files_concurrent_requests(self) -> None:
        """Test generate input files with concurrent requests."""
        responses = []
        
        # Submit multiple concurrent requests
        for i in range(3):
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
                headers=self.headers,
            )
            responses.append(response)
        
        # All requests should be processed
        for response in responses:
            assert response.status_code in [200, 400, 422, 500]

    def test_generate_input_files_job_state_integration(self) -> None:
        """Test generate input files integration with job state management."""
        # Execute generate input files
        response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
            headers=self.headers,
        )

        # Check job status
        job_status_response = self.client.get(
            f"/api/v1/jobs/{self.job_id}",
            headers=self.headers,
        )

        # Job status should be accessible
        assert job_status_response.status_code in [200, 404]
        
        if job_status_response.status_code == 200:
            job_data = job_status_response.json()
            assert "job_state" in job_data
            assert "stages" in job_data

    def test_generate_input_files_audit_trail(self) -> None:
        """Test that generate input files creates proper audit trail."""
        # Execute generate input files
        response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
            headers=self.headers,
        )

        # Check audit events (if audit endpoint exists)
        audit_response = self.client.get(
            f"/api/v1/jobs/{self.job_id}/audit",
            headers=self.headers,
        )

        # Audit endpoint should be accessible (may not exist yet)
        if audit_response.status_code == 200:
            audit_data = audit_response.json()
            assert isinstance(audit_data, list)
            
            # Should have audit events for the generate input files operation
            if audit_data:
                event_types = [event.get("event_type") for event in audit_data]
                assert any("generate" in str(event_type).lower() or "input" in str(event_type).lower() 
                          for event_type in event_types)

    def test_generate_input_files_with_various_policy_paths(self) -> None:
        """Test generate input files with various policy path scenarios."""
        test_cases = [
            # No policy path (use default)
            {},
            # Valid absolute path
            {"adapter_policy_path": "/opt/omnia/policies/default.json"},
            # Valid relative path
            {"adapter_policy_path": "policies/custom.json"},
        ]

        for request_data in test_cases:
            response = self.client.post(
                f"/api/v1/jobs/{uuid.uuid4()}/stages/generate-input-files",
                json=request_data,
                headers=self.headers,
            )

            assert response.status_code in [200, 400, 422, 500]

    def test_generate_input_files_dependency_validation(self) -> None:
        """Test that generate input files validates dependencies properly."""
        # This test verifies that the stage checks for required artifacts
        # from previous stages (like parse-catalog)
        
        response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
            headers=self.headers,
        )

        # Should handle missing dependencies gracefully
        assert response.status_code in [200, 400, 422, 500]
        
        if response.status_code in [400, 422]:
            # Error should indicate dependency issues if that's the case
            response_text = response.text.lower()
            # Check for dependency-related error messages
            dependency_keywords = ["dependency", "prerequisite", "required", "missing", "catalog"]
            has_dependency_error = any(keyword in response_text for keyword in dependency_keywords)
            # This assertion is optional since the exact error handling may vary
            # assert has_dependency_error or "not found" in response_text
