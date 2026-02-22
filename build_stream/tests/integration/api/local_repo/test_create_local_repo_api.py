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

"""Integration tests for Local Repository create API."""

from unittest.mock import patch

from tests.integration.api.local_repo.conftest import setup_input_files


class TestCreateLocalRepoSuccess:
    """Happy-path create local repository tests."""

    def test_returns_202_with_valid_request(
        self, client, auth_headers, created_job, nfs_queue_dir, input_dir
    ):
        setup_input_files(input_dir, created_job)

        with patch(
            "infra.repositories.nfs_input_repository"
            ".NfsInputRepository.get_source_input_repository_path",
            return_value=input_dir / created_job / "input",
        ), patch(
            "infra.repositories.nfs_input_repository"
            ".NfsInputRepository.get_destination_input_repository_path",
            return_value=nfs_queue_dir / "dest_input",
        ), patch(
            "infra.repositories.nfs_input_repository"
            ".NfsInputRepository.validate_input_directory",
            return_value=True,
        ), patch(
            "infra.repositories.nfs_playbook_queue_request_repository"
            ".NfsPlaybookQueueRequestRepository.is_available",
            return_value=True,
        ), patch(
            "infra.repositories.nfs_playbook_queue_request_repository"
            ".NfsPlaybookQueueRequestRepository.write_request",
            return_value=nfs_queue_dir / "requests" / "test.json",
        ):
            response = client.post(
                f"/api/v1/jobs/{created_job}/stages/create-local-repository",
                headers=auth_headers,
            )

        assert response.status_code == 202
        data = response.json()
        assert data["job_id"] == created_job
        assert data["stage"] == "create-local-repository"
        assert data["status"] == "accepted"
        assert "submitted_at" in data
        assert "correlation_id" in data

    def test_returns_correlation_id(
        self, client, created_job, unique_correlation_id,
        nfs_queue_dir, input_dir
    ):
        setup_input_files(input_dir, created_job)
        headers = {
            "Authorization": "Bearer test-client-123",
            "X-Correlation-Id": unique_correlation_id,
        }

        with patch(
            "infra.repositories.nfs_input_repository"
            ".NfsInputRepository.get_source_input_repository_path",
            return_value=input_dir / created_job / "input",
        ), patch(
            "infra.repositories.nfs_input_repository"
            ".NfsInputRepository.get_destination_input_repository_path",
            return_value=nfs_queue_dir / "dest_input",
        ), patch(
            "infra.repositories.nfs_input_repository"
            ".NfsInputRepository.validate_input_directory",
            return_value=True,
        ), patch(
            "infra.repositories.nfs_playbook_queue_request_repository"
            ".NfsPlaybookQueueRequestRepository.is_available",
            return_value=True,
        ), patch(
            "infra.repositories.nfs_playbook_queue_request_repository"
            ".NfsPlaybookQueueRequestRepository.write_request",
            return_value=nfs_queue_dir / "requests" / "test.json",
        ):
            response = client.post(
                f"/api/v1/jobs/{created_job}/stages/create-local-repository",
                headers=headers,
            )

        assert response.status_code == 202
        assert response.json()["correlation_id"] == unique_correlation_id


class TestCreateLocalRepoValidation:
    """Validation scenarios for create local repository."""

    def test_invalid_job_id_returns_400(self, client, auth_headers):
        response = client.post(
            "/api/v1/jobs/invalid-uuid/stages/create-local-repository",
            headers=auth_headers,
        )
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["error"] == "INVALID_JOB_ID"

    def test_nonexistent_job_returns_404(self, client, auth_headers):
        fake_job_id = "018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"
        response = client.post(
            f"/api/v1/jobs/{fake_job_id}/stages/create-local-repository",
            headers=auth_headers,
        )
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert detail["error"] == "JOB_NOT_FOUND"


class TestCreateLocalRepoAuthentication:
    """Authentication header tests."""

    def test_missing_authorization_returns_422(self, client, created_job):
        headers = {
            "X-Correlation-Id": "019bf590-1234-7890-abcd-ef1234567890",
        }
        response = client.post(
            f"/api/v1/jobs/{created_job}/stages/create-local-repository",
            headers=headers,
        )
        assert response.status_code == 422

    def test_invalid_authorization_format_returns_401(self, client, created_job):
        headers = {
            "Authorization": "InvalidFormat test-token",
            "X-Correlation-Id": "019bf590-1234-7890-abcd-ef1234567890",
        }
        response = client.post(
            f"/api/v1/jobs/{created_job}/stages/create-local-repository",
            headers=headers,
        )
        assert response.status_code == 401

    def test_empty_bearer_token_returns_401(self, client, created_job):
        headers = {
            "Authorization": "Bearer ",
            "X-Correlation-Id": "019bf590-1234-7890-abcd-ef1234567890",
        }
        response = client.post(
            f"/api/v1/jobs/{created_job}/stages/create-local-repository",
            headers=headers,
        )
        assert response.status_code == 401


class TestCreateLocalRepoInputValidation:
    """Input file validation tests."""

    def test_missing_input_files_returns_400(self, client, auth_headers, created_job):
        with patch(
            "infra.repositories.nfs_input_repository"
            ".NfsInputRepository.validate_input_directory",
            return_value=False,
        ):
            response = client.post(
                f"/api/v1/jobs/{created_job}/stages/create-local-repository",
                headers=auth_headers,
            )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["error"] == "INPUT_FILES_MISSING"
