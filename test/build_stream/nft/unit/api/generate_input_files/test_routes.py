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

"""Unit tests for Generate Input Files API routes."""

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, status

from api.generate_input_files.routes import generate_input_files
from api.generate_input_files.schemas import GenerateInputFilesRequest
from core.artifacts.exceptions import ArtifactNotFoundError
from core.catalog.exceptions import (
    AdapterPolicyValidationError,
    ConfigGenerationError,
)
from core.jobs.exceptions import (
    JobNotFoundError,
    StageAlreadyCompletedError,
    TerminalStateViolationError,
    UpstreamStageNotCompletedError,
)


def create_test_uuid():
    """Helper to create valid UUIDs for testing."""
    return str(uuid.uuid4())


class MockArtifactRef:
    """Mock artifact reference."""
    def __init__(self):
        self.key = "configs/test-key"
        self.digest = "sha256:abcd1234"
        self.size_bytes = 1024
        self.uri = "/path/to/configs"


class MockGenerateInputFilesResult:
    """Mock result for generate input files."""
    def __init__(self):
        self.job_id = create_test_uuid()
        self.stage_state = "COMPLETED"
        self.message = "Input files generated successfully"
        self.configs_ref = MockArtifactRef()
        self.config_file_count = 5
        self.config_files = ["config1.yml", "config2.yml"]
        self.completed_at = "2026-03-24T12:00:00Z"


class MockGenerateInputFilesUseCase:
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
        return MockGenerateInputFilesResult()


class MockDBSession:
    """Mock database session."""

    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.is_active = True

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


@pytest.mark.asyncio
class TestGenerateInputFilesRoutes:
    """Test cases for generate input files routes."""

    async def test_generate_input_files_success(self):
        """Test successful input file generation."""
        test_job_id = create_test_uuid()
        use_case = MockGenerateInputFilesUseCase()
        db_session = MockDBSession()

        response = await generate_input_files(
            job_id=test_job_id,
            request_body=None,
            token_data={"client_id": "client-123"},
            scope_data={"scope": "catalog:read"},
            use_case=use_case,
            db_session=db_session,
        )

        assert response.stage_state == "COMPLETED"
        assert response.message == "Input files generated successfully"
        assert response.job_id is not None
        assert len(use_case.executed_commands) == 1

    async def test_generate_input_files_with_custom_policy_path(self):
        """Test with custom adapter policy path."""
        test_job_id = create_test_uuid()
        use_case = MockGenerateInputFilesUseCase()
        db_session = MockDBSession()

        request_body = GenerateInputFilesRequest(
            adapter_policy_path="/valid/path/to/policy.yml"
        )

        response = await generate_input_files(
            job_id=test_job_id,
            request_body=request_body,
            token_data={"client_id": "client-123"},
            scope_data={"scope": "catalog:read"},
            use_case=use_case,
            db_session=db_session,
        )

        assert response.stage_state == "COMPLETED"
        assert len(use_case.executed_commands) == 1
        # Verify command has the adapter policy path
        command = use_case.executed_commands[0]
        assert command.adapter_policy_path is not None

    async def test_generate_input_files_invalid_job_id(self):
        """Test with invalid job ID format."""
        use_case = MockGenerateInputFilesUseCase()
        db_session = MockDBSession()

        with pytest.raises(HTTPException) as exc_info:
            await generate_input_files(
                job_id="not-a-uuid",
                request_body=None,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        detail = exc_info.value.detail
        assert detail["error"] == "INVALID_JOB_ID"

    async def test_generate_input_files_invalid_policy_path(self):
        """Test with invalid adapter policy path."""
        test_job_id = create_test_uuid()
        use_case = MockGenerateInputFilesUseCase()
        db_session = MockDBSession()

        request_body = GenerateInputFilesRequest(
            adapter_policy_path="../../../etc/passwd"  # Path traversal attempt
        )

        with pytest.raises(HTTPException) as exc_info:
            await generate_input_files(
                job_id=test_job_id,
                request_body=request_body,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        detail = exc_info.value.detail
        assert detail["error"] == "INVALID_POLICY_PATH"

    async def test_generate_input_files_job_not_found(self):
        """Test when job is not found."""
        test_job_id = create_test_uuid()
        use_case = MockGenerateInputFilesUseCase(
            error_to_raise=JobNotFoundError("Job not found", test_job_id)
        )
        db_session = MockDBSession()

        with pytest.raises(HTTPException) as exc_info:
            await generate_input_files(
                job_id=test_job_id,
                request_body=None,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        detail = exc_info.value.detail
        assert detail["error"] == "JOB_NOT_FOUND"

    async def test_generate_input_files_terminal_state_violation(self):
        """Test when job is in terminal state."""
        test_job_id = create_test_uuid()
        use_case = MockGenerateInputFilesUseCase(
            error_to_raise=TerminalStateViolationError("Job", test_job_id, "FAILED")
        )
        db_session = MockDBSession()

        with pytest.raises(HTTPException) as exc_info:
            await generate_input_files(
                job_id=test_job_id,
                request_body=None,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        detail = exc_info.value.detail
        assert detail["error"] == "TERMINAL_STATE"

    async def test_generate_input_files_stage_already_completed(self):
        """Test when stage is already completed."""
        test_job_id = create_test_uuid()
        use_case = MockGenerateInputFilesUseCase(
            error_to_raise=StageAlreadyCompletedError("Stage", test_job_id, "generate-input-files")
        )
        db_session = MockDBSession()

        with pytest.raises(HTTPException) as exc_info:
            await generate_input_files(
                job_id=test_job_id,
                request_body=None,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        detail = exc_info.value.detail
        assert detail["error"] == "STAGE_ALREADY_COMPLETED"

    async def test_generate_input_files_upstream_stage_not_completed(self):
        """Test when upstream stage (parse-catalog) is not completed."""
        test_job_id = create_test_uuid()
        use_case = MockGenerateInputFilesUseCase(
            error_to_raise=UpstreamStageNotCompletedError(
                "generate-input-files",
                test_job_id,
                "parse-catalog"
            )
        )
        db_session = MockDBSession()

        with pytest.raises(HTTPException) as exc_info:
            await generate_input_files(
                job_id=test_job_id,
                request_body=None,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_412_PRECONDITION_FAILED
        detail = exc_info.value.detail
        assert detail["error"] == "UPSTREAM_STAGE_NOT_COMPLETED"

    async def test_generate_input_files_artifact_not_found(self):
        """Test when upstream artifact is not found."""
        test_job_id = create_test_uuid()
        use_case = MockGenerateInputFilesUseCase(
            error_to_raise=ArtifactNotFoundError("Artifact not found", "catalog-key")
        )
        db_session = MockDBSession()

        with pytest.raises(HTTPException) as exc_info:
            await generate_input_files(
                job_id=test_job_id,
                request_body=None,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        detail = exc_info.value.detail
        assert detail["error"] == "UPSTREAM_ARTIFACT_NOT_FOUND"

    async def test_generate_input_files_adapter_policy_validation_error(self):
        """Test when adapter policy validation fails."""
        test_job_id = create_test_uuid()
        use_case = MockGenerateInputFilesUseCase(
            error_to_raise=AdapterPolicyValidationError("Invalid adapter policy")
        )
        db_session = MockDBSession()

        with pytest.raises(HTTPException) as exc_info:
            await generate_input_files(
                job_id=test_job_id,
                request_body=None,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = exc_info.value.detail
        assert detail["error"] == "CONFIG_GENERATION_FAILED"

    async def test_generate_input_files_config_generation_error(self):
        """Test when config generation fails."""
        test_job_id = create_test_uuid()
        use_case = MockGenerateInputFilesUseCase(
            error_to_raise=ConfigGenerationError("Failed to generate config")
        )
        db_session = MockDBSession()

        with pytest.raises(HTTPException) as exc_info:
            await generate_input_files(
                job_id=test_job_id,
                request_body=None,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = exc_info.value.detail
        assert detail["error"] == "CONFIG_GENERATION_FAILED"

    async def test_generate_input_files_unexpected_error(self):
        """Test with unexpected error."""
        test_job_id = create_test_uuid()
        use_case = MockGenerateInputFilesUseCase(
            error_to_raise=RuntimeError("Unexpected error")
        )
        db_session = MockDBSession()

        with pytest.raises(HTTPException) as exc_info:
            await generate_input_files(
                job_id=test_job_id,
                request_body=None,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = exc_info.value.detail
        assert detail["error"] == "INTERNAL_ERROR"
        assert "unexpected error" in detail["message"].lower()
