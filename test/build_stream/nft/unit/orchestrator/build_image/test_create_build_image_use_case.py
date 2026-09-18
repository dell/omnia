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

"""Unit tests for CreateBuildImageUseCase."""

import uuid

import pytest

from core.build_image.entities import BuildImageRequest
from core.build_image.exceptions import InventoryHostMissingError
from core.build_image.value_objects import Architecture, InventoryHost
from core.jobs.entities import Stage
from core.jobs.exceptions import JobNotFoundError
from core.jobs.value_objects import (
    ClientId, CorrelationId, JobId, StageName, StageState, StageType,
)
from orchestrator.build_image.commands import CreateBuildImageCommand
from orchestrator.build_image.use_cases import CreateBuildImageUseCase


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


class MockConfigService:
    """Mock build image config service."""

    def __init__(self, inventory_host=None, should_fail=False):
        """Initialize mock."""
        self.inventory_host = inventory_host
        self.should_fail = should_fail

    def get_inventory_host(self, job_id, architecture, correlation_id):
        """Return inventory host or raise error."""
        if self.should_fail:
            raise InventoryHostMissingError("Config error", correlation_id)
        return self.inventory_host


class MockQueueService:
    """Mock build image queue service."""

    def __init__(self):
        """Initialize mock."""
        self.submitted_requests = []

    def submit_request(self, request, correlation_id):
        """Submit request."""
        self.submitted_requests.append((request, correlation_id))


class MockInventoryRepo:
    """Mock inventory repository."""

    def __init__(self):
        """Initialize mock."""
        self.created_files = []

    def create_inventory_file(self, inventory_host, job_id):
        """Create mock inventory file."""
        self.created_files.append((inventory_host, job_id))
        return f"/opt/omnia/build_stream_inv/{job_id}/inventory"


class MockUUIDGenerator:
    """Mock UUID generator."""

    def __init__(self):
        """Initialize mock."""

    def generate(self):
        """Generate mock UUID."""
        return uuid.uuid4()


class TestCreateBuildImageUseCase:
    """Test cases for CreateBuildImageUseCase."""

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
        return job

    @pytest.fixture
    def x86_stage(self, job_id):
        """Create a PENDING build-image-x86_64 stage."""
        return Stage(
            job_id=job_id,
            stage_name=StageName(StageType.BUILD_IMAGE_X86_64.value),
        )

    @pytest.fixture
    def aarch64_stage(self, job_id):
        """Create a PENDING build-image-aarch64 stage."""
        return Stage(
            job_id=job_id,
            stage_name=StageName(StageType.BUILD_IMAGE_AARCH64.value),
        )

    @pytest.fixture
    def upstream_completed_stage(self, job_id):
        """Create a COMPLETED create-local-repository stage."""
        stage = Stage(
            job_id=job_id,
            stage_name=StageName(StageType.CREATE_LOCAL_REPOSITORY.value),
        )
        stage.start()
        stage.complete()
        return stage

    @pytest.fixture
    def use_case_x86(self, mock_job, job_id, x86_stage, upstream_completed_stage):
        """Create use case for x86_64 tests."""
        stages = {
            StageType.BUILD_IMAGE_X86_64.value: x86_stage,
            StageType.CREATE_LOCAL_REPOSITORY.value: upstream_completed_stage,
        }
        return CreateBuildImageUseCase(
            job_repo=MockJobRepository(job=mock_job),
            stage_repo=MockStageRepository(stages=stages),
            audit_repo=MockAuditRepository(),
            config_service=MockConfigService(),
            queue_service=MockQueueService(),
            inventory_repo=MockInventoryRepo(),
            uuid_generator=MockUUIDGenerator(),
        )

    def test_execute_success_x86_64(self, use_case_x86, job_id, client_id, correlation_id):
        """Test successful execution for x86_64."""
        command = CreateBuildImageCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1", "group2"],
        )

        result = use_case_x86.execute(command)

        assert result.job_id == str(job_id)
        assert result.stage_name == StageType.BUILD_IMAGE_X86_64.value
        assert result.status == "accepted"
        assert result.architecture == "x86_64"
        assert result.image_key == "test-image"
        assert result.functional_groups == ["group1", "group2"]

    def test_execute_success_aarch64_with_host(
        self, mock_job, job_id, client_id, correlation_id,
        aarch64_stage, upstream_completed_stage,
    ):
        """Test successful execution for aarch64 with inventory host."""
        stages = {
            StageType.BUILD_IMAGE_AARCH64.value: aarch64_stage,
            StageType.CREATE_LOCAL_REPOSITORY.value: upstream_completed_stage,
        }
        use_case = CreateBuildImageUseCase(
            job_repo=MockJobRepository(job=mock_job),
            stage_repo=MockStageRepository(stages=stages),
            audit_repo=MockAuditRepository(),
            config_service=MockConfigService(
                inventory_host=InventoryHost("192.168.1.100")
            ),
            queue_service=MockQueueService(),
            inventory_repo=MockInventoryRepo(),
            uuid_generator=MockUUIDGenerator(),
        )

        command = CreateBuildImageCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
            architecture="aarch64",
            image_key="test-image",
            functional_groups=["group1"],
        )

        result = use_case.execute(command)
        assert result.architecture == "aarch64"
        assert result.functional_groups == ["group1"]

    def test_execute_job_not_found(self, job_id, client_id, correlation_id):
        """Test execution when job is not found."""
        use_case = CreateBuildImageUseCase(
            job_repo=MockJobRepository(job=None),
            stage_repo=MockStageRepository(),
            audit_repo=MockAuditRepository(),
            config_service=MockConfigService(),
            queue_service=MockQueueService(),
            inventory_repo=MockInventoryRepo(),
            uuid_generator=MockUUIDGenerator(),
        )

        command = CreateBuildImageCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1"],
        )

        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_execute_stage_not_found(
        self, mock_job, job_id, client_id, correlation_id, upstream_completed_stage,
    ):
        """Test execution when stage is not found."""
        stages = {
            StageType.CREATE_LOCAL_REPOSITORY.value: upstream_completed_stage,
        }
        use_case = CreateBuildImageUseCase(
            job_repo=MockJobRepository(job=mock_job),
            stage_repo=MockStageRepository(stages=stages),
            audit_repo=MockAuditRepository(),
            config_service=MockConfigService(),
            queue_service=MockQueueService(),
            inventory_repo=MockInventoryRepo(),
            uuid_generator=MockUUIDGenerator(),
        )

        command = CreateBuildImageCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1"],
        )

        with pytest.raises(Exception):
            use_case.execute(command)

    def test_execute_invalid_architecture(self, use_case_x86, job_id, client_id, correlation_id):
        """Test execution with invalid architecture."""
        command = CreateBuildImageCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
            architecture="invalid",
            image_key="test-image",
            functional_groups=["group1"],
        )

        with pytest.raises(Exception):
            use_case_x86.execute(command)

    def test_execute_aarch64_missing_inventory_host(
        self, mock_job, job_id, client_id, correlation_id,
        aarch64_stage, upstream_completed_stage,
    ):
        """Test aarch64 execution with missing inventory host."""
        stages = {
            StageType.BUILD_IMAGE_AARCH64.value: aarch64_stage,
            StageType.CREATE_LOCAL_REPOSITORY.value: upstream_completed_stage,
        }
        use_case = CreateBuildImageUseCase(
            job_repo=MockJobRepository(job=mock_job),
            stage_repo=MockStageRepository(stages=stages),
            audit_repo=MockAuditRepository(),
            config_service=MockConfigService(should_fail=True),
            queue_service=MockQueueService(),
            inventory_repo=MockInventoryRepo(),
            uuid_generator=MockUUIDGenerator(),
        )

        command = CreateBuildImageCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
            architecture="aarch64",
            image_key="test-image",
            functional_groups=["group1"],
        )

        with pytest.raises(InventoryHostMissingError):
            use_case.execute(command)

    def test_execute_emits_audit_event(self, use_case_x86, job_id, client_id, correlation_id):
        """Test that execution emits audit event."""
        command = CreateBuildImageCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1"],
        )

        use_case_x86.execute(command)

        assert len(use_case_x86._audit_repo.saved_events) == 1
        event = use_case_x86._audit_repo.saved_events[0]
        assert event.event_type == "STAGE_STARTED"
        assert event.details["stage_name"] == StageType.BUILD_IMAGE_X86_64.value
        assert event.details["architecture"] == "x86_64"
        assert event.details["image_key"] == "test-image"

    def test_execute_submits_to_queue(self, use_case_x86, job_id, client_id, correlation_id):
        """Test that execution submits request to queue."""
        command = CreateBuildImageCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1"],
        )

        use_case_x86.execute(command)

        assert len(use_case_x86._queue_service.submitted_requests) == 1
        request, _ = use_case_x86._queue_service.submitted_requests[0]
        assert isinstance(request, BuildImageRequest)
        assert request.job_id == str(job_id)

    def test_execute_starts_stage(self, use_case_x86, job_id, client_id, correlation_id):
        """Test that execution starts the stage."""
        command = CreateBuildImageCommand(
            job_id=job_id,
            client_id=client_id,
            correlation_id=correlation_id,
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1"],
        )

        use_case_x86.execute(command)

        assert len(use_case_x86._stage_repo.saved_stages) >= 1
        saved_stage = use_case_x86._stage_repo.saved_stages[0]
        assert saved_stage.stage_state == StageState.IN_PROGRESS
