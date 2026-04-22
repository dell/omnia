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

"""Unit tests for Deploy use case."""

import uuid
from datetime import datetime, timezone

import pytest

from core.image_group.entities import ImageGroup, Image
from core.image_group.value_objects import ImageGroupId, ImageGroupStatus
from core.image_group.exceptions import (
    ImageGroupNotFoundError,
    ImageGroupMismatchError,
    InvalidStateTransitionError as IGInvalidStateTransitionError,
)
from core.jobs.entities.job import Job
from core.jobs.entities.stage import Stage
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
from core.deploy.exceptions import DeployExecutionError
from orchestrator.deploy.commands.deploy_command import DeployCommand
from orchestrator.deploy.use_cases.deploy_use_case import DeployUseCase


def _uuid():
    return str(uuid.uuid4())


class MockJobRepo:
    """Mock job repository."""

    def __init__(self):
        self._jobs = {}

    def save(self, job):
        self._jobs[str(job.job_id)] = job

    def find_by_id(self, job_id):
        key = str(job_id) if not isinstance(job_id, str) else job_id
        return self._jobs.get(key)

    def exists(self, job_id):
        key = str(job_id) if not isinstance(job_id, str) else job_id
        return key in self._jobs


class MockStageRepo:
    """Mock stage repository."""

    def __init__(self):
        self._stages = {}

    def save(self, stage):
        key = f"{stage.job_id}/{stage.stage_name}"
        self._stages[key] = stage

    def find_by_job_and_name(self, job_id, stage_name):
        key = f"{job_id}/{stage_name}"
        return self._stages.get(key)

    def find_all_by_job(self, job_id):
        return [s for k, s in self._stages.items() if k.startswith(str(job_id))]


class MockAuditRepo:
    """Mock audit event repository."""

    def __init__(self):
        self.events = []

    def save(self, event):
        self.events.append(event)

    def find_by_job(self, job_id):
        return [e for e in self.events if str(e.job_id) == str(job_id)]


class MockUUIDGenerator:
    """Mock UUID generator."""

    def __init__(self):
        self._counter = 0

    def generate(self):
        self._counter += 1
        return uuid.UUID(int=self._counter)


class MockQueueService:
    """Mock queue service."""

    def __init__(self, should_fail=False):
        self.submitted = []
        self._should_fail = should_fail

    def submit_request(self, request, correlation_id):
        if self._should_fail:
            raise RuntimeError("Queue unavailable")
        self.submitted.append(request)


class MockImageGroupRepo:
    """Mock ImageGroup repository."""

    def __init__(self):
        self._groups = {}

    def save(self, ig):
        self._groups[str(ig.job_id)] = ig

    def find_by_job_id(self, job_id):
        return self._groups.get(str(job_id))

    def find_by_job_id_for_update(self, job_id):
        return self.find_by_job_id(job_id)

    def update_status(self, image_group_id, new_status):
        for ig in self._groups.values():
            if str(ig.id) == str(image_group_id):
                ig.status = new_status

    def exists(self, image_group_id):
        return any(str(ig.id) == str(image_group_id) for ig in self._groups.values())


def _make_job(job_id, client_id):
    """Create a test Job entity."""
    job = Job(
        job_id=job_id,
        client_id=client_id,
        request_client_id=str(client_id),
        job_state=JobState.IN_PROGRESS,
    )
    return job


def _make_stage(job_id, stage_type, state=StageState.PENDING):
    """Create a test Stage entity."""
    return Stage(
        job_id=job_id,
        stage_name=StageName(stage_type.value),
        stage_state=state,
        attempt=1,
    )


def _make_image_group(job_id, ig_id="test-cluster-v1", status=ImageGroupStatus.BUILT):
    """Create a test ImageGroup entity."""
    now = datetime.now(timezone.utc)
    return ImageGroup(
        id=ImageGroupId(ig_id),
        job_id=job_id,
        status=status,
        images=[],
        created_at=now,
        updated_at=now,
    )


def _make_command(job_id, client_id=None, image_group_id="test-cluster-v1"):
    """Create a DeployCommand."""
    return DeployCommand(
        job_id=job_id,
        client_id=client_id or ClientId("test-client"),
        correlation_id=CorrelationId(_uuid()),
        image_group_id=ImageGroupId(image_group_id),
    )


def _build_use_case(job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen):
    return DeployUseCase(
        job_repo=job_repo,
        stage_repo=stage_repo,
        audit_repo=audit_repo,
        image_group_repo=ig_repo,
        queue_service=queue_service,
        uuid_generator=uuid_gen,
    )


class TestDeployUseCase:
    """Tests for DeployUseCase."""

    @pytest.fixture
    def job_repo(self):
        return MockJobRepo()

    @pytest.fixture
    def stage_repo(self):
        return MockStageRepo()

    @pytest.fixture
    def audit_repo(self):
        return MockAuditRepo()

    @pytest.fixture
    def ig_repo(self):
        return MockImageGroupRepo()

    @pytest.fixture
    def queue_service(self):
        return MockQueueService()

    @pytest.fixture
    def uuid_gen(self):
        return MockUUIDGenerator()

    def test_execute_success(self, job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen):
        """Successful deploy returns accepted response."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        job = _make_job(job_id, client_id)
        job_repo.save(job)

        # Upstream build-image completed
        build_stage = _make_stage(job_id, StageType.BUILD_IMAGE_X86_64, StageState.COMPLETED)
        stage_repo.save(build_stage)

        # Deploy stage pending
        deploy_stage = _make_stage(job_id, StageType.DEPLOY, StageState.PENDING)
        stage_repo.save(deploy_stage)

        # ImageGroup in BUILT status
        ig = _make_image_group(job_id)
        ig_repo.save(ig)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen)
        result = use_case.execute(command)

        assert result.job_id == str(job_id)
        assert result.stage_name == "deploy"
        assert result.status == "accepted"
        assert result.image_group_id == "test-cluster-v1"
        assert len(queue_service.submitted) == 1
        assert len(audit_repo.events) == 1

    def test_execute_job_not_found(self, job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen):
        """Raises JobNotFoundError when job doesn't exist."""
        command = _make_command(job_id=JobId(_uuid()))
        use_case = _build_use_case(job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen)

        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_execute_client_mismatch(self, job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen):
        """Raises JobNotFoundError when client doesn't own job."""
        job_id = JobId(_uuid())
        job = _make_job(job_id, ClientId("owner-client"))
        job_repo.save(job)

        command = _make_command(job_id=job_id, client_id=ClientId("other-client"))
        use_case = _build_use_case(job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen)

        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_upstream_build_not_completed(self, job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen):
        """Raises UpstreamStageNotCompletedError when no build stage completed."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        job = _make_job(job_id, client_id)
        job_repo.save(job)

        # Build stage only pending, not completed
        build_stage = _make_stage(job_id, StageType.BUILD_IMAGE_X86_64, StageState.PENDING)
        stage_repo.save(build_stage)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen)

        with pytest.raises(UpstreamStageNotCompletedError):
            use_case.execute(command)

    def test_image_group_not_found(self, job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen):
        """Raises ImageGroupNotFoundError when no ImageGroup exists for job."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        job = _make_job(job_id, client_id)
        job_repo.save(job)

        build_stage = _make_stage(job_id, StageType.BUILD_IMAGE_X86_64, StageState.COMPLETED)
        stage_repo.save(build_stage)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen)

        with pytest.raises(ImageGroupNotFoundError):
            use_case.execute(command)

    def test_image_group_id_mismatch(self, job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen):
        """Raises ImageGroupMismatchError when supplied ID doesn't match."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        job = _make_job(job_id, client_id)
        job_repo.save(job)

        build_stage = _make_stage(job_id, StageType.BUILD_IMAGE_X86_64, StageState.COMPLETED)
        stage_repo.save(build_stage)

        ig = _make_image_group(job_id, ig_id="actual-cluster-v1")
        ig_repo.save(ig)

        command = _make_command(job_id=job_id, client_id=client_id, image_group_id="wrong-cluster-v1")
        use_case = _build_use_case(job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen)

        with pytest.raises(ImageGroupMismatchError):
            use_case.execute(command)

    def test_image_group_wrong_status(self, job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen):
        """Raises InvalidStateTransitionError when status is PASSED or CLEANED (requires fresh build)."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        job = _make_job(job_id, client_id)
        job_repo.save(job)

        build_stage = _make_stage(job_id, StageType.BUILD_IMAGE_X86_64, StageState.COMPLETED)
        stage_repo.save(build_stage)

        ig = _make_image_group(job_id, status=ImageGroupStatus.PASSED)
        ig_repo.save(ig)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen)

        with pytest.raises(IGInvalidStateTransitionError):
            use_case.execute(command)

    def test_deploy_retry_with_failed_stage_succeeds(self, job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen):
        """Deploy stage in FAILED state should be reset and retried successfully."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        job = _make_job(job_id, client_id)
        job_repo.save(job)

        build_stage = _make_stage(job_id, StageType.BUILD_IMAGE_X86_64, StageState.COMPLETED)
        stage_repo.save(build_stage)

        deploy_stage = _make_stage(job_id, StageType.DEPLOY, StageState.FAILED)
        stage_repo.save(deploy_stage)

        ig = _make_image_group(job_id, status=ImageGroupStatus.FAILED)
        ig_repo.save(ig)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen)
        use_case.execute(command)

        saved_stage = stage_repo.find_by_job_and_name(job_id, StageName(StageType.DEPLOY.value))
        assert saved_stage.stage_state == StageState.IN_PROGRESS
        assert len(queue_service.submitted) == 1

    def test_transitions_image_group_to_deploying(self, job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen):
        """ImageGroup status transitions to DEPLOYING on start."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        job = _make_job(job_id, client_id)
        job_repo.save(job)

        build_stage = _make_stage(job_id, StageType.BUILD_IMAGE_X86_64, StageState.COMPLETED)
        stage_repo.save(build_stage)
        deploy_stage = _make_stage(job_id, StageType.DEPLOY, StageState.PENDING)
        stage_repo.save(deploy_stage)

        ig = _make_image_group(job_id)
        ig_repo.save(ig)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen)
        use_case.execute(command)

        updated_ig = ig_repo.find_by_job_id(job_id)
        assert updated_ig.status == ImageGroupStatus.DEPLOYING

    def test_submits_provision_playbook(self, job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen):
        """Submits provision.yml playbook to queue."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        job = _make_job(job_id, client_id)
        job_repo.save(job)

        build_stage = _make_stage(job_id, StageType.BUILD_IMAGE_X86_64, StageState.COMPLETED)
        stage_repo.save(build_stage)
        deploy_stage = _make_stage(job_id, StageType.DEPLOY, StageState.PENDING)
        stage_repo.save(deploy_stage)

        ig = _make_image_group(job_id)
        ig_repo.save(ig)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen)
        use_case.execute(command)

        assert len(queue_service.submitted) == 1
        submitted = queue_service.submitted[0]
        assert str(submitted.playbook_path) == "provision.yml"
        assert submitted.extra_vars.to_dict()["image_group_id"] == "test-cluster-v1"

    def test_emits_audit_event(self, job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen):
        """Emits STAGE_STARTED audit event."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        job = _make_job(job_id, client_id)
        job_repo.save(job)

        build_stage = _make_stage(job_id, StageType.BUILD_IMAGE_X86_64, StageState.COMPLETED)
        stage_repo.save(build_stage)
        deploy_stage = _make_stage(job_id, StageType.DEPLOY, StageState.PENDING)
        stage_repo.save(deploy_stage)

        ig = _make_image_group(job_id)
        ig_repo.save(ig)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen)
        use_case.execute(command)

        assert len(audit_repo.events) == 1
        assert audit_repo.events[0].event_type == "STAGE_STARTED"
        assert audit_repo.events[0].details["stage_name"] == "deploy"

    def test_queue_failure_raises_execution_error(self, job_repo, stage_repo, audit_repo, ig_repo, uuid_gen):
        """Raises ValidationExecutionError when queue submission fails."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        job = _make_job(job_id, client_id)
        job_repo.save(job)

        build_stage = _make_stage(job_id, StageType.BUILD_IMAGE_X86_64, StageState.COMPLETED)
        stage_repo.save(build_stage)
        deploy_stage = _make_stage(job_id, StageType.DEPLOY, StageState.PENDING)
        stage_repo.save(deploy_stage)

        ig = _make_image_group(job_id)
        ig_repo.save(ig)

        failing_queue = MockQueueService(should_fail=True)
        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(job_repo, stage_repo, audit_repo, ig_repo, failing_queue, uuid_gen)

        with pytest.raises(DeployExecutionError):
            use_case.execute(command)

    def test_aarch64_upstream_accepted(self, job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen):
        """Accepts when aarch64 build stage is completed instead of x86_64."""
        job_id = JobId(_uuid())
        client_id = ClientId("test-client")
        job = _make_job(job_id, client_id)
        job_repo.save(job)

        build_stage = _make_stage(job_id, StageType.BUILD_IMAGE_AARCH64, StageState.COMPLETED)
        stage_repo.save(build_stage)
        deploy_stage = _make_stage(job_id, StageType.DEPLOY, StageState.PENDING)
        stage_repo.save(deploy_stage)

        ig = _make_image_group(job_id)
        ig_repo.save(ig)

        command = _make_command(job_id=job_id, client_id=client_id)
        use_case = _build_use_case(job_repo, stage_repo, audit_repo, ig_repo, queue_service, uuid_gen)
        result = use_case.execute(command)

        assert result.status == "accepted"
