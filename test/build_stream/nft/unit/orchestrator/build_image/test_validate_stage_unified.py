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

"""Unit tests for _validate_stage_unified in CreateBuildImageUseCase.

Ensures the unified build-image stage follows the same retry/reset
pattern as create-local-repository and other stages:
- FAILED  -> auto-reset to PENDING + JobStateHelper.handle_job_resume
- COMPLETED -> StageAlreadyCompletedError
- IN_PROGRESS -> InvalidStateTransitionError
- PENDING -> proceed normally
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from core.jobs.entities import Job, Stage
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    StageAlreadyCompletedError,
    StageNotFoundError,
)
from core.jobs.value_objects import (
    ClientId,
    CorrelationId,
    JobId,
    StageName,
    StageState,
    StageType,
)
from orchestrator.build_image.commands import CreateBuildImageCommand
from orchestrator.build_image.use_cases import CreateBuildImageUseCase


def _uuid():
    """Generate a valid UUID string."""
    return str(uuid.uuid4())


@pytest.fixture(name="job_id")
def job_id_fixture():
    """Provide a valid JobId."""
    return JobId(_uuid())


@pytest.fixture(name="client_id")
def client_id_fixture():
    """Provide a valid ClientId."""
    return ClientId("test-client")


@pytest.fixture(name="correlation_id")
def correlation_id_fixture():
    """Provide a valid CorrelationId."""
    return CorrelationId(_uuid())


@pytest.fixture(name="mock_job")
def mock_job_fixture(client_id):
    """Provide a mock Job entity."""
    job = Job(
        job_id=JobId(_uuid()),
        client_id=client_id,
        request_client_id="test-client",
    )
    return job


@pytest.fixture(name="upstream_stage")
def upstream_stage_fixture(job_id):
    """Provide a COMPLETED create-local-repository stage."""
    stage = Stage(
        job_id=job_id,
        stage_name=StageName(StageType.CREATE_LOCAL_REPOSITORY.value),
    )
    stage.start()
    stage.complete()
    return stage


@pytest.fixture(name="command")
def command_fixture(job_id, client_id, correlation_id):
    """Provide a CreateBuildImageCommand for unified mode."""
    return CreateBuildImageCommand(
        job_id=job_id,
        client_id=client_id,
        correlation_id=correlation_id,
    )


def _make_build_image_stage(job_id, state):
    """Create a build-image stage in the given state."""
    stage = Stage(
        job_id=job_id,
        stage_name=StageName(StageType.BUILD_IMAGE.value),
    )
    if state == StageState.IN_PROGRESS:
        stage.start()
    elif state == StageState.COMPLETED:
        stage.start()
        stage.complete()
    elif state == StageState.FAILED:
        stage.start()
        stage.fail(error_code="TEST_ERROR", error_summary="test failure")
    return stage


def _make_use_case(mock_job, stages_dict):
    """Create a use case with mocked repositories."""
    job_repo = MagicMock()
    job_repo.find_by_id.return_value = mock_job

    stage_repo = MagicMock()

    def _find_by_job_and_name(_job_id, stage_name):
        return stages_dict.get(stage_name.value)

    stage_repo.find_by_job_and_name.side_effect = _find_by_job_and_name

    audit_repo = MagicMock()
    uuid_generator = MagicMock()
    uuid_generator.generate.return_value = uuid.uuid4()

    use_case = CreateBuildImageUseCase(
        job_repo=job_repo,
        stage_repo=stage_repo,
        audit_repo=audit_repo,
        config_service=MagicMock(),
        queue_service=MagicMock(),
        inventory_repo=MagicMock(),
        uuid_generator=uuid_generator,
    )
    return use_case


class TestValidateStageUnifiedPending:
    """Test that PENDING stage proceeds normally."""

    def test_pending_stage_returns_stage(
        self, job_id, mock_job, upstream_stage, command,
    ):
        """PENDING build-image stage should be returned for execution."""
        build_stage = _make_build_image_stage(job_id, StageState.PENDING)
        stages = {
            StageType.CREATE_LOCAL_REPOSITORY.value: upstream_stage,
            StageType.BUILD_IMAGE.value: build_stage,
        }
        use_case = _make_use_case(mock_job, stages)

        result = use_case._validate_stage_unified(command)

        assert result is build_stage
        assert result.stage_state == StageState.PENDING


class TestValidateStageUnifiedFailed:
    """Test that FAILED stage auto-resets to PENDING for retry."""

    @patch("orchestrator.build_image.use_cases.create_build_image.JobStateHelper")
    def test_failed_stage_auto_resets_to_pending(
        self, mock_helper, job_id, mock_job, upstream_stage, command,
    ):
        """FAILED build-image stage should be auto-reset to PENDING."""
        build_stage = _make_build_image_stage(job_id, StageState.FAILED)
        stages = {
            StageType.CREATE_LOCAL_REPOSITORY.value: upstream_stage,
            StageType.BUILD_IMAGE.value: build_stage,
        }
        use_case = _make_use_case(mock_job, stages)

        result = use_case._validate_stage_unified(command)

        assert result.stage_state == StageState.PENDING
        # Verify stage was saved after reset
        use_case._stage_repo.save.assert_called_with(build_stage)

    @patch("orchestrator.build_image.use_cases.create_build_image.JobStateHelper")
    def test_failed_stage_increments_attempt(
        self, mock_helper, job_id, mock_job, upstream_stage, command,
    ):
        """Reset from FAILED should increment the attempt counter."""
        build_stage = _make_build_image_stage(job_id, StageState.FAILED)
        stages = {
            StageType.CREATE_LOCAL_REPOSITORY.value: upstream_stage,
            StageType.BUILD_IMAGE.value: build_stage,
        }
        use_case = _make_use_case(mock_job, stages)

        result = use_case._validate_stage_unified(command)

        assert result.attempt == 2  # First attempt + reset

    @patch("orchestrator.build_image.use_cases.create_build_image.JobStateHelper")
    def test_failed_stage_calls_handle_job_resume(
        self, mock_helper, job_id, mock_job, upstream_stage, command,
    ):
        """FAILED stage reset should call JobStateHelper.handle_job_resume."""
        build_stage = _make_build_image_stage(job_id, StageState.FAILED)
        stages = {
            StageType.CREATE_LOCAL_REPOSITORY.value: upstream_stage,
            StageType.BUILD_IMAGE.value: build_stage,
        }
        use_case = _make_use_case(mock_job, stages)

        use_case._validate_stage_unified(command)

        mock_helper.handle_job_resume.assert_called_once_with(
            job_repo=use_case._job_repo,
            audit_repo=use_case._audit_repo,
            uuid_generator=use_case._uuid_generator,
            job_id=command.job_id,
            stage_name=StageType.BUILD_IMAGE.value,
            correlation_id=str(command.correlation_id),
            client_id=str(command.client_id),
        )

    @patch("orchestrator.build_image.use_cases.create_build_image.JobStateHelper")
    def test_failed_stage_clears_error_fields(
        self, mock_helper, job_id, mock_job, upstream_stage, command,
    ):
        """Reset from FAILED should clear error_code and error_summary."""
        build_stage = _make_build_image_stage(job_id, StageState.FAILED)
        assert build_stage.error_code == "TEST_ERROR"

        stages = {
            StageType.CREATE_LOCAL_REPOSITORY.value: upstream_stage,
            StageType.BUILD_IMAGE.value: build_stage,
        }
        use_case = _make_use_case(mock_job, stages)

        result = use_case._validate_stage_unified(command)

        assert result.error_code is None
        assert result.error_summary is None


class TestValidateStageUnifiedCompleted:
    """Test that COMPLETED stage raises StageAlreadyCompletedError."""

    def test_completed_stage_raises_error(
        self, job_id, mock_job, upstream_stage, command,
    ):
        """COMPLETED build-image stage should raise StageAlreadyCompletedError."""
        build_stage = _make_build_image_stage(job_id, StageState.COMPLETED)
        stages = {
            StageType.CREATE_LOCAL_REPOSITORY.value: upstream_stage,
            StageType.BUILD_IMAGE.value: build_stage,
        }
        use_case = _make_use_case(mock_job, stages)

        with pytest.raises(StageAlreadyCompletedError) as exc_info:
            use_case._validate_stage_unified(command)

        assert str(command.job_id) in str(exc_info.value)


class TestValidateStageUnifiedInProgress:
    """Test that IN_PROGRESS stage raises InvalidStateTransitionError."""

    def test_in_progress_stage_raises_error(
        self, job_id, mock_job, upstream_stage, command,
    ):
        """IN_PROGRESS build-image stage should raise InvalidStateTransitionError."""
        build_stage = _make_build_image_stage(job_id, StageState.IN_PROGRESS)
        stages = {
            StageType.CREATE_LOCAL_REPOSITORY.value: upstream_stage,
            StageType.BUILD_IMAGE.value: build_stage,
        }
        use_case = _make_use_case(mock_job, stages)

        with pytest.raises(InvalidStateTransitionError):
            use_case._validate_stage_unified(command)


class TestValidateStageUnifiedNotFound:
    """Test that missing stage raises StageNotFoundError."""

    def test_stage_not_found_raises_error(
        self, job_id, mock_job, upstream_stage, command,
    ):
        """Missing build-image stage should raise StageNotFoundError."""
        stages = {
            StageType.CREATE_LOCAL_REPOSITORY.value: upstream_stage,
            # No BUILD_IMAGE stage
        }
        use_case = _make_use_case(mock_job, stages)

        with pytest.raises(StageNotFoundError):
            use_case._validate_stage_unified(command)
