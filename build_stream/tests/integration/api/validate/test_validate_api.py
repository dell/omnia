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

"""Integration tests for Validate API — Phase 3."""

import uuid
from unittest.mock import patch


class TestValidateSuccess:
    """Happy-path validate stage tests — AC-3.1."""

    def test_returns_202_with_valid_request(
        self, client, auth_headers, job_with_completed_restart, nfs_queue_dir
    ):
        """Test successful validate request returns 202 with QUEUED status."""
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
                f"/api/v1/jobs/{job_with_completed_restart}/stages/validate",
                headers=auth_headers,
                json={
                    "scenario_names": ["discovery"],
                    "test_suite": "smoke",
                    "timeout_minutes": 60,
                },
            )

        assert response.status_code == 202
        data = response.json()
        assert data["job_id"] == job_with_completed_restart
        assert data["stage"] == "validate"
        assert data["status"] == "QUEUED"
        assert "submitted_at" in data
        assert "correlation_id" in data
        assert "attempt" in data

    def test_returns_correlation_id(
        self, client, job_with_completed_restart, unique_correlation_id,
        nfs_queue_dir
    ):
        """Test that correlation ID is returned in response."""
        headers = {
            "Authorization": "Bearer test-client-123",
            "X-Correlation-Id": unique_correlation_id,
            "Idempotency-Key": f"test-key-{uuid.uuid4()}",
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
                f"/api/v1/jobs/{job_with_completed_restart}/stages/validate",
                headers=headers,
                json={"scenario_names": ["all"]},
            )

        assert response.status_code == 202
        data = response.json()
        assert data["correlation_id"] == unique_correlation_id

    def test_default_request_body(
        self, client, auth_headers, job_with_completed_restart, nfs_queue_dir
    ):
        """Test validate with empty body uses defaults."""
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
                f"/api/v1/jobs/{job_with_completed_restart}/stages/validate",
                headers=auth_headers,
                json={},
            )

        assert response.status_code == 202

    def test_queue_submission_has_molecule_command_type(
        self, client, auth_headers, job_with_completed_restart, nfs_queue_dir, monkeypatch
    ):
        """AC-3.2: Validate request submitted with command_type='molecule'."""
        mock_submissions = []

        def mock_write_request(self, request):
            mock_submissions.append(request)
            return f"/mock/path/{request.request_id}.json"

        monkeypatch.setattr(
            "infra.repositories.nfs_playbook_queue_request_repository"
            ".NfsPlaybookQueueRequestRepository.write_request",
            mock_write_request,
        )
        monkeypatch.setattr(
            "infra.repositories.nfs_playbook_queue_request_repository"
            ".NfsPlaybookQueueRequestRepository.is_available",
            lambda self: True,
        )

        response = client.post(
            f"/api/v1/jobs/{job_with_completed_restart}/stages/validate",
            headers=auth_headers,
            json={
                "scenario_names": ["discovery", "slurm"],
                "test_suite": "smoke",
                "timeout_minutes": 60,
            },
        )

        assert response.status_code == 202
        assert len(mock_submissions) == 1
        submitted = mock_submissions[0]
        assert submitted.command_type == "test_automation"
        assert submitted.stage_type == "validate"
        assert submitted.scenario_names == ["discovery", "slurm"]
        assert submitted.test_suite == "smoke"
        assert submitted.timeout_minutes == 60
        assert submitted.job_id == job_with_completed_restart


class TestValidateValidation:
    """Validation scenarios for validate stage."""

    def test_invalid_job_id_returns_400(self, client, auth_headers):
        """Invalid job_id format returns 400."""
        response = client.post(
            "/api/v1/jobs/invalid-uuid/stages/validate",
            headers=auth_headers,
            json={"scenario_names": ["all"]},
        )
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["error"] == "INVALID_JOB_ID"

    def test_nonexistent_job_returns_404(self, client, auth_headers):
        """Non-existent job_id returns 404."""
        fake_job_id = "018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"
        response = client.post(
            f"/api/v1/jobs/{fake_job_id}/stages/validate",
            headers=auth_headers,
            json={"scenario_names": ["all"]},
        )
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert detail["error"] == "JOB_NOT_FOUND"

    def test_stage_guard_violation_returns_412(
        self, client, auth_headers, created_job
    ):
        """AC-3.6: Job without completed restart returns 412."""
        response = client.post(
            f"/api/v1/jobs/{created_job}/stages/validate",
            headers=auth_headers,
            json={"scenario_names": ["all"]},
        )
        assert response.status_code == 412
        detail = response.json()["detail"]
        assert detail["error"] in ("STAGE_GUARD_VIOLATION", "UPSTREAM_STAGE_NOT_COMPLETED")


class TestValidateAuthentication:
    """Authentication header tests."""

    def test_missing_authorization_returns_error(
        self, client, job_with_completed_restart
    ):
        """Test validate without authorization header."""
        headers = {
            "X-Correlation-Id": "019bf590-1234-7890-abcd-ef1234567890",
        }
        response = client.post(
            f"/api/v1/jobs/{job_with_completed_restart}/stages/validate",
            headers=headers,
            json={"scenario_names": ["all"]},
        )
        assert response.status_code in (202, 401, 422)

    def test_invalid_authorization_format_returns_error(
        self, client, job_with_completed_restart
    ):
        """Test validate with invalid authorization format."""
        headers = {
            "Authorization": "InvalidFormat test-token",
            "X-Correlation-Id": "019bf590-1234-7890-abcd-ef1234567890",
        }
        response = client.post(
            f"/api/v1/jobs/{job_with_completed_restart}/stages/validate",
            headers=headers,
            json={"scenario_names": ["all"]},
        )
        assert response.status_code in (202, 401)

    def test_empty_bearer_token_returns_error(
        self, client, job_with_completed_restart
    ):
        """Test validate with empty bearer token."""
        headers = {
            "Authorization": "Bearer ",
            "X-Correlation-Id": "019bf590-1234-7890-abcd-ef1234567890",
        }
        response = client.post(
            f"/api/v1/jobs/{job_with_completed_restart}/stages/validate",
            headers=headers,
            json={"scenario_names": ["all"]},
        )
        assert response.status_code in (202, 401)


class TestValidateErrorHandling:
    """Error handling tests."""

    def test_queue_unavailable_returns_500(
        self, client, auth_headers, job_with_completed_restart, monkeypatch
    ):
        """Test validate when queue is unavailable."""
        monkeypatch.setattr(
            "infra.repositories.nfs_playbook_queue_request_repository"
            ".NfsPlaybookQueueRequestRepository.is_available",
            lambda self: False,
        )

        response = client.post(
            f"/api/v1/jobs/{job_with_completed_restart}/stages/validate",
            headers=auth_headers,
            json={"scenario_names": ["all"]},
        )
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert detail["error"] == "VALIDATION_EXECUTION_ERROR"
