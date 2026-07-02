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

"""Unit tests for ValidateUseCase — Phase 3 (spec §7)."""

import uuid

import pytest

from core.jobs.entities import Job, Stage
from core.jobs.exceptions import (
    InvalidStateTransitionError,
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
from orchestrator.validate.commands import ValidateCommand
from orchestrator.validate.use_cases import ValidateUseCase


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
    scenario_names: list | None = None,
    test_suite: str = "",
    timeout_minutes: int = 120,
) -> ValidateCommand:
    return ValidateCommand(
        job_id=job_id or JobId(_uuid()),
        client_id=client_id or ClientId("test-client"),
        correlation_id=CorrelationId(_uuid()),
        scenario_names=scenario_names or ["all"],
        test_suite=test_suite,
        timeout_minutes=timeout_minutes,
    )


# --- Mock repositories ---

class MockJobRepo:
    """Mock job repository for testing."""

    def __init__(self):
        self._jobs = {}

    def save(self, job: Job) -> None:
        self._jobs[str(job.job_id)] = job

    def find_by_id(self, job_id):
        key = str(job_id) if not isinstance(job_id, str) else job_id
        return self._jobs.get(key)

    def exists(self, job_id) -> bool:
        key = str(job_id) if not isinstance(job_id, str) else job_id
        return key in self._jobs


class MockStageRepo:
    """Mock stage repository for testing."""

    def __init__(self):
        self._stages = {}

    def save(self, stage: Stage) -> None:
        key = (str(stage.job_id), str(stage.stage_name))
        self._stages[key] = stage

    def save_all(self, stages) -> None:
        for s in stages:
            self.save(s)

    def find_by_job_and_name(self, job_id, stage_name):
        key = (str(job_id), str(stage_name))
        return self._stages.get(key)

    def find_all_by_job(self, job_id):
        jid = str(job_id)
        return [s for k, s in self._stages.items() if k[0] == jid]


class MockAuditRepo:
    """Mock audit repository for testing."""

    def __init__(self):
        self._events = []

    def save(self, event) -> None:
        self._events.append(event)

    def find_by_job(self, job_id):
        jid = str(job_id)
        return [e for e in self._events if str(e.job_id) == jid]


class MockUUIDGenerator:
    """Mock UUID generator for testing."""

    def generate(self):
        return uuid.uuid4()


class MockQueueService:
    """Mock queue service for testing."""

    def __init__(self, should_fail: bool = False):
        self.submitted = []
        self.should_fail = should_fail

    def submit_request(self, request, correlation_id):
        if self.should_fail:
            raise IOError("Queue unavailable")
        self.submitted.append(request)


# --- Fixtures ---

@pytest.fixture
def job_repo():
    return MockJobRepo()


@pytest.fixture
def stage_repo():
    return MockStageRepo()


@pytest.fixture
def audit_repo():
    return MockAuditRepo()


@pytest.fixture
def uuid_gen():
    return MockUUIDGenerator()


@pytest.fixture
def queue_service():
    return MockQueueService()


def _build_use_case(job_repo, stage_repo, audit_repo, queue_service, uuid_gen):
    """Build use case with mocked dependencies."""
    return ValidateUseCase(
        job_repo=job_repo,
        stage_repo=stage_repo,
        audit_repo=audit_repo,
        queue_service=queue_service,
        uuid_generator=uuid_gen,
    )


def _setup_job_with_restart(job_repo, stage_repo, job_id, client_id):
    """Common setup: create job + completed restart stage."""
    job = _make_job(job_id, client_id)
    job_repo.save(job)
    restart_stage = _make_stage(job_id, StageType.RESTART, StageState.COMPLETED)
    stage_repo.save(restart_stage)


# --- Tests ---

class TestValidateUseCaseSuccess:
    """Happy-path tests for ValidateUseCase — AC-3.1, AC-3.2, AC-3.3."""

    def test_execute_success_returns_queued(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """AC-3.1: Successful execution returns QUEUED status."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        _setup_job_with_restart(job_repo, stage_repo, job_id, client_id)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )

        result = use_case.execute(command)

        assert result.job_id == str(job_id)
        assert result.stage_name == "validate"
        assert result.status == "QUEUED"
        assert result.attempt == 1
        assert result.submitted_at.endswith("Z")
        assert result.correlation_id == str(command.correlation_id)

    def test_execute_submits_test_automation_request(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """AC-3.2: Request submitted to NFS queue with command_type='test_automation'."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        _setup_job_with_restart(job_repo, stage_repo, job_id, client_id)

        command = _make_command(
            job_id=job_id,
            client_id=client_id,
            scenario_names=["discovery", "slurm"],
            test_suite="smoke",
            timeout_minutes=60,
        )
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )
        use_case.execute(command)

        assert len(queue_service.submitted) == 1
        submitted = queue_service.submitted[0]
        assert submitted.command_type == "test_automation"
        assert submitted.stage_type == "validate"
        assert submitted.scenario_names == ["discovery", "slurm"]
        assert submitted.test_suite == "smoke"
        assert submitted.timeout_minutes == 60
        assert submitted.job_id == str(job_id)
        assert submitted.config_path == "/opt/omnia/automation/omnia_test_config.yml"

    def test_execute_artifact_dir_includes_attempt(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """AC-3.3: artifact_dir follows /artifacts/{job_id}/validate/attempt_{N}/."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        _setup_job_with_restart(job_repo, stage_repo, job_id, client_id)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )
        use_case.execute(command)

        submitted = queue_service.submitted[0]
        expected_dir = f"/opt/omnia/build_stream_root/artifacts/{job_id}/validate/attempt_1"
        assert submitted.artifact_dir == expected_dir

    def test_execute_request_id_format(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """Request ID follows validate_{job_id}_{timestamp} convention."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        _setup_job_with_restart(job_repo, stage_repo, job_id, client_id)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )
        use_case.execute(command)

        submitted = queue_service.submitted[0]
        assert submitted.request_id.startswith(f"validate_{job_id}_")

    def test_execute_default_scenarios(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """Default scenario_names=['all'] when not specified."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        _setup_job_with_restart(job_repo, stage_repo, job_id, client_id)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )
        use_case.execute(command)

        submitted = queue_service.submitted[0]
        assert submitted.scenario_names == ["all"]
        assert submitted.test_suite == ""
        assert submitted.timeout_minutes == 120


class TestValidateUseCaseGuards:
    """Guard check tests — AC-3.5, AC-3.6."""

    def test_job_not_found(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """AC-3.4: Non-existent job raises JobNotFoundError."""
        command = _make_command()
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )

        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_client_mismatch(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """Client mismatch raises JobNotFoundError."""
        job_id = JobId(_uuid())
        job = _make_job(job_id, ClientId("owner-client"))
        job_repo.save(job)

        command = _make_command(job_id=job_id, client_id=ClientId("other-client"))
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )

        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_restart_stage_not_completed(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """AC-3.6: Missing/incomplete restart stage raises UpstreamStageNotCompletedError."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        job = _make_job(job_id, client_id)
        job_repo.save(job)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )

        with pytest.raises(UpstreamStageNotCompletedError):
            use_case.execute(command)

    def test_restart_stage_pending_raises(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """Restart stage in PENDING state raises UpstreamStageNotCompletedError."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        job = _make_job(job_id, client_id)
        job_repo.save(job)

        restart_stage = _make_stage(job_id, StageType.RESTART, StageState.PENDING)
        stage_repo.save(restart_stage)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )

        with pytest.raises(UpstreamStageNotCompletedError):
            use_case.execute(command)

    def test_active_validate_stage_raises_409(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """AC-3.5: Active validate stage (IN_PROGRESS) raises InvalidStateTransitionError."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        _setup_job_with_restart(job_repo, stage_repo, job_id, client_id)

        active_validate = _make_stage(job_id, StageType.VALIDATE, StageState.IN_PROGRESS)
        stage_repo.save(active_validate)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )

        with pytest.raises(InvalidStateTransitionError):
            use_case.execute(command)

    def test_pending_validate_stage_raises_409(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """Active validate stage (PENDING) raises InvalidStateTransitionError."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        _setup_job_with_restart(job_repo, stage_repo, job_id, client_id)

        pending_validate = _make_stage(job_id, StageType.VALIDATE, StageState.PENDING)
        stage_repo.save(pending_validate)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )

        with pytest.raises(InvalidStateTransitionError):
            use_case.execute(command)


class TestValidateUseCaseQueueFailure:
    """Queue failure and error handling tests — AC-3.8."""

    def test_queue_failure_raises_validation_execution_error(
        self, job_repo, stage_repo, audit_repo, uuid_gen
    ):
        """AC-3.8: Queue failure raises ValidationExecutionError."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        _setup_job_with_restart(job_repo, stage_repo, job_id, client_id)

        failing_queue = MockQueueService(should_fail=True)
        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, failing_queue, uuid_gen
        )

        with pytest.raises(ValidationExecutionError):
            use_case.execute(command)


class TestValidateUseCaseAudit:
    """Audit event tests — AC-3.7."""

    def test_emits_stage_started_event(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """AC-3.7: Should emit STAGE_STARTED audit event with scenario details."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        _setup_job_with_restart(job_repo, stage_repo, job_id, client_id)

        command = _make_command(
            job_id=job_id,
            client_id=client_id,
            scenario_names=["discovery"],
            test_suite="smoke",
        )
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )
        use_case.execute(command)

        events = audit_repo.find_by_job(job_id)
        assert len(events) == 1
        assert events[0].event_type == "STAGE_STARTED"
        assert events[0].details["stage_name"] == "validate"
        assert events[0].details["scenario_names"] == ["discovery"]
        assert events[0].details["test_suite"] == "smoke"

    def test_stage_transitions_to_in_progress(
        self, job_repo, stage_repo, audit_repo, queue_service, uuid_gen
    ):
        """Stage should transition to IN_PROGRESS after queue submission."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        _setup_job_with_restart(job_repo, stage_repo, job_id, client_id)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(
            job_repo, stage_repo, audit_repo, queue_service, uuid_gen
        )
        use_case.execute(command)

        saved_stage = stage_repo.find_by_job_and_name(
            job_id, StageName(StageType.VALIDATE.value)
        )
        assert saved_stage.stage_state == StageState.IN_PROGRESS
