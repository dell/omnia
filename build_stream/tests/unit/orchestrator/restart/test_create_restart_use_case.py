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

"""Unit tests for CreateRestartUseCase."""

import uuid

import pytest

from core.jobs.entities import Stage
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    StageNotFoundError,
    TerminalStateViolationError,
)
from core.jobs.value_objects import (
    ClientId, CorrelationId, JobId, StageName, StageState, StageType,
)
from core.localrepo.entities import PlaybookRequest
from orchestrator.restart.commands import CreateRestartCommand
from orchestrator.restart.use_cases import CreateRestartUseCase


def _uuid():
    """Generate a valid UUID string."""
    return str(uuid.uuid4())


class MockJobRepository:
    """Mock job repository."""

    def __init__(self, job=None):
        """Initialize mock with job data."""
        self.job = job
        self.saved_jobs = []

    def find_by_id(self, job_id):
        """Return mock job or None."""
        return self.job

    def save(self, job):
        """Save job."""
        self.saved_jobs.append(job)


class MockStageRepository:
    """Mock stage repository."""

    def __init__(self, stages=None):
        """Initialize mock with stage data."""
        self._stages = stages or {}
        self.saved_stages = []

    def find_by_job_and_name(self, job_id, stage_name):
        """Return mock stage by name."""
        return self._stages.get(stage_name.value)

    def save(self, stage):
        """Save stage."""
        self.saved_stages.append(stage)


class MockAuditRepository:
    """Mock audit repository."""

    def __init__(self):
        """Initialize mock."""
        self.saved_events = []

    def save(self, event):
        """Save audit event."""
        self.saved_events.append(event)


class MockQueueService:
    """Mock playbook queue request service."""

    def __init__(self):
        """Initialize mock."""
        self.submitted_requests = []

    def submit_request(self, request, correlation_id):
        """Submit request."""
        self.submitted_requests.append((request, correlation_id))


class MockUUIDGenerator:
    """Mock UUID generator."""

    def __init__(self):
        """Initialize mock."""

    def generate(self):
        """Generate mock UUID."""
        return uuid.uuid4()


class TestCreateRestartUseCase:
    """Test cases for CreateRestartUseCase."""

    @pytest.fixture
    def job_id(self):
        """Generate a valid job ID."""
        return JobId(_uuid())

    @pytest.fixture
    def client_id(self):
        """Generate a valid client ID."""
        return ClientId("test-client")

    @pytest.fixture
    def correlation_id(self):
        """Generate a valid correlation ID."""
        return CorrelationId(_uuid())

    @pytest.fixture
    def mock_job(self, client_id):
        """Create a mock job."""
        job = type('Job', (), {})()
        job.client_id = client_id
        job.tombstoned = False
        job.parameters = {}
        return job

    @pytest.fixture
    def mock_job_with_image_group(self, client_id):
        """Create a mock job with image_group_id in parameters."""
        job = type('Job', (), {})()
        job.client_id = client_id
        job.tombstoned = False
        job.parameters = {"image_group_id": "img-group-123"}
        return job

    @pytest.fixture
    def restart_stage(self, job_id):
        """Create a PENDING restart stage."""
        return Stage(
            job_id=job_id,
            stage_name=StageName(StageType.RESTART.value),
        )

    @pytest.fixture
    def completed_restart_stage(self, job_id):
        """Create a COMPLETED restart stage."""
        stage = Stage(
            job_id=job_id,
            stage_name=StageName(StageType.RESTART.value),
        )
        stage.start()
        stage.complete()
        return stage

    @pytest.fixture
    def in_progress_restart_stage(self, job_id):
        """Create an IN_PROGRESS restart stage."""
        stage = Stage(
            job_id=job_id,
            stage_name=StageName(StageType.RESTART.value),
        )
        stage.start()
        return stage

    @pytest.fixture
    def use_case(self, mock_job, job_id, restart_stage):
        """Create use case for tests."""
        stages = {
            StageType.RESTART.value: restart_stage,
        }
        return CreateRestartUseCase(
            job_repo=MockJobRepository(job=mock_job),
            stage_repo=MockStageRepository(stages=stages),
            audit_repo=MockAuditRepository(),
            queue_service=MockQueueService(),
            uuid_generator=MockUUIDGenerator(),
        )

    def test_execute_success(self, use_case, job_id, client_id, correlation_id):
        """Test successful restart execution."""
        command = CreateRestartCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
        )

        result = use_case.execute(command)

        assert result.job_id == str(job_id)
        assert result.stage_name == StageType.RESTART.value
        assert result.status == "accepted"
        assert result.correlation_id == str(correlation_id)

    def test_execute_success_with_image_group_id(
        self, mock_job_with_image_group, job_id, client_id, correlation_id, restart_stage,
    ):
        """Test successful restart execution returns image_group_id from job params."""
        stages = {
            StageType.RESTART.value: restart_stage,
        }
        use_case = CreateRestartUseCase(
            job_repo=MockJobRepository(job=mock_job_with_image_group),
            stage_repo=MockStageRepository(stages=stages),
            audit_repo=MockAuditRepository(),
            queue_service=MockQueueService(),
            uuid_generator=MockUUIDGenerator(),
        )

        command = CreateRestartCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
        )

        result = use_case.execute(command)

        assert result.image_group_id == "img-group-123"

    def test_execute_success_empty_image_group_id(
        self, use_case, job_id, client_id, correlation_id,
    ):
        """Test that image_group_id defaults to empty when not in job params."""
        command = CreateRestartCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
        )

        result = use_case.execute(command)

        assert result.image_group_id == ""

    def test_execute_job_not_found(self, job_id, client_id, correlation_id):
        """Test execution when job is not found."""
        use_case = CreateRestartUseCase(
            job_repo=MockJobRepository(job=None),
            stage_repo=MockStageRepository(),
            audit_repo=MockAuditRepository(),
            queue_service=MockQueueService(),
            uuid_generator=MockUUIDGenerator(),
        )

        command = CreateRestartCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
        )

        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_execute_job_tombstoned(self, job_id, client_id, correlation_id):
        """Test execution when job is tombstoned."""
        job = type('Job', (), {})()
        job.client_id = client_id
        job.tombstoned = True
        job.parameters = {}

        use_case = CreateRestartUseCase(
            job_repo=MockJobRepository(job=job),
            stage_repo=MockStageRepository(),
            audit_repo=MockAuditRepository(),
            queue_service=MockQueueService(),
            uuid_generator=MockUUIDGenerator(),
        )

        command = CreateRestartCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
        )

        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_execute_client_mismatch(self, mock_job, job_id, correlation_id, restart_stage):
        """Test execution when client ID does not match."""
        different_client = ClientId("different-client")
        stages = {
            StageType.RESTART.value: restart_stage,
        }
        use_case = CreateRestartUseCase(
            job_repo=MockJobRepository(job=mock_job),
            stage_repo=MockStageRepository(stages=stages),
            audit_repo=MockAuditRepository(),
            queue_service=MockQueueService(),
            uuid_generator=MockUUIDGenerator(),
        )

        command = CreateRestartCommand(
            job_id=job_id,
            client_id=different_client,
            correlation_id=correlation_id,
        )

        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_execute_stage_not_found(
        self, mock_job, job_id, client_id, correlation_id,
    ):
        """Test execution when restart stage is not found."""
        use_case = CreateRestartUseCase(
            job_repo=MockJobRepository(job=mock_job),
            stage_repo=MockStageRepository(stages={}),
            audit_repo=MockAuditRepository(),
            queue_service=MockQueueService(),
            uuid_generator=MockUUIDGenerator(),
        )

        command = CreateRestartCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
        )

        with pytest.raises(StageNotFoundError):
            use_case.execute(command)

    def test_execute_stage_already_completed(
        self, mock_job, job_id, client_id, correlation_id, completed_restart_stage,
    ):
        """Test execution when stage is in terminal COMPLETED state."""
        stages = {
            StageType.RESTART.value: completed_restart_stage,
        }
        use_case = CreateRestartUseCase(
            job_repo=MockJobRepository(job=mock_job),
            stage_repo=MockStageRepository(stages=stages),
            audit_repo=MockAuditRepository(),
            queue_service=MockQueueService(),
            uuid_generator=MockUUIDGenerator(),
        )

        command = CreateRestartCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
        )

        with pytest.raises(TerminalStateViolationError):
            use_case.execute(command)

    def test_execute_stage_already_in_progress(
        self, mock_job, job_id, client_id, correlation_id, in_progress_restart_stage,
    ):
        """Test execution when stage is already IN_PROGRESS."""
        stages = {
            StageType.RESTART.value: in_progress_restart_stage,
        }
        use_case = CreateRestartUseCase(
            job_repo=MockJobRepository(job=mock_job),
            stage_repo=MockStageRepository(stages=stages),
            audit_repo=MockAuditRepository(),
            queue_service=MockQueueService(),
            uuid_generator=MockUUIDGenerator(),
        )

        command = CreateRestartCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
        )

        with pytest.raises(InvalidStateTransitionError):
            use_case.execute(command)

    def test_execute_emits_audit_event(self, use_case, job_id, client_id, correlation_id):
        """Test that execution emits STAGE_STARTED audit event."""
        command = CreateRestartCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
        )

        use_case.execute(command)

        assert len(use_case._audit_repo.saved_events) == 1
        event = use_case._audit_repo.saved_events[0]
        assert event.event_type == "STAGE_STARTED"
        assert event.details["stage_name"] == StageType.RESTART.value

    def test_execute_submits_to_queue(self, use_case, job_id, client_id, correlation_id):
        """Test that execution submits request to queue."""
        command = CreateRestartCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
        )

        use_case.execute(command)

        assert len(use_case._queue_service.submitted_requests) == 1
        request, corr_id = use_case._queue_service.submitted_requests[0]
        assert isinstance(request, PlaybookRequest)
        assert request.job_id == str(job_id)
        assert request.stage_name == StageType.RESTART.value
        assert request.playbook_path.value == "set_pxe_boot.yml"
        assert request.extra_vars.values == {}
        assert request.timeout.minutes == 30
        assert corr_id == str(correlation_id)

    def test_execute_starts_stage(self, use_case, job_id, client_id, correlation_id):
        """Test that execution transitions stage to IN_PROGRESS."""
        command = CreateRestartCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
        )

        use_case.execute(command)

        assert len(use_case._stage_repo.saved_stages) >= 1
        saved_stage = use_case._stage_repo.saved_stages[0]
        assert saved_stage.stage_state == StageState.IN_PROGRESS

    def test_execute_response_has_submitted_at(self, use_case, job_id, client_id, correlation_id):
        """Test that response includes a submitted_at timestamp."""
        command = CreateRestartCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
        )

        result = use_case.execute(command)

        assert result.submitted_at is not None
        assert "Z" in result.submitted_at
