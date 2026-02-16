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

"""Unit tests for Build Image API routes."""

import pytest
from fastapi import HTTPException, status

from api.build_image.routes import create_build_image, _build_error_response
from api.build_image.schemas import CreateBuildImageRequest, CreateBuildImageResponse
from core.build_image.exceptions import (
    BuildImageDomainError,
    InvalidArchitectureError,
    InvalidFunctionalGroupsError,
    InvalidImageKeyError,
    InventoryHostMissingError,
)
from core.jobs.exceptions import InvalidStateTransitionError, JobNotFoundError
from core.jobs.value_objects import ClientId, CorrelationId, JobId
from orchestrator.build_image.commands import CreateBuildImageCommand
from orchestrator.build_image.dtos import BuildImageResponse


class MockCreateBuildImageUseCase:
    """Mock use case for testing."""

    def __init__(self, error_to_raise=None):
        """Initialize mock with optional failure."""
        self.error_to_raise = error_to_raise
        self.executed_commands = []

    def execute(self, command):
        """Mock execute method."""
        self.executed_commands.append(command)
        if self.error_to_raise:
            raise self.error_to_raise

        return BuildImageResponse(
            job_id=str(command.job_id),
            stage_name="build-image",
            status="accepted",
            submitted_at="2026-02-12T18:30:00.000Z",
            correlation_id=str(command.correlation_id),
            architecture=command.architecture,
            image_key=command.image_key,
            functional_groups=command.functional_groups,
        )


class TestBuildImageRoutes:
    """Test cases for build image routes."""

    def test_build_error_response(self):
        """Test error response builder."""
        response = _build_error_response(
            "TEST_ERROR",
            "Test error message",
            "corr-123"
        )
        
        assert response.error == "TEST_ERROR"
        assert response.message == "Test error message"
        assert response.correlation_id == "corr-123"
        assert "Z" in response.timestamp  # ISO format with Z suffix

    def test_create_build_image_success(self):
        """Test successful build image creation."""
        use_case = MockCreateBuildImageUseCase()
        
        request_body = CreateBuildImageRequest(
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1", "group2"]
        )
        
        response = create_build_image(
            job_id="job-123",
            request_body=request_body,
            use_case=use_case,
            client_id=ClientId("client-456"),
            correlation_id=CorrelationId("corr-789")
        )
        
        assert isinstance(response, CreateBuildImageResponse)
        assert response.job_id == "job-123"
        assert response.stage == "build-image"
        assert response.status == "accepted"
        assert response.architecture == "x86_64"
        assert response.image_key == "test-image"
        assert response.functional_groups == ["group1", "group2"]
        assert response.correlation_id == "corr-789"
        
        # Verify use case was called with correct command
        assert len(use_case.executed_commands) == 1
        command = use_case.executed_commands[0]
        assert isinstance(command, CreateBuildImageCommand)
        assert str(command.job_id) == "job-123"
        assert str(command.client_id) == "client-456"
        assert str(command.correlation_id) == "corr-789"
        assert command.architecture == "x86_64"
        assert command.image_key == "test-image"
        assert command.functional_groups == ["group1", "group2"]

    def test_create_build_image_invalid_job_id(self):
        """Test with invalid job ID."""
        use_case = MockCreateBuildImageUseCase()
        
        request_body = CreateBuildImageRequest(
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1"]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            create_build_image(
                job_id="",  # Invalid empty job ID
                request_body=request_body,
                use_case=use_case,
                client_id=ClientId("client-456"),
                correlation_id=CorrelationId("corr-789")
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        detail = exc_info.value.detail
        assert detail["error"] == "INVALID_JOB_ID"
        assert "Invalid job_id format" in detail["message"]

    def test_create_build_image_job_not_found(self):
        """Test when job is not found."""
        use_case = MockCreateBuildImageUseCase(
            error_to_raise=JobNotFoundError("Job not found", "corr-789")
        )
        
        request_body = CreateBuildImageRequest(
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1"]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            create_build_image(
                job_id="job-123",
                request_body=request_body,
                use_case=use_case,
                client_id=ClientId("client-456"),
                correlation_id=CorrelationId("corr-789")
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        detail = exc_info.value.detail
        assert detail["error"] == "JOB_NOT_FOUND"

    def test_create_build_image_invalid_state_transition(self):
        """Test when stage is not in PENDING state."""
        use_case = MockCreateBuildImageUseCase(
            error_to_raise=InvalidStateTransitionError("Invalid state", "corr-789")
        )
        
        request_body = CreateBuildImageRequest(
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1"]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            create_build_image(
                job_id="job-123",
                request_body=request_body,
                use_case=use_case,
                client_id=ClientId("client-456"),
                correlation_id=CorrelationId("corr-789")
            )
        
        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        detail = exc_info.value.detail
        assert detail["error"] == "INVALID_STATE_TRANSITION"

    def test_create_build_image_invalid_architecture(self):
        """Test with invalid architecture."""
        use_case = MockCreateBuildImageUseCase(
            error_to_raise=InvalidArchitectureError("Invalid architecture", "corr-789")
        )
        
        request_body = CreateBuildImageRequest(
            architecture="invalid",
            image_key="test-image",
            functional_groups=["group1"]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            create_build_image(
                job_id="job-123",
                request_body=request_body,
                use_case=use_case,
                client_id=ClientId("client-456"),
                correlation_id=CorrelationId("corr-789")
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        detail = exc_info.value.detail
        assert detail["error"] == "INVALID_ARCHITECTURE"

    def test_create_build_image_invalid_image_key(self):
        """Test with invalid image key."""
        use_case = MockCreateBuildImageUseCase(
            error_to_raise=InvalidImageKeyError("Invalid image key", "corr-789")
        )
        
        request_body = CreateBuildImageRequest(
            architecture="x86_64",
            image_key="invalid@key",
            functional_groups=["group1"]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            create_build_image(
                job_id="job-123",
                request_body=request_body,
                use_case=use_case,
                client_id=ClientId("client-456"),
                correlation_id=CorrelationId("corr-789")
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        detail = exc_info.value.detail
        assert detail["error"] == "INVALID_IMAGE_KEY"

    def test_create_build_image_invalid_functional_groups(self):
        """Test with invalid functional groups."""
        use_case = MockCreateBuildImageUseCase(
            error_to_raise=InvalidFunctionalGroupsError("Invalid groups", "corr-789")
        )
        
        request_body = CreateBuildImageRequest(
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["invalid@group"]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            create_build_image(
                job_id="job-123",
                request_body=request_body,
                use_case=use_case,
                client_id=ClientId("client-456"),
                correlation_id=CorrelationId("corr-789")
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        detail = exc_info.value.detail
        assert detail["error"] == "INVALID_FUNCTIONAL_GROUPS"

    def test_create_build_image_missing_inventory_host(self):
        """Test aarch64 build with missing inventory host."""
        use_case = MockCreateBuildImageUseCase(
            error_to_raise=InventoryHostMissingError("Missing host", "corr-789")
        )
        
        request_body = CreateBuildImageRequest(
            architecture="aarch64",
            image_key="test-image",
            functional_groups=["group1"]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            create_build_image(
                job_id="job-123",
                request_body=request_body,
                use_case=use_case,
                client_id=ClientId("client-456"),
                correlation_id=CorrelationId("corr-789")
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        detail = exc_info.value.detail
        assert detail["error"] == "INVENTORY_HOST_MISSING"

    def test_create_build_image_domain_error(self):
        """Test with domain error."""
        use_case = MockCreateBuildImageUseCase(
            error_to_raise=BuildImageDomainError("Domain error", "corr-789")
        )
        
        request_body = CreateBuildImageRequest(
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1"]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            create_build_image(
                job_id="job-123",
                request_body=request_body,
                use_case=use_case,
                client_id=ClientId("client-456"),
                correlation_id=CorrelationId("corr-789")
            )
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = exc_info.value.detail
        assert detail["error"] == "BUILD_IMAGE_ERROR"

    def test_create_build_image_unexpected_error(self):
        """Test with unexpected error."""
        use_case = MockCreateBuildImageUseCase(error_to_raise=RuntimeError("Unexpected error"))
        
        request_body = CreateBuildImageRequest(
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1"]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            create_build_image(
                job_id="job-123",
                request_body=request_body,
                use_case=use_case,
                client_id=ClientId("client-456"),
                correlation_id=CorrelationId("corr-789")
            )
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = exc_info.value.detail
        assert detail["error"] == "INTERNAL_ERROR"
        assert detail["message"].lower().startswith("an unexpected error")
