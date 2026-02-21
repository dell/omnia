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

import pytest

from core.build_image.exceptions import InventoryHostMissingError
from core.build_image.services import BuildImageConfigService, BuildImageQueueService
from core.build_image.value_objects import Architecture, ImageKey, FunctionalGroups, InventoryHost
from core.jobs.entities import AuditEvent, Stage
from core.jobs.exceptions import JobNotFoundError, InvalidStateTransitionError
from core.jobs.value_objects import ClientId, CorrelationId, JobId, StageName, StageType
from orchestrator.build_image.commands import CreateBuildImageCommand
from orchestrator.build_image.use_cases import CreateBuildImageUseCase
from tests.unit.core.build_image.test_entities import BuildImageRequest


class MockJobRepository:
    """Mock job repository."""

    def __init__(self, job=None, is_tombstoned=False, wrong_client=False):
        """Initialize mock with job data."""
        self.job = job
        self.is_tombstoned = is_tombstoned
        self.wrong_client = wrong_client

    def find_by_id(self, job_id):
        """Return mock job or None."""
        if self.is_tombstoned:
            mock_job = self.job
            mock_job.tombstoned = True
            return mock_job
        if self.wrong_client:
            return None
        return self.job


class MockStageRepository:
    """Mock stage repository."""

    def __init__(self, stage=None, should_fail=False):
        """Initialize mock with stage data."""
        self.stage = stage
        self.should_fail = should_fail
        self.saved_stages = []

    def find_by_job_and_name(self, job_id, stage_name):
        """Return mock stage or None."""
        if self.should_fail:
            return None
        return self.stage

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


class MockUUIDGenerator:
    """Mock UUID generator."""

    def __init__(self, uuid_value="mock-uuid-123"):
        """Initialize mock with fixed UUID."""
        self.uuid_value = uuid_value

    def generate(self):
        """Generate mock UUID."""
        return self.uuid_value


class TestCreateBuildImageUseCase:
    """Test cases for CreateBuildImageUseCase."""

    @pytest.fixture
    def mock_job(self):
        """Create a mock job."""
        job = type('Job', ())()
        job.client_id = ClientId("client-123")
        job.tombstoned = False
        return job

    @pytest.fixture
    def mock_stage(self):
        """Create a mock stage."""
        stage = Stage(
            job_id=JobId("job-123"),
            stage_name=StageName(StageType.BUILD_IMAGE.value),
            status="PENDING"
        )
        return stage

    @pytest.fixture
    def use_case(self, mock_job, mock_stage):
        """Create use case with mock dependencies."""
        job_repo = MockJobRepository(job=mock_job)
        stage_repo = MockStageRepository(stage=mock_stage)
        audit_repo = MockAuditRepository()
        config_service = MockConfigService()
        queue_service = MockQueueService()
        uuid_generator = MockUUIDGenerator()
        
        return CreateBuildImageUseCase(
            job_repo=job_repo,
            stage_repo=stage_repo,
            audit_repo=audit_repo,
            config_service=config_service,
            queue_service=queue_service,
            uuid_generator=uuid_generator,
        )

    def test_execute_success_x86_64(self, use_case):
        """Test successful execution for x86_64."""
        command = CreateBuildImageCommand(
            job_id=JobId("job-123"),
            client_id=ClientId("client-123"),
            correlation_id=CorrelationId("corr-456"),
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1", "group2"],
        )
        
        result = use_case.execute(command)
        
        assert result.job_id == "job-123"
        assert result.stage_name == "build-image"
        assert result.status == "accepted"
        assert result.architecture == "x86_64"
        assert result.image_key == "test-image"
        assert result.functional_groups == ["group1", "group2"]
        assert result.correlation_id == "corr-456"

    def test_execute_success_aarch64_with_host(self, use_case):
        """Test successful execution for aarch64 with inventory host."""
        # Update config service to return inventory host
        use_case._config_service = MockConfigService(
            inventory_host=InventoryHost("192.168.1.100")
        )
        
        command = CreateBuildImageCommand(
            job_id=JobId("job-123"),
            client_id=ClientId("client-123"),
            correlation_id=CorrelationId("corr-456"),
            architecture="aarch64",
            image_key="test-image",
            functional_groups=["group1"],
        )
        
        result = use_case.execute(command)
        
        assert result.architecture == "aarch64"
        assert result.functional_groups == ["group1"]

    def test_execute_job_not_found(self, mock_stage):
        """Test execution when job is not found."""
        job_repo = MockJobRepository(job=None)
        stage_repo = MockStageRepository(stage=mock_stage)
        audit_repo = MockAuditRepository()
        config_service = MockConfigService()
        queue_service = MockQueueService()
        uuid_generator = MockUUIDGenerator()
        
        use_case = CreateBuildImageUseCase(
            job_repo=job_repo,
            stage_repo=stage_repo,
            audit_repo=audit_repo,
            config_service=config_service,
            queue_service=queue_service,
            uuid_generator=uuid_generator,
        )
        
        command = CreateBuildImageCommand(
            job_id=JobId("job-123"),
            client_id=ClientId("client-123"),
            correlation_id=CorrelationId("corr-456"),
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1"],
        )
        
        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_execute_stage_not_found(self, mock_job):
        """Test execution when stage is not found."""
        job_repo = MockJobRepository(job=mock_job)
        stage_repo = MockStageRepository(stage=None, should_fail=True)
        audit_repo = MockAuditRepository()
        config_service = MockConfigService()
        queue_service = MockQueueService()
        uuid_generator = MockUUIDGenerator()
        
        use_case = CreateBuildImageUseCase(
            job_repo=job_repo,
            stage_repo=stage_repo,
            audit_repo=audit_repo,
            config_service=config_service,
            queue_service=queue_service,
            uuid_generator=uuid_generator,
        )
        
        command = CreateBuildImageCommand(
            job_id=JobId("job-123"),
            client_id=ClientId("client-123"),
            correlation_id=CorrelationId("corr-456"),
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1"],
        )
        
        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_execute_invalid_architecture(self, use_case):
        """Test execution with invalid architecture."""
        command = CreateBuildImageCommand(
            job_id=JobId("job-123"),
            client_id=ClientId("client-123"),
            correlation_id=CorrelationId("corr-456"),
            architecture="invalid",
            image_key="test-image",
            functional_groups=["group1"],
        )
        
        with pytest.raises(Exception):  # Should raise InvalidArchitectureError
            use_case.execute(command)

    def test_execute_aarch64_missing_inventory_host(self, use_case):
        """Test aarch64 execution with missing inventory host."""
        # Update config service to return None
        use_case._config_service = MockConfigService(inventory_host=None)
        
        command = CreateBuildImageCommand(
            job_id=JobId("job-123"),
            client_id=ClientId("client-123"),
            correlation_id=CorrelationId("corr-456"),
            architecture="aarch64",
            image_key="test-image",
            functional_groups=["group1"],
        )
        
        with pytest.raises(InventoryHostMissingError):
            use_case.execute(command)
        
        # Check that stage was marked as failed
        assert len(use_case._stage_repo.saved_stages) == 1
        failed_stage = use_case._stage_repo.saved_stages[0]
        assert failed_stage.status == "FAILED"

    def test_execute_emits_audit_event(self, use_case):
        """Test that execution emits audit event."""
        command = CreateBuildImageCommand(
            job_id=JobId("job-123"),
            client_id=ClientId("client-123"),
            correlation_id=CorrelationId("corr-456"),
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1"],
        )
        
        use_case.execute(command)
        
        assert len(use_case._audit_repo.saved_events) == 1
        event = use_case._audit_repo.saved_events[0]
        assert event.job_id == JobId("job-123")
        assert event.event_type == "STAGE_STARTED"
        assert event.correlation_id == CorrelationId("corr-456")
        assert event.details["stage_name"] == "build-image"
        assert event.details["architecture"] == "x86_64"
        assert event.details["image_key"] == "test-image"

    def test_execute_submits_to_queue(self, use_case):
        """Test that execution submits request to queue."""
        command = CreateBuildImageCommand(
            job_id=JobId("job-123"),
            client_id=ClientId("client-123"),
            correlation_id=CorrelationId("corr-456"),
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1"],
        )
        
        use_case.execute(command)
        
        assert len(use_case._queue_service.submitted_requests) == 1
        request, correlation_id = use_case._queue_service.submitted_requests[0]
        assert isinstance(request, BuildImageRequest)
        assert request.job_id == "job-123"
        assert request.architecture == Architecture("x86_64")
        assert correlation_id == "corr-456"

    def test_execute_starts_stage(self, use_case):
        """Test that execution starts the stage."""
        command = CreateBuildImageCommand(
            job_id=JobId("job-123"),
            client_id=ClientId("client-123"),
            correlation_id=CorrelationId("corr-456"),
            architecture="x86_64",
            image_key="test-image",
            functional_groups=["group1"],
        )
        
        use_case.execute(command)
        
        assert len(use_case._stage_repo.saved_stages) == 1
        stage = use_case._stage_repo.saved_stages[0]
        assert stage.status == "STARTED"
