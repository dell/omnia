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

"""Integration tests for ValidateImageOnTest API."""

import json
from pathlib import Path
from unittest.mock import patch


class TestValidateImageOnTestSuccess:
    """Happy-path validate image on test tests."""

    def test_returns_202_with_valid_request(
        self, client, auth_headers, job_with_completed_build_image, nfs_queue_dir
    ):
        """Test successful validate image on test request."""
        with patch(
            "infra.repositories.nfs_playbook_queue_request_repository"
            ".NfsPlaybookQueueRequestRepository.is_available",
            return_value=True,
        ), patch(
            "infra.repositories.nfs_playbook_queue_request_repository"
            ".NfsPlaybookQueueRequestRepository.write_request",
            return_value=nfs_queue_dir / "requests" / "test.json",
        ):
            response = client.post(
                f"/api/v1/jobs/{job_with_completed_build_image}/stages/validate-image-on-test",
                headers=auth_headers,
            )

        assert response.status_code == 202
        data = response.json()
        assert data["job_id"] == job_with_completed_build_image
        assert data["stage"] == "validate-image-on-test"
        assert data["status"] == "accepted"
        assert "submitted_at" in data
        assert "correlation_id" in data

    def test_returns_correlation_id(
        self, client, job_with_completed_build_image, unique_correlation_id,
        nfs_queue_dir
    ):
        """Test correlation ID is returned in response."""
        headers = {
            "Authorization": "Bearer test-client-123",
            "X-Correlation-Id": unique_correlation_id,
        }

        with patch(
            "infra.repositories.nfs_playbook_queue_request_repository"
            ".NfsPlaybookQueueRequestRepository.is_available",
            return_value=True,
        ), patch(
            "infra.repositories.nfs_playbook_queue_request_repository"
            ".NfsPlaybookQueueRequestRepository.write_request",
            return_value=nfs_queue_dir / "requests" / "test.json",
        ):
            response = client.post(
                f"/api/v1/jobs/{job_with_completed_build_image}/stages/validate-image-on-test",
                headers=headers,
            )

        assert response.status_code == 202
        assert response.json()["correlation_id"] == unique_correlation_id

    def test_queue_submission(
        self, client, auth_headers, job_with_completed_build_image, monkeypatch
    ):
        """Test that validate request is submitted to queue."""
        # Create a mock for the queue service that tracks submissions
        mock_submissions = []
        
        def mock_write_request(self, request):
            mock_submissions.append(request)
            return f"/mock/path/{request.job_id}_{request.stage_name}.json"
        
        # Apply the mock
        monkeypatch.setattr(
            "infra.repositories.nfs_playbook_queue_request_repository.NfsPlaybookQueueRequestRepository.write_request",
            mock_write_request
        )
        monkeypatch.setattr(
            "infra.repositories.nfs_playbook_queue_request_repository.NfsPlaybookQueueRequestRepository.is_available",
            lambda self: True
        )
        
        # Make the request
        response = client.post(
            f"/api/v1/jobs/{job_with_completed_build_image}/stages/validate-image-on-test",
            headers=auth_headers,
        )
        
        # Verify response
        assert response.status_code == 202
        
        # Verify a request was submitted
        assert len(mock_submissions) == 1
        submitted_request = mock_submissions[0]
        
        # Verify request properties
        assert submitted_request.job_id == job_with_completed_build_image
        assert submitted_request.stage_name == "validate-image-on-test"
        assert str(submitted_request.playbook_path) == "discovery.yml"


class TestValidateImageOnTestValidation:
    """Validation scenarios for validate image on test."""

    def test_invalid_job_id_returns_400(self, client, auth_headers):
        """Test validate image with invalid job ID format."""
        response = client.post(
            "/api/v1/jobs/invalid-uuid/stages/validate-image-on-test",
            headers=auth_headers,
        )
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["error"] == "INVALID_JOB_ID"

    def test_nonexistent_job_returns_404(self, client, auth_headers):
        """Test validate image with non-existent job ID."""
        fake_job_id = "018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"
        response = client.post(
            f"/api/v1/jobs/{fake_job_id}/stages/validate-image-on-test",
            headers=auth_headers,
        )
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert detail["error"] == "JOB_NOT_FOUND"

    def test_stage_guard_violation_returns_412(
        self, client, auth_headers, created_job
    ):
        """Test validate image without completed build-image stage."""
        response = client.post(
            f"/api/v1/jobs/{created_job}/stages/validate-image-on-test",
            headers=auth_headers,
        )
        assert response.status_code == 412
        detail = response.json()["detail"]
        assert detail["error"] == "STAGE_GUARD_VIOLATION"
        assert "build-image" in detail["message"]


class TestValidateImageOnTestAuthentication:
    """Authentication header tests."""

    def test_missing_authorization_returns_422(
        self, client, job_with_completed_build_image
    ):
        """Test validate image without authorization header."""
        headers = {
            "X-Correlation-Id": "019bf590-1234-7890-abcd-ef1234567890",
        }
        response = client.post(
            f"/api/v1/jobs/{job_with_completed_build_image}/stages/validate-image-on-test",
            headers=headers,
        )
        assert response.status_code == 422

    def test_invalid_authorization_format_returns_401(
        self, client, job_with_completed_build_image
    ):
        """Test validate image with invalid authorization format."""
        headers = {
            "Authorization": "InvalidFormat test-token",
            "X-Correlation-Id": "019bf590-1234-7890-abcd-ef1234567890",
        }
        response = client.post(
            f"/api/v1/jobs/{job_with_completed_build_image}/stages/validate-image-on-test",
            headers=headers,
        )
        assert response.status_code == 401

    def test_empty_bearer_token_returns_401(
        self, client, job_with_completed_build_image
    ):
        """Test validate image with empty bearer token."""
        headers = {
            "Authorization": "Bearer ",
            "X-Correlation-Id": "019bf590-1234-7890-abcd-ef1234567890",
        }
        response = client.post(
            f"/api/v1/jobs/{job_with_completed_build_image}/stages/validate-image-on-test",
            headers=headers,
        )
        assert response.status_code == 401


class TestValidateImageOnTestErrorHandling:
    """Error handling tests."""

    def test_queue_unavailable_returns_500(
        self, client, auth_headers, job_with_completed_build_image
    ):
        """Test validate image when queue is unavailable."""
        with patch(
            "infra.repositories.nfs_playbook_queue_request_repository"
            ".NfsPlaybookQueueRequestRepository.is_available",
            return_value=False,
        ):
            response = client.post(
                f"/api/v1/jobs/{job_with_completed_build_image}/stages/validate-image-on-test",
                headers=auth_headers,
            )

        assert response.status_code == 500
        detail = response.json()["detail"]
        assert detail["error"] == "VALIDATION_EXECUTION_ERROR"
        # The actual error message might vary, so we don't assert on it
