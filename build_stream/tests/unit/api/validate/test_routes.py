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

"""Unit tests for ValidateImageOnTest API routes."""

import uuid

import pytest
from fastapi import HTTPException

from api.validate.routes import create_validate_image_on_test, _build_error_response
from api.validate.schemas import (
    ValidateImageOnTestRequest,
)
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    UpstreamStageNotCompletedError,
)
from core.jobs.value_objects import ClientId, CorrelationId
from core.validate.exceptions import (
    ValidationExecutionError,
)
from orchestrator.validate.dtos import ValidateImageOnTestResponse as UseCaseResponse


def _uuid():
    return str(uuid.uuid4())


class MockValidateUseCase:
    """Mock use case for testing."""
    # pylint: disable=too-few-public-methods

    def __init__(self, error_to_raise=None):
        self.error_to_raise = error_to_raise
        self.executed_commands = []

    def execute(self, command):
        """Mock execute method."""
        self.executed_commands.append(command)
        if self.error_to_raise:
            raise self.error_to_raise

        return UseCaseResponse(
            job_id=str(command.job_id),
            stage_name="validate-image-on-test",
            status="accepted",
            submitted_at="2026-02-17T10:30:00Z",
            correlation_id=str(command.correlation_id),
        )


class TestBuildErrorResponse:
    """Tests for _build_error_response helper."""
    # pylint: disable=too-few-public-methods

    def test_builds_correct_response(self):
        """Test building correct error response."""
        response = _build_error_response("TEST_ERROR", "Test message", "corr-123")
        assert response.error == "TEST_ERROR"
        assert response.message == "Test message"
        assert response.correlation_id == "corr-123"
        assert "Z" in response.timestamp


class TestCreateValidateImageOnTest:
    """Tests for create_validate_image_on_test route handler."""

    def test_success(self):
        """Test successful response."""
        job_id = _uuid()
        corr_id = _uuid()
        use_case = MockValidateUseCase()
        
        request_body = ValidateImageOnTestRequest(image_key="test-image")
        
        response = create_validate_image_on_test(
            job_id=job_id,
            request_body=request_body,
            token_data={"client_id": "test-client", "scopes": ["job:write"]},
            use_case=use_case,
            correlation_id=CorrelationId(corr_id),
            _=None,
        )

        assert response.job_id == job_id
        assert response.stage == "validate-image-on-test"
        assert response.status == "accepted"
        assert response.correlation_id == corr_id
        assert "submitted_at" in response.model_dump()

        # Verify command was created correctly
        assert len(use_case.executed_commands) == 1
        command = use_case.executed_commands[0]
        assert str(command.job_id) == job_id
        assert str(command.client_id) == "test-client"
        assert str(command.correlation_id) == corr_id

    def test_invalid_job_id(self):
        """Invalid job_id should raise 400."""
        use_case = MockValidateUseCase()
        corr_id = _uuid()

        with pytest.raises(HTTPException) as exc_info:
            create_validate_image_on_test(
                job_id="not-a-uuid",
                request_body=ValidateImageOnTestRequest(image_key="test-image"),
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(corr_id),
                _=None,
            )
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "INVALID_JOB_ID"

    def test_job_not_found(self):
        """JobNotFoundError should raise 404."""
        use_case = MockValidateUseCase(
            error_to_raise=JobNotFoundError(job_id=_uuid())
        )
        corr_id = _uuid()

        with pytest.raises(HTTPException) as exc_info:
            create_validate_image_on_test(
                job_id=_uuid(),
                request_body=ValidateImageOnTestRequest(image_key="test-image"),
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(corr_id),
                _=None,
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error"] == "JOB_NOT_FOUND"

    def test_invalid_state_transition(self):
        """InvalidStateTransitionError should raise 409."""
        use_case = MockValidateUseCase(
            error_to_raise=InvalidStateTransitionError(
                entity_type="Stage",
                entity_id="test",
                from_state="COMPLETED",
                to_state="IN_PROGRESS",
            )
        )
        corr_id = _uuid()

        with pytest.raises(HTTPException) as exc_info:
            create_validate_image_on_test(
                job_id=_uuid(),
                request_body=ValidateImageOnTestRequest(image_key="test-image"),
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(corr_id),
                _=None,
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["error"] == "INVALID_STATE_TRANSITION"

    def test_upstream_stage_not_completed(self):
        """UpstreamStageNotCompletedError should raise 422."""
        use_case = MockValidateUseCase(
            error_to_raise=UpstreamStageNotCompletedError(
                job_id="test-job-id",
                required_stage="build-image-x86_64 or build-image-aarch64",
                actual_state="x86_64: PENDING, aarch64: NOT_FOUND",
                correlation_id="corr-123"
            )
        )
        corr_id = _uuid()

        with pytest.raises(HTTPException) as exc_info:
            create_validate_image_on_test(
                job_id=_uuid(),
                request_body=ValidateImageOnTestRequest(image_key="test-image"),
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(corr_id),
                _=None,
            )
        assert exc_info.value.status_code == 412
        assert exc_info.value.detail["error"] == "UPSTREAM_STAGE_NOT_COMPLETED"

    def test_validation_execution_error(self):
        """ValidationExecutionError should raise 500."""
        use_case = MockValidateUseCase(
            error_to_raise=ValidationExecutionError(
                "Queue failed", "corr-123"
            )
        )
        corr_id = _uuid()

        with pytest.raises(HTTPException) as exc_info:
            create_validate_image_on_test(
                job_id=_uuid(),
                request_body=ValidateImageOnTestRequest(image_key="test-image"),
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(corr_id),
                _=None,
            )
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail["error"] == "VALIDATION_EXECUTION_ERROR"

    def test_unexpected_error(self):
        """Unexpected errors should raise 500."""
        use_case = MockValidateUseCase(
            error_to_raise=RuntimeError("unexpected")
        )
        corr_id = _uuid()

        with pytest.raises(HTTPException) as exc_info:
            create_validate_image_on_test(
                job_id=_uuid(),
                request_body=ValidateImageOnTestRequest(image_key="test-image"),
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(corr_id),
                _=None,
            )
        assert exc_info.value.status_code == 500
