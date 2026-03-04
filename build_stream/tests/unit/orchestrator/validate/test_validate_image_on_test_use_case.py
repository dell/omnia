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

"""Unit tests for ValidateImageOnTestUseCase."""

import uuid

import pytest

from core.jobs.entities import Job, Stage
from core.jobs.exceptions import (
    JobNotFoundError,
    UpstreamStageNotCompletedError,
)
from core.jobs.value_objects import (
    ClientId,
    CorrelationId,
    JobId,
    JobState,
    StageName,
    StageState,
    StageType,
)
from core.validate.exceptions import (
    ValidationExecutionError,
)
from orchestrator.validate.commands import ValidateImageOnTestCommand
from orchestrator.validate.use_cases import ValidateImageOnTestUseCase


# --- Helpers ---

def _uuid() -> str:
    return str(uuid.uuid4())


def _make_job(job_id: JobId, client_id: ClientId) -> Job:
    job = Job(
        job_id=job_id,
        client_id=client_id,
        request_client_id="req-client-123",
        job_state=JobState.IN_PROGRESS,
    )
    return job


def _make_stage(
    job_id: JobId,
    stage_type: StageType,
    state: StageState = StageState.PENDING,
) -> Stage:
    return Stage(
        job_id=job_id,
        stage_name=StageName(stage_type.value),
        stage_state=state,
        attempt=1,
    )


def _make_command(
    job_id: JobId | None = None,
    client_id: ClientId | None = None,
) -> ValidateImageOnTestCommand:
    return ValidateImageOnTestCommand(
        job_id=job_id or JobId(_uuid()),
        client_id=client_id or ClientId("test-client"),
        correlation_id=CorrelationId(_uuid()),
        image_key="test-image",
    )


# --- Mock repositories ---

class MockJobRepo:
    """Mock job repository for testing."""
    # pylint: disable=too-few-public-methods

    def __init__(self):
        """Initialize mock job repository."""
        self._jobs = {}

    def save(self, job: Job) -> None:
        """Save job to repository."""
        self._jobs[str(job.job_id)] = job

    def find_by_id(self, job_id):
        """Find job by ID."""
        key = str(job_id) if not isinstance(job_id, str) else job_id
        return self._jobs.get(key)

    def exists(self, job_id) -> bool:
        """Check if job exists."""
        key = str(job_id) if not isinstance(job_id, str) else job_id
        return key in self._jobs


class MockStageRepo:
    """Mock stage repository for testing."""
    # pylint: disable=too-few-public-methods

    def __init__(self):
        """Initialize mock stage repository."""
        self._stages = {}

    def save(self, stage: Stage) -> None:
        """Save stage to repository."""
        key = (str(stage.job_id), str(stage.stage_name))
        self._stages[key] = stage

    def save_all(self, stages) -> None:
        """Save multiple stages."""
        for s in stages:
            self.save(s)

    def find_by_job_and_name(self, job_id, stage_name):
        """Find stage by job ID and stage name."""
        key = (str(job_id), str(stage_name))
        return self._stages.get(key)

    def find_all_by_job(self, job_id):
        """Find all stages for a job."""
        jid = str(job_id)
        return [s for k, s in self._stages.items() if k[0] == jid]


class MockAuditRepo:
    """Mock audit repository for testing."""
    # pylint: disable=too-few-public-methods

    def __init__(self):
        """Initialize mock audit repository."""
        self._events = []

    def save(self, event) -> None:
        """Save event to repository."""
        self._events.append(event)

    def find_by_job(self, job_id):
        """Find events by job ID."""
        jid = str(job_id)
        return [e for e in self._events if str(e.job_id) == jid]


class MockUUIDGenerator:
    """Mock UUID generator for testing."""
    # pylint: disable=too-few-public-methods

    def generate(self):
        """Generate a UUID."""
        return uuid.uuid4()


class MockQueueService:
    """Mock queue service for testing."""
    # pylint: disable=too-few-public-methods

    def __init__(self, should_fail: bool = False):
        """Initialize mock queue service."""
        self.submitted = []
        self.should_fail = should_fail

    def submit_request(self, request, correlation_id):
        """Submit request to queue."""
        if self.should_fail:
            raise IOError("Queue unavailable")
        self.submitted.append(request)


# --- Fixtures ---

@pytest.fixture
def job_repo():
    """Provide mock job repository."""
    return MockJobRepo()


@pytest.fixture
def stage_repo():
    """Provide mock stage repository."""
    return MockStageRepo()


@pytest.fixture
def audit_repo():
    """Provide mock audit repository."""
    return MockAuditRepo()


@pytest.fixture
def uuid_gen():
    """Provide mock UUID generator."""
    return MockUUIDGenerator()


@pytest.fixture
def queue_service():
    """Provide mock queue service."""
    return MockQueueService()


def _build_use_case(job_repo, stage_repo, audit_repo, queue_service, uuid_gen):
    """Build use case with mocked dependencies."""
    return ValidateImageOnTestUseCase(
        job_repo=job_repo,
        stage_repo=stage_repo,
        audit_repo=audit_repo,
        queue_service=queue_service,
        uuid_generator=uuid_gen,
    )


# --- Tests ---

class TestValidateImageOnTestUseCase:
    """Tests for ValidateImageOnTestUseCase."""

    def test_execute_success(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """Successful execution should submit to queue and return response."""
        # pylint: disable=too-many-arguments, redefined-outer-name
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")

        # Setup: job, validate stage, and a completed build-image stage
        job = _make_job(job_id, client_id)
        job_repo.save(job)

        validate_stage = _make_stage(job_id, StageType.VALIDATE_IMAGE_ON_TEST)
        stage_repo.save(validate_stage)

        build_stage = _make_stage(
            job_id, StageType.BUILD_IMAGE_X86_64, StageState.COMPLETED
        )
        stage_repo.save(build_stage)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )

        result = use_case.execute(command)

        assert result.job_id == str(job_id)
        assert result.stage_name == "validate-image-on-test"
        assert result.status == "accepted"
        assert len(queue_service.submitted) == 1
        assert len(audit_repo.find_by_job(job_id)) == 1

    def test_execute_with_aarch64_completed(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """Should succeed when aarch64 build stage is completed."""
        # pylint: disable=too-many-arguments, redefined-outer-name
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")

        job = _make_job(job_id, client_id)
        job_repo.save(job)

        validate_stage = _make_stage(job_id, StageType.VALIDATE_IMAGE_ON_TEST)
        stage_repo.save(validate_stage)

        build_stage = _make_stage(
            job_id, StageType.BUILD_IMAGE_AARCH64, StageState.COMPLETED
        )
        stage_repo.save(build_stage)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )

        result = use_case.execute(command)
        assert result.status == "accepted"

    def test_execute_job_not_found(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """Should raise JobNotFoundError when job does not exist."""
        # pylint: disable=too-many-arguments, redefined-outer-name
        command = _make_command()
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )

        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_execute_client_mismatch(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """Should raise JobNotFoundError when client doesn't own the job."""
        # pylint: disable=too-many-arguments, redefined-outer-name
        job_id = JobId(_uuid())
        job = _make_job(job_id, ClientId("owner-client"))
        job_repo.save(job)

        command = _make_command(job_id=job_id, client_id=ClientId("other-client"))
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )

        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_execute_stage_not_found(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """Should raise JobNotFoundError when validate stage doesn't exist."""
        # pylint: disable=too-many-arguments, redefined-outer-name
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        job = _make_job(job_id, client_id)
        job_repo.save(job)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )

        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_execute_stage_guard_violation_no_build_stages(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """Should raise UpstreamStageNotCompletedError when no build stage completed."""
        # pylint: disable=too-many-arguments, redefined-outer-name
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")

        job = _make_job(job_id, client_id)
        job_repo.save(job)

        validate_stage = _make_stage(job_id, StageType.VALIDATE_IMAGE_ON_TEST)
        stage_repo.save(validate_stage)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )

        with pytest.raises(UpstreamStageNotCompletedError):
            use_case.execute(command)

    def test_execute_stage_guard_violation_build_pending(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """Should raise UpstreamStageNotCompletedError when build stage is PENDING."""
        # pylint: disable=too-many-arguments, redefined-outer-name
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")

        job = _make_job(job_id, client_id)
        job_repo.save(job)

        validate_stage = _make_stage(job_id, StageType.VALIDATE_IMAGE_ON_TEST)
        stage_repo.save(validate_stage)

        build_stage = _make_stage(
            job_id, StageType.BUILD_IMAGE_X86_64, StageState.PENDING
        )
        stage_repo.save(build_stage)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )

        with pytest.raises(UpstreamStageNotCompletedError):
            use_case.execute(command)

    def test_execute_queue_failure(
        self, job_repo, stage_repo, audit_repo, uuid_gen
    ):
        """Should raise ValidationExecutionError when queue submission fails."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")

        job = _make_job(job_id, client_id)
        job_repo.save(job)

        validate_stage = _make_stage(job_id, StageType.VALIDATE_IMAGE_ON_TEST)
        stage_repo.save(validate_stage)

        build_stage = _make_stage(
            job_id, StageType.BUILD_IMAGE_X86_64, StageState.COMPLETED
        )
        stage_repo.save(build_stage)

        failing_queue = MockQueueService(should_fail=True)
        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, failing_queue, uuid_gen
        )

        with pytest.raises(ValidationExecutionError):
            use_case.execute(command)

        # Stage should be marked as FAILED
        saved_stage = stage_repo.find_by_job_and_name(
            job_id, StageName(StageType.VALIDATE_IMAGE_ON_TEST.value)
        )
        assert saved_stage.stage_state == StageState.FAILED

    def test_execute_emits_audit_event(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """Should emit STAGE_STARTED audit event."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")

        job = _make_job(job_id, client_id)
        job_repo.save(job)

        validate_stage = _make_stage(job_id, StageType.VALIDATE_IMAGE_ON_TEST)
        stage_repo.save(validate_stage)

        build_stage = _make_stage(
            job_id, StageType.BUILD_IMAGE_X86_64, StageState.COMPLETED
        )
        stage_repo.save(build_stage)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )
        use_case.execute(command)

        events = audit_repo.find_by_job(job_id)
        assert len(events) == 1
        assert events[0].event_type == "STAGE_STARTED"
        assert events[0].details["stage_name"] == "validate-image-on-test"

    def test_execute_starts_stage(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """Stage should transition to IN_PROGRESS after submission."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")

        job = _make_job(job_id, client_id)
        job_repo.save(job)

        validate_stage = _make_stage(job_id, StageType.VALIDATE_IMAGE_ON_TEST)
        stage_repo.save(validate_stage)

        build_stage = _make_stage(
            job_id, StageType.BUILD_IMAGE_X86_64, StageState.COMPLETED
        )
        stage_repo.save(build_stage)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )
        use_case.execute(command)

        saved_stage = stage_repo.find_by_job_and_name(
            job_id, StageName(StageType.VALIDATE_IMAGE_ON_TEST.value)
        )
        assert saved_stage.stage_state == StageState.IN_PROGRESS

    def test_execute_submits_correct_request(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """Submitted request should have correct playbook and stage name."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")

        job = _make_job(job_id, client_id)
        job_repo.save(job)

        validate_stage = _make_stage(job_id, StageType.VALIDATE_IMAGE_ON_TEST)
        stage_repo.save(validate_stage)

        build_stage = _make_stage(
            job_id, StageType.BUILD_IMAGE_X86_64, StageState.COMPLETED
        )
        stage_repo.save(build_stage)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )
        use_case.execute(command)

        assert len(queue_service.submitted) == 1
        submitted = queue_service.submitted[0]
        assert submitted.stage_name == "validate-image-on-test"
        assert str(submitted.playbook_path) == "discovery.yml"
        assert submitted.job_id == str(job_id)
