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

"""Unit tests for Validate API routes — Phase 3 (spec §7)."""

import uuid

import pytest
from fastapi import HTTPException

from api.validate.routes import create_validate, _build_error_response
from api.validate.schemas import ValidateRequestSchema
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    UpstreamStageNotCompletedError,
)
from core.jobs.value_objects import ClientId, CorrelationId
from core.validate.exceptions import (
    StageGuardViolationError,
    ValidateDomainError,
    ValidationExecutionError,
)
from orchestrator.validate.dtos import ValidateResponse as UseCaseResponse


def _uuid():
    return str(uuid.uuid4())


class MockValidateUseCase:
    """Mock use case for testing."""

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
            stage_name="validate",
            status="QUEUED",
            submitted_at="2026-02-17T10:30:00Z",
            correlation_id=str(command.correlation_id),
            attempt=1,
        )


class TestBuildErrorResponse:
    """Tests for _build_error_response helper."""

    def test_builds_correct_response(self):
        """Test building correct error response."""
        response = _build_error_response("TEST_ERROR", "Test message", "corr-123")
        assert response.error == "TEST_ERROR"
        assert response.message == "Test message"
        assert response.correlation_id == "corr-123"
        assert "Z" in response.timestamp


class TestCreateValidate:
    """Tests for create_validate route handler — AC-3.1 through AC-3.9."""

    def test_success_returns_202_body(self):
        """AC-3.1: Returns 202 with correct body for valid job."""
        job_id = _uuid()
        corr_id = _uuid()
        use_case = MockValidateUseCase()

        request_body = ValidateRequestSchema(
            scenario_names=["discovery"],
            test_suite="smoke",
            timeout_minutes=60,
        )

        response = create_validate(
            job_id=job_id,
            request_body=request_body,
            token_data={"client_id": "test-client", "scopes": ["job:write"]},
            use_case=use_case,
            correlation_id=CorrelationId(corr_id),
            _=None,
        )

        assert response.job_id == job_id
        assert response.stage == "validate"
        assert response.status == "QUEUED"
        assert response.attempt == 1
        assert "correlation_id" in response.model_dump()

    def test_command_receives_scenario_names(self):
        """AC-3.9: scenario_names propagated from request to command."""
        job_id = _uuid()
        corr_id = _uuid()
        use_case = MockValidateUseCase()

        request_body = ValidateRequestSchema(
            scenario_names=["discovery", "slurm"],
            test_suite="regression",
            timeout_minutes=240,
        )

        create_validate(
            job_id=job_id,
            request_body=request_body,
            token_data={"client_id": "test-client", "scopes": ["job:write"]},
            use_case=use_case,
            correlation_id=CorrelationId(corr_id),
            _=None,
        )

        assert len(use_case.executed_commands) == 1
        command = use_case.executed_commands[0]
        assert command.scenario_names == ["discovery", "slurm"]
        assert command.test_suite == "regression"
        assert command.timeout_minutes == 240

    def test_default_request_body(self):
        """Defaults: scenario_names=['all'], test_suite='', timeout=120."""
        job_id = _uuid()
        corr_id = _uuid()
        use_case = MockValidateUseCase()

        request_body = ValidateRequestSchema()

        create_validate(
            job_id=job_id,
            request_body=request_body,
            token_data={"client_id": "test-client", "scopes": ["job:write"]},
            use_case=use_case,
            correlation_id=CorrelationId(corr_id),
            _=None,
        )

        command = use_case.executed_commands[0]
        assert command.scenario_names == ["all"]
        assert command.test_suite == ""
        assert command.timeout_minutes == 120

    def test_invalid_job_id_returns_400(self):
        """Invalid job_id should raise 400."""
        use_case = MockValidateUseCase()
        corr_id = _uuid()

        with pytest.raises(HTTPException) as exc_info:
            create_validate(
                job_id="not-a-uuid",
                request_body=ValidateRequestSchema(),
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(corr_id),
                _=None,
            )
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "INVALID_JOB_ID"

    def test_job_not_found_returns_404(self):
        """AC-3.4: Non-existent job_id returns 404."""
        use_case = MockValidateUseCase(
            error_to_raise=JobNotFoundError(job_id=_uuid())
        )
        corr_id = _uuid()

        with pytest.raises(HTTPException) as exc_info:
            create_validate(
                job_id=_uuid(),
                request_body=ValidateRequestSchema(),
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(corr_id),
                _=None,
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error"] == "JOB_NOT_FOUND"

    def test_stage_already_active_returns_409(self):
        """AC-3.5: Duplicate call returns 409 INVALID_STATE_TRANSITION."""
        use_case = MockValidateUseCase(
            error_to_raise=InvalidStateTransitionError(
                entity_type="Stage",
                entity_id="test-id",
                from_state="QUEUED",
                to_state="QUEUED",
            )
        )
        corr_id = _uuid()

        with pytest.raises(HTTPException) as exc_info:
            create_validate(
                job_id=_uuid(),
                request_body=ValidateRequestSchema(),
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(corr_id),
                _=None,
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["error"] == "INVALID_STATE_TRANSITION"

    def test_upstream_stage_not_completed_returns_412(self):
        """AC-3.6: Job without completed restart returns 412."""
        use_case = MockValidateUseCase(
            error_to_raise=UpstreamStageNotCompletedError(
                job_id=_uuid(),
                required_stage="restart",
                actual_state="PENDING",
            )
        )
        corr_id = _uuid()

        with pytest.raises(HTTPException) as exc_info:
            create_validate(
                job_id=_uuid(),
                request_body=ValidateRequestSchema(),
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(corr_id),
                _=None,
            )
        assert exc_info.value.status_code == 412
        assert exc_info.value.detail["error"] == "UPSTREAM_STAGE_NOT_COMPLETED"

    def test_stage_guard_violation_returns_412(self):
        """StageGuardViolationError should raise 412."""
        use_case = MockValidateUseCase(
            error_to_raise=StageGuardViolationError(
                message="Restart stage not completed",
                correlation_id=_uuid(),
            )
        )
        corr_id = _uuid()

        with pytest.raises(HTTPException) as exc_info:
            create_validate(
                job_id=_uuid(),
                request_body=ValidateRequestSchema(),
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(corr_id),
                _=None,
            )
        assert exc_info.value.status_code == 412
        assert exc_info.value.detail["error"] == "STAGE_GUARD_VIOLATION"

    def test_validation_execution_error_returns_500(self):
        """ValidationExecutionError should raise 500."""
        use_case = MockValidateUseCase(
            error_to_raise=ValidationExecutionError("Queue failed", "corr-123")
        )
        corr_id = _uuid()

        with pytest.raises(HTTPException) as exc_info:
            create_validate(
                job_id=_uuid(),
                request_body=ValidateRequestSchema(),
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(corr_id),
                _=None,
            )
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail["error"] == "VALIDATION_EXECUTION_ERROR"

    def test_validate_domain_error_returns_500(self):
        """ValidateDomainError should raise 500."""
        use_case = MockValidateUseCase(
            error_to_raise=ValidateDomainError("Domain error", "corr-123")
        )
        corr_id = _uuid()

        with pytest.raises(HTTPException) as exc_info:
            create_validate(
                job_id=_uuid(),
                request_body=ValidateRequestSchema(),
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(corr_id),
                _=None,
            )
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail["error"] == "VALIDATE_ERROR"

    def test_unexpected_error_returns_500(self):
        """Unexpected errors should raise 500 INTERNAL_ERROR."""
        use_case = MockValidateUseCase(
            error_to_raise=RuntimeError("unexpected")
        )
        corr_id = _uuid()

        with pytest.raises(HTTPException) as exc_info:
            create_validate(
                job_id=_uuid(),
                request_body=ValidateRequestSchema(),
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(corr_id),
                _=None,
            )
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail["error"] == "INTERNAL_ERROR"

    def test_correlation_id_propagates(self):
        """AC-3.7: correlation_id propagates to response."""
        job_id = _uuid()
        corr_id = _uuid()
        use_case = MockValidateUseCase()

        response = create_validate(
            job_id=job_id,
            request_body=ValidateRequestSchema(),
            token_data={"client_id": "test-client", "scopes": ["job:write"]},
            use_case=use_case,
            correlation_id=CorrelationId(corr_id),
            _=None,
        )

        assert response.correlation_id == corr_id
        command = use_case.executed_commands[0]
        assert str(command.correlation_id) == corr_id
