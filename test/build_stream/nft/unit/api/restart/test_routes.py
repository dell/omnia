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

"""Unit tests for Restart API routes."""

import uuid
import pytest
from fastapi import HTTPException, status

from api.restart.routes import create_restart, _build_error_response
from api.restart.schemas import CreateRestartResponse
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    StageNotFoundError,
    TerminalStateViolationError,
)
from core.jobs.value_objects import ClientId, CorrelationId, JobId
from orchestrator.restart.commands import CreateRestartCommand
from orchestrator.restart.dtos import RestartResponse


def create_test_uuid():
    """Helper function to create valid UUIDs for testing."""
    return str(uuid.uuid4())


class MockCreateRestartUseCase:
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

        return RestartResponse(
            job_id=str(command.job_id),
            stage_name="restart",
            status="accepted",
            submitted_at="2026-02-12T18:30:00.000Z",
            image_group_id="img-group-123",
            correlation_id=str(command.correlation_id),
        )


class TestRestartRoutes:
    """Test cases for restart routes."""

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
        assert "Z" in response.timestamp

    def test_create_restart_success(self):
        """Test successful restart creation."""
        test_correlation_id = create_test_uuid()
        test_job_id = create_test_uuid()
        use_case = MockCreateRestartUseCase()

        response = create_restart(
            job_id=test_job_id,
            token_data={"client_id": "client-456"},
            use_case=use_case,
            correlation_id=CorrelationId(test_correlation_id),
        )

        assert isinstance(response, CreateRestartResponse)
        assert response.job_id == test_job_id
        assert response.stage == "restart"
        assert response.status == "accepted"
        assert response.image_group_id == "img-group-123"
        assert response.correlation_id == test_correlation_id

        # Verify use case was called with correct command
        assert len(use_case.executed_commands) == 1
        command = use_case.executed_commands[0]
        assert isinstance(command, CreateRestartCommand)
        assert str(command.job_id) == test_job_id
        assert str(command.client_id) == "client-456"
        assert str(command.correlation_id) == test_correlation_id

    def test_create_restart_response_has_links(self):
        """Test that successful response includes HATEOAS _links."""
        test_correlation_id = create_test_uuid()
        test_job_id = create_test_uuid()
        use_case = MockCreateRestartUseCase()

        response = create_restart(
            job_id=test_job_id,
            token_data={"client_id": "client-456"},
            use_case=use_case,
            correlation_id=CorrelationId(test_correlation_id),
        )

        assert response.links is not None
        assert response.links.self_link == f"/api/v1/jobs/{test_job_id}"
        assert response.links.status == f"/api/v1/jobs/{test_job_id}"

    def test_create_restart_invalid_job_id(self):
        """Test with invalid job ID format."""
        use_case = MockCreateRestartUseCase()

        with pytest.raises(HTTPException) as exc_info:
            create_restart(
                job_id="",
                token_data={"client_id": "client-456"},
                use_case=use_case,
                correlation_id=CorrelationId(create_test_uuid()),
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        detail = exc_info.value.detail
        assert detail["error"] == "INVALID_JOB_ID"
        assert "Invalid job_id format" in detail["message"]

    def test_create_restart_job_not_found(self):
        """Test when job is not found."""
        use_case = MockCreateRestartUseCase(
            error_to_raise=JobNotFoundError("Job not found", create_test_uuid())
        )

        with pytest.raises(HTTPException) as exc_info:
            create_restart(
                job_id=create_test_uuid(),
                token_data={"client_id": "client-456"},
                use_case=use_case,
                correlation_id=CorrelationId(create_test_uuid()),
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        detail = exc_info.value.detail
        assert detail["error"] == "JOB_NOT_FOUND"

    def test_create_restart_stage_not_found(self):
        """Test when restart stage is not found."""
        test_job_id = create_test_uuid()
        use_case = MockCreateRestartUseCase(
            error_to_raise=StageNotFoundError(test_job_id, "restart", create_test_uuid())
        )

        with pytest.raises(HTTPException) as exc_info:
            create_restart(
                job_id=test_job_id,
                token_data={"client_id": "client-456"},
                use_case=use_case,
                correlation_id=CorrelationId(create_test_uuid()),
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        detail = exc_info.value.detail
        assert detail["error"] == "STAGE_NOT_FOUND"

    def test_create_restart_invalid_state_transition(self):
        """Test when stage is not in PENDING state."""
        test_job_id = create_test_uuid()
        use_case = MockCreateRestartUseCase(
            error_to_raise=InvalidStateTransitionError(
                "Stage", f"{test_job_id}/restart", "IN_PROGRESS", "IN_PROGRESS", create_test_uuid()
            )
        )

        with pytest.raises(HTTPException) as exc_info:
            create_restart(
                job_id=test_job_id,
                token_data={"client_id": "client-456"},
                use_case=use_case,
                correlation_id=CorrelationId(create_test_uuid()),
            )

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        detail = exc_info.value.detail
        assert detail["error"] == "INVALID_STATE_TRANSITION"

    def test_create_restart_terminal_state_violation(self):
        """Test when stage is in a terminal state."""
        test_job_id = create_test_uuid()
        use_case = MockCreateRestartUseCase(
            error_to_raise=TerminalStateViolationError(
                "Stage", f"{test_job_id}/restart", "COMPLETED", create_test_uuid()
            )
        )

        with pytest.raises(HTTPException) as exc_info:
            create_restart(
                job_id=test_job_id,
                token_data={"client_id": "client-456"},
                use_case=use_case,
                correlation_id=CorrelationId(create_test_uuid()),
            )

        assert exc_info.value.status_code == status.HTTP_412_PRECONDITION_FAILED
        detail = exc_info.value.detail
        assert detail["error"] == "PRECONDITION_FAILED"

    def test_create_restart_unexpected_error(self):
        """Test with unexpected error."""
        use_case = MockCreateRestartUseCase(
            error_to_raise=RuntimeError("Unexpected error")
        )

        with pytest.raises(HTTPException) as exc_info:
            create_restart(
                job_id=create_test_uuid(),
                token_data={"client_id": "client-456"},
                use_case=use_case,
                correlation_id=CorrelationId(create_test_uuid()),
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = exc_info.value.detail
        assert detail["error"] == "INTERNAL_ERROR"
        assert detail["message"].lower().startswith("an unexpected error")
