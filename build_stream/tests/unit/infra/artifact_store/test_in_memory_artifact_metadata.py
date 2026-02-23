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

"""Unit tests for InMemoryArtifactMetadataRepository."""

import pytest

from core.artifacts.entities import ArtifactRecord
from core.artifacts.value_objects import (
    ArtifactDigest,
    ArtifactKey,
    ArtifactKind,
    ArtifactRef,
)
from core.jobs.value_objects import JobId, StageName, StageType
from infra.artifact_store.in_memory_artifact_metadata import (
    InMemoryArtifactMetadataRepository,
)


VALID_JOB_ID = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
VALID_JOB_ID_2 = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c11"


def _make_ref(key_str: str = "ns/hash/label.bin") -> ArtifactRef:
    return ArtifactRef(
        key=ArtifactKey(key_str),
        digest=ArtifactDigest("a" * 64),
        size_bytes=100,
        uri=f"memory://{key_str}",
    )


def _make_record(
    job_id_str: str = VALID_JOB_ID,
    stage: str = "parse-catalog",
    label: str = "catalog-file",
    record_id: str = "rec-001",
) -> ArtifactRecord:
    return ArtifactRecord(
        id=record_id,
        job_id=JobId(job_id_str),
        stage_name=StageName(stage),
        label=label,
        artifact_ref=_make_ref(f"ns/{record_id}/{label}.bin"),
        kind=ArtifactKind.FILE,
        content_type="application/json",
    )


class TestSave:
    """Tests for saving artifact records."""

    def test_save_and_find(self, artifact_metadata_repo) -> None:
        """Test that save and find operations work correctly."""
        record = _make_record()
        artifact_metadata_repo.save(record)
        found = artifact_metadata_repo.find_by_job_stage_and_label(
            job_id=JobId(VALID_JOB_ID),
            stage_name=StageName(StageType.PARSE_CATALOG.value),
            label="catalog-file",
        )
        assert found is not None
        assert found.id == "rec-001"

    def test_save_overwrites_same_key(self, artifact_metadata_repo) -> None:
        """Test that save overwrites existing record with same key."""
        record1 = _make_record(record_id="rec-001")
        record2 = _make_record(record_id="rec-002")
        artifact_metadata_repo.save(record1)
        artifact_metadata_repo.save(record2)
        found = artifact_metadata_repo.find_by_job_stage_and_label(
            job_id=JobId(VALID_JOB_ID),
            stage_name=StageName(StageType.PARSE_CATALOG.value),
            label="catalog-file",
        )
        assert found is not None
        assert found.id == "rec-002"


class TestFind:
    """Tests for finding artifact records."""

    def test_find_not_found(self, artifact_metadata_repo) -> None:
        """Test that find returns None for nonexistent record."""
        found = artifact_metadata_repo.find_by_job_stage_and_label(
            job_id=JobId(VALID_JOB_ID),
            stage_name=StageName(StageType.PARSE_CATALOG.value),
            label="nonexistent",
        )
        assert found is None

    def test_find_by_job(self, artifact_metadata_repo) -> None:
        """Test that find_by_job returns correct records."""
        artifact_metadata_repo.save(_make_record(label="catalog-file", record_id="r1"))
        artifact_metadata_repo.save(
            _make_record(
                stage="generate-input-files",
                label="omnia-configs",
                record_id="r2",
            )
        )
        artifact_metadata_repo.save(
            _make_record(
                job_id_str=VALID_JOB_ID_2,
                label="catalog-file",
                record_id="r3",
            )
        )
        results = artifact_metadata_repo.find_by_job(JobId(VALID_JOB_ID))
        assert len(results) == 2

    def test_find_by_job_empty(self, artifact_metadata_repo) -> None:
        """Test that find_by_job returns empty list for no records."""
        results = artifact_metadata_repo.find_by_job(JobId(VALID_JOB_ID))
        assert results == []


class TestDelete:
    """Tests for deleting artifact records."""

    def test_delete_by_job(self, artifact_metadata_repo) -> None:
        """Test that delete_by_job removes correct records."""
        artifact_metadata_repo.save(_make_record(label="catalog-file", record_id="r1"))
        artifact_metadata_repo.save(
            _make_record(
                stage="generate-input-files",
                label="omnia-configs",
                record_id="r2",
            )
        )
        artifact_metadata_repo.save(
            _make_record(
                job_id_str=VALID_JOB_ID_2,
                label="catalog-file",
                record_id="r3",
            )
        )
        count = artifact_metadata_repo.delete_by_job(JobId(VALID_JOB_ID))
        assert count == 2
        assert artifact_metadata_repo.find_by_job(JobId(VALID_JOB_ID)) == []
        assert len(artifact_metadata_repo.find_by_job(JobId(VALID_JOB_ID_2))) == 1

    def test_delete_by_job_returns_zero(self, artifact_metadata_repo) -> None:
        """Test that delete_by_job returns 0 for no matching records."""
        count = artifact_metadata_repo.delete_by_job(JobId(VALID_JOB_ID))
        assert count == 0
