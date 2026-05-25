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

"""Unit tests for CleanupJobUseCase (hard delete + automated cleanup)."""

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from core.cleanup.exceptions import (
    AlreadyCleanedError,
    CleanupNfsFailedError,
    CleanupS3FailedError,
    CleanupStateInvalidError,
)
from core.cleanup.s3_service import S3CleanupResult, S3CleanupService
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

class FakeS3CleanupService(S3CleanupService):
    """Records calls and returns a configurable per-call deleted count."""

    def __init__(self, per_call_deleted=2, raise_for=None):
        self.calls = []
        self._per_call_deleted = per_call_deleted
        self._raise_for = raise_for

    def delete_image_path(self, image_path: str) -> S3CleanupResult:
        self.calls.append(image_path)
        if self._raise_for and image_path in self._raise_for:
            raise CleanupS3FailedError(
                image_group_id=image_path, exit_code=1, stderr="boom"
            )
        return S3CleanupResult(
            image_path=image_path,
            objects_deleted=self._per_call_deleted,
            exit_code=0,
            success=True,
        )


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
    s3_service: S3CleanupService,
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
        s3_cleanup_service=s3_service,
        uuid_generator=UUIDv4Generator(),
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

        s3 = FakeS3CleanupService(per_call_deleted=3)

        # NFS artifact dir with one fake file
        artifact_dir = tmp_path / "artifacts" / str(jid)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "config.yml").write_text("hello", encoding="utf-8")

        use_case = _build_use_case(
            s3_service=s3,
            job_repo=job_repo,
            image_group_repo=ig_repo,
            nfs_base=str(tmp_path),
        )
        return use_case, jid, client, ig_repo, s3, artifact_dir

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
        uc, jid, client, ig_repo, s3, artifact_dir = self._setup(status, tmp_path)
        cmd = CleanupJobCommand(
            job_id=jid, client_id=client, correlation_id=_correlation_id()
        )

        result = uc.execute(cmd)

        assert result.status == ImageGroupStatus.CLEANED.value
        assert result.cleanup_type == "manual"
        assert result.s3_objects_deleted == 3
        assert result.nfs_files_deleted == 1
        assert len(s3.calls) == 1
        assert ig_repo.find_by_job_id(jid).status == ImageGroupStatus.CLEANED
        assert not artifact_dir.exists()

    def test_missing_nfs_dir_returns_zero(self, tmp_path):
        uc, jid, client, ig_repo, s3, artifact_dir = self._setup(
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
        assert ig_repo.find_by_job_id(jid).status == ImageGroupStatus.CLEANED

    def test_legacy_image_name_skipped_without_failing(self, tmp_path):
        jid = _job_id()
        client = _client_id()
        job_repo = InMemoryJobRepository()
        job_repo.save(_make_job(client, jid))

        ig_repo = InMemoryImageGroupRepository()
        ig = _make_image_group(
            jid, image_paths=["slurm_node.img"]  # legacy filename, no s3://
        )
        ig_repo.save(ig)
        s3 = FakeS3CleanupService()

        use_case = _build_use_case(
            s3_service=s3,
            job_repo=job_repo,
            image_group_repo=ig_repo,
            nfs_base=str(tmp_path),
        )

        cmd = CleanupJobCommand(
            job_id=jid, client_id=client, correlation_id=_correlation_id()
        )
        result = use_case.execute(cmd)
        assert result.s3_objects_deleted == 0
        # No s3cmd invocations for legacy entries
        assert s3.calls == []


# ---------------------------------------------------------------------------
# Guard tests
# ---------------------------------------------------------------------------

class TestCleanupJobGuards:
    """Verify state preconditions and ownership checks."""

    def test_missing_job_raises_not_found(self, tmp_path):
        s3 = FakeS3CleanupService()
        use_case = _build_use_case(s3_service=s3, nfs_base=str(tmp_path))

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

        s3 = FakeS3CleanupService()
        use_case = _build_use_case(
            s3_service=s3,
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

        s3 = FakeS3CleanupService()
        use_case = _build_use_case(
            s3_service=s3,
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

        s3 = FakeS3CleanupService()
        use_case = _build_use_case(
            s3_service=s3,
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
    """Verify S3 / NFS failure surfaces propagate cleanly."""

    def test_s3_failure_propagates(self, tmp_path):
        jid = _job_id()
        client = _client_id()

        job_repo = InMemoryJobRepository()
        job_repo.save(_make_job(client, jid))

        ig_repo = InMemoryImageGroupRepository()
        path = (
            "s3://boot-images/slurm_node_x86_64/"
            "rhel-slurm_node_x86_64_xyz-image-build1/"
        )
        ig_repo.save(_make_image_group(jid, image_paths=[path]))

        s3 = FakeS3CleanupService(raise_for={path})
        use_case = _build_use_case(
            s3_service=s3,
            job_repo=job_repo,
            image_group_repo=ig_repo,
            nfs_base=str(tmp_path),
        )

        cmd = CleanupJobCommand(
            job_id=jid, client_id=client, correlation_id=_correlation_id()
        )
        with pytest.raises(CleanupS3FailedError):
            use_case.execute(cmd)
        # Image group must remain in its original state
        assert ig_repo.find_by_job_id(jid).status == ImageGroupStatus.BUILT


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

        s3 = FakeS3CleanupService(per_call_deleted=1)
        use_case = _build_use_case(
            s3_service=s3,
            job_repo=job_repo,
            image_group_repo=ig_repo,
            nfs_base=str(tmp_path),
        )

        result = use_case.execute_auto(
            job_id_str=str(jid),
            correlation_id="cron-test",
        )
        assert result.cleanup_type == "auto"
        assert result.status == ImageGroupStatus.CLEANED.value
        assert ig_repo.find_by_job_id(jid).status == ImageGroupStatus.CLEANED
