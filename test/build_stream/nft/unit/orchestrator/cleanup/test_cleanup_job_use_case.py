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

"""Unit tests for CleanupJobUseCase (hard delete + automated cleanup).

Image cleanup is handled by submitting ``image_build_manager.yml
--tags cleanup_images`` to the NFS playbook queue (replacing the
earlier direct s3cmd subprocess approach).
"""

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from core.cleanup.exceptions import (
    AlreadyCleanedError,
    CleanupNfsFailedError,
    CleanupStateInvalidError,
)
from core.image_group.entities import Image, ImageGroup
from core.image_group.value_objects import (
    ImageGroupId,
    ImageGroupStatus,
)
from core.jobs.entities import Job
from core.jobs.exceptions import JobNotFoundError
from core.jobs.value_objects import (
    ClientId,
    CorrelationId,
    JobId,
)
from infra.id_generator import UUIDv4Generator
from infra.repositories.in_memory import (
    InMemoryAuditEventRepository,
    InMemoryImageGroupRepository,
    InMemoryImageRepository,
    InMemoryJobRepository,
    InMemoryStageRepository,
)
from orchestrator.cleanup.commands.cleanup_job import CleanupJobCommand
from orchestrator.cleanup.use_cases.cleanup_job import CleanupJobUseCase


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeQueueService:
    """Records queue submissions for testing."""

    def __init__(self, should_fail=False):
        self.submitted = []
        self._should_fail = should_fail

    def submit_request(self, request, correlation_id):
        if self._should_fail:
            raise RuntimeError("Queue unavailable")
        self.submitted.append(request)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _job_id() -> JobId:
    return JobId(str(uuid.uuid4()))


def _client_id() -> ClientId:
    return ClientId(str(uuid.uuid4()))


def _correlation_id() -> CorrelationId:
    return CorrelationId(str(uuid.uuid4()))


def _make_job(client: ClientId, jid: JobId) -> Job:
    return Job(
        job_id=jid,
        client_id=client,
        request_client_id=str(client),
    )


def _make_image_group(
    jid: JobId,
    image_group_id: str = "test-group",
    status: ImageGroupStatus = ImageGroupStatus.BUILT,
    image_paths=None,
) -> ImageGroup:
    paths = image_paths or [
        "s3://boot-images/slurm_node_x86_64/"
        "rhel-slurm_node_x86_64_xyz-image-build1/",
    ]
    images = [
        Image(
            id=str(uuid.uuid4()),
            image_group_id=image_group_id,
            role=f"role-{idx}",
            image_name=path,
            created_at=datetime.now(timezone.utc),
        )
        for idx, path in enumerate(paths)
    ]
    return ImageGroup(
        id=ImageGroupId(image_group_id),
        job_id=jid,
        status=status,
        images=images,
    )


def _build_use_case(
    queue_service=None,
    job_repo=None,
    stage_repo=None,
    image_group_repo=None,
    image_repo=None,
    nfs_base: str = None,
) -> CleanupJobUseCase:
    return CleanupJobUseCase(
        job_repo=job_repo or InMemoryJobRepository(),
        stage_repo=stage_repo or InMemoryStageRepository(),
        audit_repo=InMemoryAuditEventRepository(),
        image_group_repo=image_group_repo or InMemoryImageGroupRepository(),
        image_repo=image_repo or InMemoryImageRepository(),
        uuid_generator=UUIDv4Generator(),
        queue_service=queue_service,
        nfs_artifact_base=nfs_base,
    )


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestCleanupJobSuccess:
    """Verify successful manual cleanup transitions and side-effects."""

    def _setup(self, status, tmp_path):
        jid = _job_id()
        client = _client_id()

        job_repo = InMemoryJobRepository()
        job_repo.save(_make_job(client, jid))

        ig_repo = InMemoryImageGroupRepository()
        image_path = (
            "s3://boot-images/slurm_node_x86_64/"
            "rhel-slurm_node_x86_64_abc-image-build1/"
        )
        ig = _make_image_group(jid, status=status, image_paths=[image_path])
        ig_repo.save(ig)

        queue_service = FakeQueueService()

        # NFS artifact dir with one fake file
        artifact_dir = tmp_path / "artifacts" / str(jid)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "config.yml").write_text("hello", encoding="utf-8")

        use_case = _build_use_case(
            queue_service=queue_service,
            job_repo=job_repo,
            image_group_repo=ig_repo,
            nfs_base=str(tmp_path),
        )
        return use_case, jid, client, ig_repo, queue_service, artifact_dir

    @pytest.mark.parametrize(
        "status",
        [
            ImageGroupStatus.BUILT,
            ImageGroupStatus.DEPLOYED,
            ImageGroupStatus.RESTARTED,
            ImageGroupStatus.PASSED,
            ImageGroupStatus.FAILED,
        ],
    )
    def test_eligible_states_clean_successfully(self, status, tmp_path):
        uc, jid, client, ig_repo, queue_service, artifact_dir = self._setup(status, tmp_path)
        cmd = CleanupJobCommand(
            job_id=jid, client_id=client, correlation_id=_correlation_id()
        )

        result = uc.execute(cmd)

        # Cleanup playbook submission succeeded (via FakeQueueService), so
        # the ImageGroup moves to the non-terminal CLEANING state -- the
        # final CLEANED transition only happens once ResultPoller observes
        # a successful playbook result (see test_result_poller.py).
        assert result.status == ImageGroupStatus.CLEANING.value
        assert result.cleanup_type == "manual"
        assert result.nfs_files_deleted == 1
        # Cleanup playbook was submitted to queue
        assert len(queue_service.submitted) == 1
        submitted = queue_service.submitted[0]
        assert submitted.tags == "cleanup_images"
        extra_vars = submitted.extra_vars.to_dict()
        assert "cleanup_image_pattern" in extra_vars
        # skip_approval is required so the playbook's interactive
        # confirmation prompt doesn't silently skip S3/registry deletion
        # when run headlessly by the playbook watcher.
        assert extra_vars["skip_approval"] == "true"
        assert ig_repo.find_by_job_id(jid).status == ImageGroupStatus.CLEANING
        assert not artifact_dir.exists()

    def test_missing_nfs_dir_returns_zero(self, tmp_path):
        uc, jid, client, ig_repo, queue_service, artifact_dir = self._setup(
            ImageGroupStatus.BUILT, tmp_path
        )
        # Wipe the artifact dir before cleanup runs.
        for child in artifact_dir.iterdir():
            child.unlink()
        artifact_dir.rmdir()

        cmd = CleanupJobCommand(
            job_id=jid, client_id=client, correlation_id=_correlation_id()
        )
        result = uc.execute(cmd)
        assert result.nfs_files_deleted == 0
        assert ig_repo.find_by_job_id(jid).status == ImageGroupStatus.CLEANING

    def test_cleanup_without_queue_service_still_succeeds(self, tmp_path):
        """Cleanup should still proceed even if no queue service is configured."""
        jid = _job_id()
        client = _client_id()
        job_repo = InMemoryJobRepository()
        job_repo.save(_make_job(client, jid))

        ig_repo = InMemoryImageGroupRepository()
        ig = _make_image_group(jid)
        ig_repo.save(ig)

        use_case = _build_use_case(
            queue_service=None,
            job_repo=job_repo,
            image_group_repo=ig_repo,
            nfs_base=str(tmp_path),
        )

        cmd = CleanupJobCommand(
            job_id=jid, client_id=client, correlation_id=_correlation_id()
        )
        result = use_case.execute(cmd)
        assert result.status == ImageGroupStatus.CLEANED.value
        assert ig_repo.find_by_job_id(jid).status == ImageGroupStatus.CLEANED

    def test_async_cleanup_does_not_tombstone_job_yet(self, tmp_path):
        """Job tombstoning must wait for ResultPoller confirmation, not
        happen eagerly when the cleanup playbook was merely submitted."""
        uc, jid, client, ig_repo, queue_service, _artifact_dir = self._setup(
            ImageGroupStatus.BUILT, tmp_path
        )
        cmd = CleanupJobCommand(
            job_id=jid, client_id=client, correlation_id=_correlation_id()
        )
        uc.execute(cmd)

        job = uc._job_repo.find_by_id(jid)  # pylint: disable=protected-access
        assert job is not None
        assert job.tombstoned is False

    def test_sync_fallback_tombstones_job_immediately(self, tmp_path):
        """Without a queue service there's nothing to wait on, so the
        legacy synchronous CLEANED + tombstone behavior still applies."""
        jid = _job_id()
        client = _client_id()
        job_repo = InMemoryJobRepository()
        job_repo.save(_make_job(client, jid))

        ig_repo = InMemoryImageGroupRepository()
        ig_repo.save(_make_image_group(jid))

        use_case = _build_use_case(
            queue_service=None,
            job_repo=job_repo,
            image_group_repo=ig_repo,
            nfs_base=str(tmp_path),
        )
        cmd = CleanupJobCommand(
            job_id=jid, client_id=client, correlation_id=_correlation_id()
        )
        use_case.execute(cmd)

        job = job_repo.find_by_id(jid)
        assert job.tombstoned is True

    def test_cleanup_playbook_submits_image_group_id_as_pattern(self, tmp_path):
        """Verify cleanup_image_pattern extra var matches the image_group_id."""
        jid = _job_id()
        client = _client_id()
        job_repo = InMemoryJobRepository()
        job_repo.save(_make_job(client, jid))

        ig_repo = InMemoryImageGroupRepository()
        ig = _make_image_group(jid, image_group_id="my-cluster-v1")
        ig_repo.save(ig)

        queue_service = FakeQueueService()
        use_case = _build_use_case(
            queue_service=queue_service,
            job_repo=job_repo,
            image_group_repo=ig_repo,
            nfs_base=str(tmp_path),
        )

        cmd = CleanupJobCommand(
            job_id=jid, client_id=client, correlation_id=_correlation_id()
        )
        use_case.execute(cmd)

        assert len(queue_service.submitted) == 1
        submitted = queue_service.submitted[0]
        assert submitted.extra_vars.to_dict()["cleanup_image_pattern"] == "my-cluster-v1"
        assert str(submitted.playbook_path) == "image_build_manager.yml"


# ---------------------------------------------------------------------------
# Guard tests
# ---------------------------------------------------------------------------

class TestCleanupJobGuards:
    """Verify state preconditions and ownership checks."""

    def test_missing_job_raises_not_found(self, tmp_path):
        use_case = _build_use_case(nfs_base=str(tmp_path))

        cmd = CleanupJobCommand(
            job_id=_job_id(),
            client_id=_client_id(),
            correlation_id=_correlation_id(),
        )
        with pytest.raises(JobNotFoundError):
            use_case.execute(cmd)

    def test_client_mismatch_raises_not_found(self, tmp_path):
        jid = _job_id()
        owner = _client_id()
        intruder = _client_id()

        job_repo = InMemoryJobRepository()
        job_repo.save(_make_job(owner, jid))

        ig_repo = InMemoryImageGroupRepository()
        ig_repo.save(_make_image_group(jid))

        use_case = _build_use_case(
            job_repo=job_repo,
            image_group_repo=ig_repo,
            nfs_base=str(tmp_path),
        )

        cmd = CleanupJobCommand(
            job_id=jid,
            client_id=intruder,
            correlation_id=_correlation_id(),
        )
        with pytest.raises(JobNotFoundError):
            use_case.execute(cmd)

    @pytest.mark.parametrize(
        "active_status",
        [
            ImageGroupStatus.DEPLOYING,
            ImageGroupStatus.RESTARTING,
            ImageGroupStatus.VALIDATING,
        ],
    )
    def test_active_state_raises_state_invalid(self, active_status, tmp_path):
        jid = _job_id()
        client = _client_id()

        job_repo = InMemoryJobRepository()
        job_repo.save(_make_job(client, jid))

        ig_repo = InMemoryImageGroupRepository()
        ig_repo.save(_make_image_group(jid, status=active_status))

        use_case = _build_use_case(
            job_repo=job_repo,
            image_group_repo=ig_repo,
            nfs_base=str(tmp_path),
        )

        cmd = CleanupJobCommand(
            job_id=jid, client_id=client, correlation_id=_correlation_id()
        )
        with pytest.raises(CleanupStateInvalidError):
            use_case.execute(cmd)

    def test_already_cleaned_raises(self, tmp_path):
        jid = _job_id()
        client = _client_id()

        job_repo = InMemoryJobRepository()
        job_repo.save(_make_job(client, jid))

        ig_repo = InMemoryImageGroupRepository()
        ig_repo.save(
            _make_image_group(jid, status=ImageGroupStatus.CLEANED)
        )

        use_case = _build_use_case(
            job_repo=job_repo,
            image_group_repo=ig_repo,
            nfs_base=str(tmp_path),
        )

        cmd = CleanupJobCommand(
            job_id=jid, client_id=client, correlation_id=_correlation_id()
        )
        with pytest.raises(AlreadyCleanedError):
            use_case.execute(cmd)


# ---------------------------------------------------------------------------
# Failure propagation tests
# ---------------------------------------------------------------------------

class TestCleanupJobFailures:
    """Verify queue submission failure is handled gracefully."""

    def test_queue_failure_still_completes_cleanup(self, tmp_path):
        """When queue submission fails, cleanup still proceeds (NFS + status)."""
        jid = _job_id()
        client = _client_id()

        job_repo = InMemoryJobRepository()
        job_repo.save(_make_job(client, jid))

        ig_repo = InMemoryImageGroupRepository()
        ig_repo.save(_make_image_group(jid))

        failing_queue = FakeQueueService(should_fail=True)
        use_case = _build_use_case(
            queue_service=failing_queue,
            job_repo=job_repo,
            image_group_repo=ig_repo,
            nfs_base=str(tmp_path),
        )

        cmd = CleanupJobCommand(
            job_id=jid, client_id=client, correlation_id=_correlation_id()
        )
        # Cleanup should still succeed (queue failure is non-fatal)
        result = use_case.execute(cmd)
        assert result.status == ImageGroupStatus.CLEANED.value
        assert ig_repo.find_by_job_id(jid).status == ImageGroupStatus.CLEANED


# ---------------------------------------------------------------------------
# Auto cleanup (cron) tests
# ---------------------------------------------------------------------------

class TestExecuteAuto:
    """Verify the cron-driven path skips client ownership checks."""

    def test_auto_cleanup_skips_client_check(self, tmp_path):
        jid = _job_id()
        client = _client_id()

        job_repo = InMemoryJobRepository()
        job_repo.save(_make_job(client, jid))

        ig_repo = InMemoryImageGroupRepository()
        ig_repo.save(
            _make_image_group(jid, status=ImageGroupStatus.FAILED)
        )

        queue_service = FakeQueueService()
        use_case = _build_use_case(
            queue_service=queue_service,
            job_repo=job_repo,
            image_group_repo=ig_repo,
            nfs_base=str(tmp_path),
        )

        result = use_case.execute_auto(
            job_id_str=str(jid),
            correlation_id="cron-test",
        )
        assert result.cleanup_type == "auto"
        # Queue submission succeeded -> async CLEANING, finalized later by
        # ResultPoller once the playbook reports success.
        assert result.status == ImageGroupStatus.CLEANING.value
        assert ig_repo.find_by_job_id(jid).status == ImageGroupStatus.CLEANING
