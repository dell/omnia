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

"""Unit tests for local repository API routes."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.local_repo.routes import router
from core.jobs.exceptions import JobNotFoundError
from core.jobs.value_objects import JobId
from core.localrepo.exceptions import (
    InputDirectoryInvalidError,
    InputFilesMissingError,
    QueueUnavailableError,
)
from api.local_repo.schemas import CreateLocalRepoResponse
from orchestrator.local_repo.dtos import LocalRepoResponse


class TestCreateLocalRepositoryRoute:
    """Tests for POST /api/v1/jobs/{job_id}/stages/create-local-repository."""

    @pytest.fixture
    def mock_use_case(self):
        """Mock CreateLocalRepoUseCase."""
        use_case = MagicMock()
        use_case.execute = MagicMock()
        return use_case

    @pytest.fixture
    def job_id(self):
        """Provide a valid job ID."""
        return str(uuid.uuid4())

    def test_success_response(self, mock_use_case, job_id):
        """Test successful API call returns 202."""
        # Setup mock response
        expected_response = LocalRepoResponse(
            job_id=job_id,
            stage_name="create-local-repository",
            status="accepted",
            submitted_at="2026-02-10T07:00:00Z",
            correlation_id=str(uuid.uuid4()),
        )
        mock_use_case.execute.return_value = expected_response

        # Create app with dependency override
        from api.local_repo.dependencies import get_create_local_repo_use_case
        from api.dependencies import verify_token
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_create_local_repo_use_case] = lambda: mock_use_case
        app.dependency_overrides[verify_token] = lambda: {"sub": "test-client", "client_id": "test-client-id", "scopes": ["job:write"]}
        client = TestClient(app)

        # Make request
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers={"Authorization": "Bearer test-token", "X-Correlation-Id": str(uuid.uuid4())},
        )

        # Verify response
        assert response.status_code == 202
        response_data = response.json()
        assert response_data["job_id"] == job_id
        assert response_data["stage"] == "create-local-repository"
        assert response_data["status"] == "accepted"
        assert "submitted_at" in response_data
        assert "correlation_id" in response_data

    def test_job_not_found_returns_404(self, mock_use_case, job_id):
        """Test that JobNotFoundError returns 404."""
        # Setup mock to raise exception
        mock_use_case.execute.side_effect = JobNotFoundError(job_id=JobId(job_id))

        # Create app with dependency override
        from api.local_repo.dependencies import get_create_local_repo_use_case
        from api.dependencies import verify_token
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_create_local_repo_use_case] = lambda: mock_use_case
        app.dependency_overrides[verify_token] = lambda: {"sub": "test-client", "client_id": "test-client-id", "scopes": ["job:write"]}
        client = TestClient(app)

        # Make request
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers={"Authorization": "Bearer test-token"},
        )

        # Verify response
        assert response.status_code == 404
        response_data = response.json()
        assert response_data["detail"]["error"] == "JOB_NOT_FOUND"

    def test_input_files_missing_returns_400(self, mock_use_case, job_id):
        """Test that InputFilesMissingError returns 400."""
        # Setup mock to raise exception
        mock_use_case.execute.side_effect = InputFilesMissingError(
            job_id=JobId(job_id),
            input_path="/input/path",
            correlation_id=str(uuid.uuid4()),
        )

        # Create app with dependency override
        from api.local_repo.dependencies import get_create_local_repo_use_case
        from api.dependencies import verify_token
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_create_local_repo_use_case] = lambda: mock_use_case
        app.dependency_overrides[verify_token] = lambda: {"sub": "test-client", "client_id": "test-client-id", "scopes": ["job:write"]}
        client = TestClient(app)

        # Make request
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers={"Authorization": "Bearer test-token"},
        )

        # Verify response
        assert response.status_code == 400
        response_data = response.json()
        assert response_data["detail"]["error"] == "INPUT_FILES_MISSING"

    def test_input_directory_invalid_returns_400(self, mock_use_case, job_id):
        """Test that InputDirectoryInvalidError returns 400."""
        # Setup mock to raise exception
        mock_use_case.execute.side_effect = InputDirectoryInvalidError(
            job_id=JobId(job_id),
            input_path="/input/path",
            reason="Directory is empty",
            correlation_id=str(uuid.uuid4()),
        )

        # Create app with dependency override
        from api.local_repo.dependencies import get_create_local_repo_use_case
        from api.dependencies import verify_token
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_create_local_repo_use_case] = lambda: mock_use_case
        app.dependency_overrides[verify_token] = lambda: {"sub": "test-client", "client_id": "test-client-id", "scopes": ["job:write"]}
        client = TestClient(app)

        # Make request
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers={"Authorization": "Bearer test-token"},
        )

        # Verify response
        assert response.status_code == 400
        response_data = response.json()
        assert response_data["detail"]["error"] == "INPUT_DIRECTORY_INVALID"

    def test_queue_unavailable_returns_503(self, mock_use_case, job_id):
        """Test that QueueUnavailableError returns 503."""
        # Setup mock to raise exception
        mock_use_case.execute.side_effect = QueueUnavailableError(
            queue_path="/queue/path",
            reason="NFS not mounted",
            correlation_id=str(uuid.uuid4()),
        )

        # Create app with dependency override
        from api.local_repo.dependencies import get_create_local_repo_use_case
        from api.dependencies import verify_token
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_create_local_repo_use_case] = lambda: mock_use_case
        app.dependency_overrides[verify_token] = lambda: {"sub": "test-client", "client_id": "test-client-id", "scopes": ["job:write"]}
        client = TestClient(app)

        # Make request
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers={"Authorization": "Bearer test-token"},
        )

        # Verify response
        assert response.status_code == 503
        response_data = response.json()
        assert response_data["detail"]["error"] == "QUEUE_UNAVAILABLE"

    def test_unexpected_exception_returns_500(self, mock_use_case, job_id):
        """Test that unexpected exceptions return 500."""
        # Setup mock to raise exception
        mock_use_case.execute.side_effect = Exception("Unexpected error")

        # Create app with dependency override
        from api.local_repo.dependencies import get_create_local_repo_use_case
        from api.dependencies import verify_token
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_create_local_repo_use_case] = lambda: mock_use_case
        app.dependency_overrides[verify_token] = lambda: {"sub": "test-client", "client_id": "test-client-id", "scopes": ["job:write"]}
        client = TestClient(app)

        # Make request
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers={"Authorization": "Bearer test-token"},
        )

        # Verify response
        assert response.status_code == 500
        response_data = response.json()
        assert response_data["detail"]["error"] == "INTERNAL_ERROR"

    def test_invalid_job_id_format_returns_400(self, mock_use_case):
        """Test that invalid job ID format returns 400."""
        # Create app with dependency override
        from api.local_repo.dependencies import get_create_local_repo_use_case
        from api.dependencies import verify_token
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_create_local_repo_use_case] = lambda: mock_use_case
        app.dependency_overrides[verify_token] = lambda: {"sub": "test-client", "client_id": "test-client-id", "scopes": ["job:write"]}
        client = TestClient(app)

        # Make request with invalid job ID
        response = client.post(
            "/api/v1/jobs/invalid-uuid/stages/create-local-repository",
            headers={"Authorization": "Bearer test-token"},
        )

        # Verify response
        assert response.status_code == 400
        response_data = response.json()
        assert response_data["detail"]["error"] == "INVALID_JOB_ID"

    def test_missing_authorization_returns_401(self, mock_use_case, job_id):
        """Test that missing authorization returns 401."""
        # Create app with dependency override
        from api.local_repo.dependencies import get_create_local_repo_use_case
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_create_local_repo_use_case] = lambda: mock_use_case
        client = TestClient(app)

        # Make request without auth
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
        )

        # Verify response - returns 401 for missing authorization
        assert response.status_code == 401

    def test_correlation_id_header_propagated(self, mock_use_case, job_id):
        """Test that X-Correlation-Id header is propagated."""
        correlation_id = str(uuid.uuid4())

        # Setup mock
        mock_use_case.execute.return_value = LocalRepoResponse(
            job_id=job_id,
            stage_name="create-local-repository",
            status="accepted",
            submitted_at="2026-02-10T07:00:00Z",
            correlation_id=correlation_id,
        )

        # Create app with dependency override
        from api.local_repo.dependencies import get_create_local_repo_use_case
        from api.dependencies import verify_token
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_create_local_repo_use_case] = lambda: mock_use_case
        app.dependency_overrides[verify_token] = lambda: {"sub": "test-client", "client_id": "test-client-id", "scopes": ["job:write"]}
        client = TestClient(app)

        # Make request with correlation ID
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers={
                "Authorization": "Bearer test-token",
                "X-Correlation-Id": correlation_id,
            },
        )

        # Verify response
        assert response.status_code == 202
        response_data = response.json()
        assert response_data["correlation_id"] == correlation_id
