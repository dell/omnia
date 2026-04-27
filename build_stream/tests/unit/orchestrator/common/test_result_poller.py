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

"""Unit tests for common ResultPoller."""

import asyncio
import json
import uuid

import pytest

from core.artifacts.entities import ArtifactRecord
from core.artifacts.value_objects import (
    ArtifactKey,
    ArtifactKind,
    ArtifactDigest,
    ArtifactRef,
)
from core.image_group.value_objects import ImageGroupStatus
from core.jobs.entities import Stage
from core.jobs.value_objects import (
    JobId,
    StageName,
    StageState,
)
from core.localrepo.entities import PlaybookResult
from orchestrator.common.result_poller import ResultPoller


# --- Mock dependencies ---

class MockResultService:
    def __init__(self):
        self.callback = None
        self.results_to_deliver = []

    def poll_results(self, callback):
        self.callback = callback
        count = 0
        for result in self.results_to_deliver:
            callback(result)
            count += 1
        self.results_to_deliver = []
        return count


class MockStageRepo:
    def __init__(self):
        self._stages = {}

    def save(self, stage):
        key = (str(stage.job_id), stage.stage_name.value)
        self._stages[key] = stage

    def find_by_job_and_name(self, job_id, stage_name):
        return self._stages.get((str(job_id), stage_name.value))


class MockAuditRepo:
    def __init__(self):
        self._events = []

    def save(self, event):
        self._events.append(event)

    def find_by_job(self, job_id):
        return [e for e in self._events if str(e.job_id) == str(job_id)]


class MockJobRepo:
    def __init__(self):
        self._jobs = {}

    def find_by_id(self, job_id):
        return self._jobs.get(str(job_id))

    def save(self, job):
        self._jobs[str(job.job_id)] = job


class MockUUIDGenerator:
    def generate(self):
        return uuid.uuid4()


# --- Fixtures ---

@pytest.fixture
def mock_result_service():
    return MockResultService()


@pytest.fixture
def mock_stage_repo():
    return MockStageRepo()


@pytest.fixture
def mock_audit_repo():
    return MockAuditRepo()


@pytest.fixture
def mock_job_repo():
    return MockJobRepo()


@pytest.fixture
def mock_uuid_gen():
    return MockUUIDGenerator()


@pytest.fixture
def result_poller(mock_result_service, mock_job_repo, mock_stage_repo, mock_audit_repo, mock_uuid_gen):
    """Create ResultPoller instance with mocked dependencies."""
    return ResultPoller(
        result_service=mock_result_service,
        job_repo=mock_job_repo,
        stage_repo=mock_stage_repo,
        audit_repo=mock_audit_repo,
        uuid_generator=mock_uuid_gen,
        poll_interval=1,
    )


# --- Tests ---

class TestResultPoller:
    """Tests for common ResultPoller."""

    @pytest.mark.asyncio
    async def test_start_starts_polling(self, result_poller, mock_result_service):
        """Poller should start and begin polling."""
        await result_poller.start()
        assert result_poller._running is True
        assert result_poller._task is not None
        await result_poller.stop()

    @pytest.mark.asyncio
    async def test_stop_stops_polling(self, result_poller):
        """Poller should stop cleanly."""
        await result_poller.start()
        await result_poller.stop()
        assert result_poller._running is False

    @pytest.mark.asyncio
    async def test_double_start_is_safe(self, result_poller):
        """Starting twice should not create duplicate tasks."""
        await result_poller.start()
        await result_poller.start()  # Should log warning, not error
        assert result_poller._running is True
        await result_poller.stop()

    @pytest.mark.asyncio
    async def test_stop_without_start_is_safe(self, result_poller):
        """Stopping without starting should be a no-op."""
        await result_poller.stop()
        assert result_poller._running is False

    def test_on_result_success(
        self, result_poller, mock_stage_repo, mock_audit_repo
    ):
        """Successful result should complete the stage and emit audit event."""
        job_id = JobId(str(uuid.uuid4()))
        stage = Stage(
            job_id=job_id,
            stage_name=StageName("validate"),
            stage_state=StageState.IN_PROGRESS,
            attempt=1,
        )
        mock_stage_repo.save(stage)

        result = PlaybookResult(
            job_id=str(job_id),
            stage_name="validate",
            request_id=str(uuid.uuid4()),
            status="success",
            exit_code=0,
            duration_seconds=120,
        )

        result_poller._on_result_received(result)

        saved = mock_stage_repo.find_by_job_and_name(
            str(job_id), StageName("validate")
        )
        assert saved.stage_state == StageState.COMPLETED
        assert len(mock_audit_repo._events) == 1
        assert mock_audit_repo._events[0].event_type == "STAGE_COMPLETED"

    def test_on_result_failure(
        self, result_poller, mock_stage_repo, mock_audit_repo
    ):
        """Failed result should fail the stage and emit audit event."""
        job_id = JobId(str(uuid.uuid4()))
        stage = Stage(
            job_id=job_id,
            stage_name=StageName("validate"),
            stage_state=StageState.IN_PROGRESS,
            attempt=1,
        )
        mock_stage_repo.save(stage)

        result = PlaybookResult(
            job_id=str(job_id),
            stage_name="validate",
            request_id=str(uuid.uuid4()),
            status="failed",
            exit_code=1,
            error_code="PLAYBOOK_EXECUTION_FAILED",
            error_summary="Playbook exited with code 1",
        )

        result_poller._on_result_received(result)

        saved = mock_stage_repo.find_by_job_and_name(
            str(job_id), StageName("validate")
        )
        assert saved.stage_state == StageState.FAILED
        assert len(mock_audit_repo._events) == 1
        assert mock_audit_repo._events[0].event_type == "STAGE_FAILED"

    def test_on_result_stage_not_found(
        self, result_poller, mock_stage_repo, mock_audit_repo
    ):
        """Missing stage should be handled gracefully (no crash)."""
        result = PlaybookResult(
            job_id=str(uuid.uuid4()),
            stage_name="validate",
            request_id=str(uuid.uuid4()),
            status="success",
            exit_code=0,
        )

        # Should not raise
        result_poller._on_result_received(result)
        assert len(mock_audit_repo._events) == 0

    def test_backward_compatibility_alias(self):
        """LocalRepoResultPoller should be an alias for ResultPoller."""
        from orchestrator.local_repo.result_poller import LocalRepoResultPoller
        assert LocalRepoResultPoller is ResultPoller


# --- Mock artifact dependencies ---

class MockArtifactStore:
    """In-memory artifact store for testing."""

    def __init__(self):
        self._store = {}

    def store(self, hint, kind, content=None, **kwargs):
        key = ArtifactKey(f"{hint.namespace}/{hint.tags.get('job_id', 'x')}/{hint.label}")
        digest = ArtifactDigest("a" * 64)
        ref = ArtifactRef(key=key, digest=digest, size_bytes=len(content or b""), uri=f"mem://{key}")
        self._store[key.value] = content
        return ref

    def retrieve(self, key, kind, destination=None):
        return self._store.get(key.value, self._store.get(str(key), None))


class MockArtifactMetadataRepo:
    """In-memory artifact metadata repository for testing."""

    def __init__(self):
        self._records = {}

    def save(self, record):
        key = (str(record.job_id), record.stage_name.value, record.label)
        self._records[key] = record

    def find_by_job_stage_and_label(self, job_id, stage_name, label):
        return self._records.get((str(job_id), stage_name.value, label))


class MockImageGroupRepo:
    """In-memory ImageGroup repository for testing."""

    def __init__(self):
        self._groups = {}

    def save(self, image_group):
        self._groups[str(image_group.id)] = image_group

    def find_by_job_id(self, job_id):
        for ig in self._groups.values():
            if str(ig.job_id) == str(job_id):
                return ig
        return None


class MockImageRepo:
    """In-memory Image repository for testing."""

    def __init__(self):
        self._images = []

    def save_batch(self, images):
        self._images.extend(images)

    def find_by_image_group_id(self, image_group_id):
        return [i for i in self._images if i.image_group_id == str(image_group_id)]


# --- Fixtures for build-image tests ---

def _store_catalog_metadata(artifact_store, artifact_metadata_repo, job_id, metadata):
    """Helper: persist a catalog-metadata artifact the way parse-catalog does."""
    content = json.dumps(metadata).encode("utf-8")
    ref = artifact_store.store(
        hint=type("H", (), {
            "namespace": "catalog",
            "label": "catalog-metadata",
            "tags": {"job_id": str(job_id)},
        })(),
        kind=ArtifactKind.FILE,
        content=content,
    )
    record = ArtifactRecord(
        id=str(uuid.uuid4()),
        job_id=JobId(str(job_id)),
        stage_name=StageName("parse-catalog"),
        label="catalog-metadata",
        artifact_ref=ref,
        kind=ArtifactKind.FILE,
        content_type="application/json",
    )
    artifact_metadata_repo.save(record)


class TestBuildImageSuccess:
    """Tests for ImageGroup/Image creation on build-image success."""

    def test_creates_image_group_and_images_on_build_image_success(self):
        """On build-image success with artifact repos wired, ImageGroup + Images are created."""
        job_id = JobId(str(uuid.uuid4()))

        stage_repo = MockStageRepo()
        stage = Stage(
            job_id=job_id,
            stage_name=StageName("build-image-x86_64"),
            stage_state=StageState.IN_PROGRESS,
            attempt=1,
        )
        stage_repo.save(stage)

        ig_repo = MockImageGroupRepo()
        img_repo = MockImageRepo()
        artifact_store = MockArtifactStore()
        artifact_metadata_repo = MockArtifactMetadataRepo()

        # Simulate parse-catalog having stored catalog metadata
        _store_catalog_metadata(
            artifact_store, artifact_metadata_repo, job_id,
            {
                "image_group_id": "test-cluster-v1",
                "roles": ["slurm_node_x86_64", "kube_cp_x86_64"],
                "role_images": {
                    "slurm_node_x86_64": "slurm_node.qcow2",
                    "kube_cp_x86_64": "kube_cp.qcow2",
                },
            },
        )

        poller = ResultPoller(
            result_service=MockResultService(),
            job_repo=MockJobRepo(),
            stage_repo=stage_repo,
            audit_repo=MockAuditRepo(),
            uuid_generator=MockUUIDGenerator(),
            poll_interval=1,
            image_group_repo=ig_repo,
            image_repo=img_repo,
            artifact_store=artifact_store,
            artifact_metadata_repo=artifact_metadata_repo,
        )

        result = PlaybookResult(
            job_id=str(job_id),
            stage_name="build-image-x86_64",
            request_id=str(uuid.uuid4()),
            status="success",
            exit_code=0,
            duration_seconds=300,
        )

        poller._on_result_received(result)

        # ImageGroup should have been created with BUILT status
        ig = ig_repo.find_by_job_id(job_id)
        assert ig is not None, "ImageGroup was not created"
        assert str(ig.id) == "test-cluster-v1"
        assert ig.status == ImageGroupStatus.BUILT

        # Images should have been created for each role
        images = img_repo.find_by_image_group_id("test-cluster-v1")
        assert len(images) == 2
        roles = {i.role for i in images}
        assert roles == {"slurm_node_x86_64", "kube_cp_x86_64"}

    def test_skips_image_group_when_artifact_repos_missing(self):
        """Without artifact repos, ImageGroup creation is skipped (the original bug)."""
        job_id = JobId(str(uuid.uuid4()))

        stage_repo = MockStageRepo()
        stage = Stage(
            job_id=job_id,
            stage_name=StageName("build-image-x86_64"),
            stage_state=StageState.IN_PROGRESS,
            attempt=1,
        )
        stage_repo.save(stage)

        ig_repo = MockImageGroupRepo()
        img_repo = MockImageRepo()

        # Deliberately omit artifact_store and artifact_metadata_repo
        poller = ResultPoller(
            result_service=MockResultService(),
            job_repo=MockJobRepo(),
            stage_repo=stage_repo,
            audit_repo=MockAuditRepo(),
            uuid_generator=MockUUIDGenerator(),
            poll_interval=1,
            image_group_repo=ig_repo,
            image_repo=img_repo,
            # artifact_store=None,            -- the bug
            # artifact_metadata_repo=None,    -- the bug
        )

        result = PlaybookResult(
            job_id=str(job_id),
            stage_name="build-image-x86_64",
            request_id=str(uuid.uuid4()),
            status="success",
            exit_code=0,
            duration_seconds=300,
        )

        poller._on_result_received(result)

        # Stage should still be COMPLETED
        saved = stage_repo.find_by_job_and_name(
            str(job_id), StageName("build-image-x86_64")
        )
        assert saved.stage_state == StageState.COMPLETED

        # But ImageGroup should NOT have been created
        ig = ig_repo.find_by_job_id(job_id)
        assert ig is None, "ImageGroup should not be created without artifact repos"

    def test_no_image_group_for_non_build_image_stage(self):
        """Non-build-image stages should not trigger ImageGroup creation."""
        job_id = JobId(str(uuid.uuid4()))

        stage_repo = MockStageRepo()
        stage = Stage(
            job_id=job_id,
            stage_name=StageName("create-local-repository"),
            stage_state=StageState.IN_PROGRESS,
            attempt=1,
        )
        stage_repo.save(stage)

        ig_repo = MockImageGroupRepo()
        img_repo = MockImageRepo()

        poller = ResultPoller(
            result_service=MockResultService(),
            job_repo=MockJobRepo(),
            stage_repo=stage_repo,
            audit_repo=MockAuditRepo(),
            uuid_generator=MockUUIDGenerator(),
            poll_interval=1,
            image_group_repo=ig_repo,
            image_repo=img_repo,
            artifact_store=MockArtifactStore(),
            artifact_metadata_repo=MockArtifactMetadataRepo(),
        )

        result = PlaybookResult(
            job_id=str(job_id),
            stage_name="create-local-repository",
            request_id=str(uuid.uuid4()),
            status="success",
            exit_code=0,
        )

        poller._on_result_received(result)

        ig = ig_repo.find_by_job_id(job_id)
        assert ig is None, "ImageGroup should not be created for non-build-image stages"
