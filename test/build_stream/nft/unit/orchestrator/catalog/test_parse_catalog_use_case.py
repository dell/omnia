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

"""Unit tests for ParseCatalogUseCase (reintroduced, minimal form).

Covers the reason this stage was reintroduced: catching the
image_group_id 1:1-with-job uniqueness violation before any
create-local-repository/build-image cycles run.
"""

import json
import uuid

import pytest

from core.artifacts.entities import ArtifactRecord
from core.artifacts.value_objects import ArtifactDigest, ArtifactKey, ArtifactKind, ArtifactRef
from core.catalog.exceptions import CatalogNotUploadedError, InvalidCatalogFormatError
from core.image_group.exceptions import DuplicateImageGroupError
from core.image_group.value_objects import ImageGroupId
from core.jobs.entities import Job
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    StageAlreadyCompletedError,
    TerminalStateViolationError,
)
from core.jobs.value_objects import ClientId, CorrelationId, JobId, StageName, StageType
from infra.id_generator import UUIDv4Generator
from infra.repositories.in_memory import (
    InMemoryAuditEventRepository,
    InMemoryJobRepository,
    InMemoryStageRepository,
)
from orchestrator.catalog.commands.parse_catalog import ParseCatalogCommand
from orchestrator.catalog.use_cases.parse_catalog import ParseCatalogUseCase


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeArtifactStore:
    """In-memory artifact store for testing."""

    def __init__(self):
        self._store = {}

    def store(self, hint, kind, content=None, **_kwargs):
        key = ArtifactKey(f"{hint.namespace}/{hint.tags.get('job_id', 'x')}/{hint.label}")
        digest = ArtifactDigest("a" * 64)
        ref = ArtifactRef(key=key, digest=digest, size_bytes=len(content or b""), uri=f"mem://{key}")
        self._store[key.value] = content
        return ref

    def retrieve(self, key, kind):  # pylint: disable=unused-argument
        return self._store.get(key.value)


class FakeArtifactMetadataRepo:
    """In-memory artifact metadata repository for testing."""

    def __init__(self):
        self._records = []

    def save(self, record):
        self._records.append(record)

    def list_by_job_id(self, job_id):
        return [r for r in self._records if str(r.job_id) == str(job_id)]


class FakeImageGroupRepo:
    """In-memory ImageGroup existence checker for testing."""

    def __init__(self, existing_ids=None):
        self._existing_ids = set(existing_ids or [])

    def exists(self, image_group_id) -> bool:
        return str(image_group_id) in self._existing_ids


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _job_id() -> JobId:
    return JobId(str(uuid.uuid4()))


def _client_id() -> ClientId:
    return ClientId(str(uuid.uuid4()))


def _correlation_id() -> CorrelationId:
    return CorrelationId(str(uuid.uuid4()))


def _upload_catalog(
    artifact_store: FakeArtifactStore,
    artifact_metadata_repo: FakeArtifactMetadataRepo,
    job_id: JobId,
    catalog_data: dict,
    label: str = "catalog_rhel.json",
) -> None:
    """Simulate the "upload" stage having already stored the catalog."""
    from core.artifacts.value_objects import StoreHint  # local import to avoid cycles

    content = json.dumps(catalog_data).encode("utf-8")
    hint = StoreHint(
        namespace="config-files", label=label, tags={"job_id": str(job_id)}
    )
    ref = artifact_store.store(hint=hint, kind=ArtifactKind.FILE, content=content)
    record = ArtifactRecord(
        id=str(uuid.uuid4()),
        job_id=job_id,
        stage_name=StageName("upload"),
        label=label,
        artifact_ref=ref,
        kind=ArtifactKind.FILE,
        content_type="application/octet-stream",
    )
    artifact_metadata_repo.save(record)


def _valid_catalog(image_group_id: str = "omnia-services-rhel-10-0-slurm-test") -> dict:
    return {
        "Catalog": {
            "Identifier": image_group_id,
            "Name": "test-catalog",
            "Version": "1.0",
            "FunctionalLayer": [
                {"Name": "slurm_node_rhel_10_0_x86_64"},
                {"Name": "slurm_control_node_rhel_10_0_x86_64"},
            ],
        }
    }


def _build_use_case(
    job_repo=None,
    stage_repo=None,
    audit_repo=None,
    artifact_store=None,
    artifact_metadata_repo=None,
    image_group_repo=None,
) -> ParseCatalogUseCase:
    return ParseCatalogUseCase(
        job_repo=job_repo or InMemoryJobRepository(),
        stage_repo=stage_repo or InMemoryStageRepository(),
        audit_repo=audit_repo or InMemoryAuditEventRepository(),
        artifact_store=artifact_store or FakeArtifactStore(),
        artifact_metadata_repo=artifact_metadata_repo or FakeArtifactMetadataRepo(),
        uuid_generator=UUIDv4Generator(),
        image_group_repo=image_group_repo,
    )


def _make_job_and_stage(job_repo, stage_repo, jid, client):
    from core.jobs.entities import Stage

    job = Job(job_id=jid, client_id=client, request_client_id=str(client))
    job_repo.save(job)
    stage = Stage(job_id=jid, stage_name=StageName(StageType.PARSE_CATALOG.value))
    stage_repo.save(stage)
    return job, stage


# ---------------------------------------------------------------------------
# Happy-path / violation-check tests
# ---------------------------------------------------------------------------

class TestUniquenessCheck:
    """The core reason this stage was reintroduced."""

    def test_new_image_group_id_passes(self):
        jid = _job_id()
        client = _client_id()
        job_repo = InMemoryJobRepository()
        stage_repo = InMemoryStageRepository()
        _make_job_and_stage(job_repo, stage_repo, jid, client)

        artifact_store = FakeArtifactStore()
        artifact_metadata_repo = FakeArtifactMetadataRepo()
        _upload_catalog(artifact_store, artifact_metadata_repo, jid, _valid_catalog("new-group-id"))

        use_case = _build_use_case(
            job_repo=job_repo,
            stage_repo=stage_repo,
            artifact_store=artifact_store,
            artifact_metadata_repo=artifact_metadata_repo,
            image_group_repo=FakeImageGroupRepo(existing_ids=set()),
        )
        cmd = ParseCatalogCommand(job_id=jid, client_id=client, correlation_id=_correlation_id())

        result = use_case.execute(cmd)

        assert result.stage_state == "COMPLETED"
        assert result.image_group_id == "new-group-id"
        assert stage_repo.find_by_job_and_name(
            jid, StageName(StageType.PARSE_CATALOG.value)
        ).stage_state.value == "COMPLETED"

    def test_duplicate_image_group_id_raises_and_fails_stage(self):
        """This is the violation the user reported: a second job reusing
        an image_group_id already owned by another job's ImageGroup."""
        jid = _job_id()
        client = _client_id()
        job_repo = InMemoryJobRepository()
        stage_repo = InMemoryStageRepository()
        _make_job_and_stage(job_repo, stage_repo, jid, client)

        artifact_store = FakeArtifactStore()
        artifact_metadata_repo = FakeArtifactMetadataRepo()
        _upload_catalog(
            artifact_store, artifact_metadata_repo, jid,
            _valid_catalog("omnia-services-rhel-10-0-slurm-test"),
        )

        use_case = _build_use_case(
            job_repo=job_repo,
            stage_repo=stage_repo,
            artifact_store=artifact_store,
            artifact_metadata_repo=artifact_metadata_repo,
            image_group_repo=FakeImageGroupRepo(
                existing_ids={"omnia-services-rhel-10-0-slurm-test"}
            ),
        )
        cmd = ParseCatalogCommand(job_id=jid, client_id=client, correlation_id=_correlation_id())

        with pytest.raises(DuplicateImageGroupError):
            use_case.execute(cmd)

        stage = stage_repo.find_by_job_and_name(jid, StageName(StageType.PARSE_CATALOG.value))
        assert stage.stage_state.value == "FAILED"
        assert stage.error_code == "DuplicateImageGroupError"

    def test_no_image_group_repo_skips_check(self):
        """Without an image_group_repo configured, the check is skipped
        (fails open, matching the pre-existing behavior of this check)."""
        jid = _job_id()
        client = _client_id()
        job_repo = InMemoryJobRepository()
        stage_repo = InMemoryStageRepository()
        _make_job_and_stage(job_repo, stage_repo, jid, client)

        artifact_store = FakeArtifactStore()
        artifact_metadata_repo = FakeArtifactMetadataRepo()
        _upload_catalog(artifact_store, artifact_metadata_repo, jid, _valid_catalog())

        use_case = _build_use_case(
            job_repo=job_repo,
            stage_repo=stage_repo,
            artifact_store=artifact_store,
            artifact_metadata_repo=artifact_metadata_repo,
            image_group_repo=None,
        )
        cmd = ParseCatalogCommand(job_id=jid, client_id=client, correlation_id=_correlation_id())

        result = use_case.execute(cmd)
        assert result.stage_state == "COMPLETED"

    def test_lowercase_catalog_keys_supported(self):
        jid = _job_id()
        client = _client_id()
        job_repo = InMemoryJobRepository()
        stage_repo = InMemoryStageRepository()
        _make_job_and_stage(job_repo, stage_repo, jid, client)

        artifact_store = FakeArtifactStore()
        artifact_metadata_repo = FakeArtifactMetadataRepo()
        _upload_catalog(
            artifact_store, artifact_metadata_repo, jid,
            {"catalog": {"identifier": "lowercase-group-id"}},
        )

        use_case = _build_use_case(
            job_repo=job_repo,
            stage_repo=stage_repo,
            artifact_store=artifact_store,
            artifact_metadata_repo=artifact_metadata_repo,
            image_group_repo=FakeImageGroupRepo(),
        )
        cmd = ParseCatalogCommand(job_id=jid, client_id=client, correlation_id=_correlation_id())

        result = use_case.execute(cmd)
        assert result.image_group_id == "lowercase-group-id"


# ---------------------------------------------------------------------------
# Catalog-loading / format tests
# ---------------------------------------------------------------------------

class TestCatalogLoading:
    """Verify catalog retrieval and format validation."""

    def test_no_catalog_uploaded_raises(self):
        jid = _job_id()
        client = _client_id()
        job_repo = InMemoryJobRepository()
        stage_repo = InMemoryStageRepository()
        _make_job_and_stage(job_repo, stage_repo, jid, client)

        use_case = _build_use_case(job_repo=job_repo, stage_repo=stage_repo)
        cmd = ParseCatalogCommand(job_id=jid, client_id=client, correlation_id=_correlation_id())

        with pytest.raises(CatalogNotUploadedError):
            use_case.execute(cmd)

    def test_catalog_missing_identifier_raises_invalid_format(self):
        jid = _job_id()
        client = _client_id()
        job_repo = InMemoryJobRepository()
        stage_repo = InMemoryStageRepository()
        _make_job_and_stage(job_repo, stage_repo, jid, client)

        artifact_store = FakeArtifactStore()
        artifact_metadata_repo = FakeArtifactMetadataRepo()
        _upload_catalog(artifact_store, artifact_metadata_repo, jid, {"Catalog": {}})

        use_case = _build_use_case(
            job_repo=job_repo,
            stage_repo=stage_repo,
            artifact_store=artifact_store,
            artifact_metadata_repo=artifact_metadata_repo,
            image_group_repo=FakeImageGroupRepo(),
        )
        cmd = ParseCatalogCommand(job_id=jid, client_id=client, correlation_id=_correlation_id())

        with pytest.raises(InvalidCatalogFormatError):
            use_case.execute(cmd)

    def test_catalog_missing_top_level_key_raises_invalid_format(self):
        jid = _job_id()
        client = _client_id()
        job_repo = InMemoryJobRepository()
        stage_repo = InMemoryStageRepository()
        _make_job_and_stage(job_repo, stage_repo, jid, client)

        artifact_store = FakeArtifactStore()
        artifact_metadata_repo = FakeArtifactMetadataRepo()
        _upload_catalog(artifact_store, artifact_metadata_repo, jid, {"NotCatalog": {}})

        use_case = _build_use_case(
            job_repo=job_repo,
            stage_repo=stage_repo,
            artifact_store=artifact_store,
            artifact_metadata_repo=artifact_metadata_repo,
        )
        cmd = ParseCatalogCommand(job_id=jid, client_id=client, correlation_id=_correlation_id())

        with pytest.raises(InvalidCatalogFormatError):
            use_case.execute(cmd)


# ---------------------------------------------------------------------------
# Stage guard tests
# ---------------------------------------------------------------------------

class TestStageGuards:
    """Verify job/stage state preconditions and ownership checks."""

    def test_missing_job_raises_not_found(self):
        use_case = _build_use_case()
        cmd = ParseCatalogCommand(
            job_id=_job_id(), client_id=_client_id(), correlation_id=_correlation_id()
        )
        with pytest.raises(JobNotFoundError):
            use_case.execute(cmd)

    def test_client_mismatch_raises_not_found(self):
        jid = _job_id()
        owner = _client_id()
        intruder = _client_id()
        job_repo = InMemoryJobRepository()
        stage_repo = InMemoryStageRepository()
        _make_job_and_stage(job_repo, stage_repo, jid, owner)

        use_case = _build_use_case(job_repo=job_repo, stage_repo=stage_repo)
        cmd = ParseCatalogCommand(job_id=jid, client_id=intruder, correlation_id=_correlation_id())

        with pytest.raises(JobNotFoundError):
            use_case.execute(cmd)

    def test_missing_stage_raises_not_found(self):
        jid = _job_id()
        client = _client_id()
        job_repo = InMemoryJobRepository()
        job_repo.save(Job(job_id=jid, client_id=client, request_client_id=str(client)))
        stage_repo = InMemoryStageRepository()  # no stage saved

        use_case = _build_use_case(job_repo=job_repo, stage_repo=stage_repo)
        cmd = ParseCatalogCommand(job_id=jid, client_id=client, correlation_id=_correlation_id())

        with pytest.raises(JobNotFoundError):
            use_case.execute(cmd)

    def test_stage_already_completed_raises(self):
        from core.jobs.entities import Stage
        from core.jobs.value_objects import StageState

        jid = _job_id()
        client = _client_id()
        job_repo = InMemoryJobRepository()
        job_repo.save(Job(job_id=jid, client_id=client, request_client_id=str(client)))
        stage_repo = InMemoryStageRepository()
        stage_repo.save(
            Stage(
                job_id=jid,
                stage_name=StageName(StageType.PARSE_CATALOG.value),
                stage_state=StageState.COMPLETED,
                attempt=1,
            )
        )

        use_case = _build_use_case(job_repo=job_repo, stage_repo=stage_repo)
        cmd = ParseCatalogCommand(job_id=jid, client_id=client, correlation_id=_correlation_id())

        with pytest.raises(StageAlreadyCompletedError):
            use_case.execute(cmd)

    def test_stage_in_progress_raises_invalid_state_transition(self):
        from core.jobs.entities import Stage
        from core.jobs.value_objects import StageState

        jid = _job_id()
        client = _client_id()
        job_repo = InMemoryJobRepository()
        job_repo.save(Job(job_id=jid, client_id=client, request_client_id=str(client)))
        stage_repo = InMemoryStageRepository()
        stage_repo.save(
            Stage(
                job_id=jid,
                stage_name=StageName(StageType.PARSE_CATALOG.value),
                stage_state=StageState.IN_PROGRESS,
                attempt=1,
            )
        )

        use_case = _build_use_case(job_repo=job_repo, stage_repo=stage_repo)
        cmd = ParseCatalogCommand(job_id=jid, client_id=client, correlation_id=_correlation_id())

        with pytest.raises(InvalidStateTransitionError):
            use_case.execute(cmd)

    def test_terminal_job_raises(self):
        jid = _job_id()
        client = _client_id()
        job_repo = InMemoryJobRepository()
        job = Job(job_id=jid, client_id=client, request_client_id=str(client))
        job.tombstone()
        job_repo.save(job)
        stage_repo = InMemoryStageRepository()

        use_case = _build_use_case(job_repo=job_repo, stage_repo=stage_repo)
        cmd = ParseCatalogCommand(job_id=jid, client_id=client, correlation_id=_correlation_id())

        with pytest.raises(JobNotFoundError):
            use_case.execute(cmd)

    def test_failed_stage_resets_and_retries(self):
        from core.jobs.entities import Stage
        from core.jobs.value_objects import StageState

        jid = _job_id()
        client = _client_id()
        job_repo = InMemoryJobRepository()
        job_repo.save(Job(job_id=jid, client_id=client, request_client_id=str(client)))
        stage_repo = InMemoryStageRepository()
        stage_repo.save(
            Stage(
                job_id=jid,
                stage_name=StageName(StageType.PARSE_CATALOG.value),
                stage_state=StageState.FAILED,
                attempt=1,
            )
        )

        artifact_store = FakeArtifactStore()
        artifact_metadata_repo = FakeArtifactMetadataRepo()
        _upload_catalog(artifact_store, artifact_metadata_repo, jid, _valid_catalog("retry-group"))

        use_case = _build_use_case(
            job_repo=job_repo,
            stage_repo=stage_repo,
            artifact_store=artifact_store,
            artifact_metadata_repo=artifact_metadata_repo,
            image_group_repo=FakeImageGroupRepo(),
        )
        cmd = ParseCatalogCommand(job_id=jid, client_id=client, correlation_id=_correlation_id())

        result = use_case.execute(cmd)
        assert result.stage_state == "COMPLETED"
        assert result.image_group_id == "retry-group"
