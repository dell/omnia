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

"""Unit tests for S1-4: API Enhancements for ImageGroup/Image Data Model.

Part A: Parse-catalog enhancement — image_group_id extraction, uniqueness check.
Part B: Build-image completion — ImageGroup/Image record creation.
"""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from core.catalog.exceptions import InvalidCatalogFormatError
from core.image_group.exceptions import DuplicateImageGroupError
from core.image_group.value_objects import ImageGroupId, ImageGroupStatus
from core.jobs.entities import Job, Stage
from core.jobs.value_objects import (
    ClientId,
    CorrelationId,
    JobId,
    StageName,
    StageState,
    StageType,
)
from infra.artifact_store.in_memory_artifact_store import InMemoryArtifactStore
from infra.artifact_store.in_memory_artifact_metadata import (
    InMemoryArtifactMetadataRepository,
)
from infra.repositories import (
    InMemoryAuditEventRepository,
    InMemoryImageGroupRepository,
    InMemoryImageRepository,
    InMemoryJobRepository,
    InMemoryStageRepository,
)
from orchestrator.catalog.commands.parse_catalog import ParseCatalogCommand
from orchestrator.catalog.use_cases.parse_catalog import ParseCatalogUseCase


VALID_JOB_ID = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
VALID_CORRELATION_ID = "018f3c4b-2d9e-7d1a-8a2b-111111111111"


class FakeUUIDGenerator:
    """Deterministic UUID generator for tests."""

    def __init__(self):
        self._counter = 0

    def generate(self):
        self._counter += 1
        return uuid.UUID(f"00000000-0000-4000-8000-{self._counter:012d}")


def _make_catalog_json(
    identifier="omnia-cluster-v1.2",
    functional_layers=None,
):
    """Build a catalog JSON dict for testing.

    Uses the real catalog format: ``{"Catalog": {"Identifier": ..., "FunctionalLayer": [...]}}``.
    """
    if functional_layers is None:
        functional_layers = [
            {"Name": "slurm_node", "FunctionalPackages": ["slurm-23.02"]},
            {"Name": "kube_node", "FunctionalPackages": ["kubelet-1.28"]},
        ]
    return {
        "Catalog": {
            "Name": "Catalog",
            "Version": "1.0",
            "Identifier": identifier,
            "FunctionalLayer": functional_layers,
        }
    }


def _make_catalog_bytes(catalog_dict=None):
    """Serialize catalog dict to bytes."""
    if catalog_dict is None:
        catalog_dict = _make_catalog_json()
    return json.dumps(catalog_dict).encode("utf-8")


def _make_command(content=None, filename="catalog.json"):
    return ParseCatalogCommand(
        job_id=JobId(VALID_JOB_ID),
        correlation_id=CorrelationId(VALID_CORRELATION_ID),
        filename=filename,
        content=content or _make_catalog_bytes(),
    )


def _setup_job_and_stage(job_repo, stage_repo):
    """Create a CREATED job with a PENDING parse-catalog stage."""
    job = Job(
        job_id=JobId(VALID_JOB_ID),
        client_id=ClientId("test-client"),
        request_client_id="test-client",
    )
    job_repo.save(job)

    stage = Stage(
        job_id=JobId(VALID_JOB_ID),
        stage_name=StageName(StageType.PARSE_CATALOG.value),
        stage_state=StageState.PENDING,
    )
    stage_repo.save(stage)
    return job, stage


def _build_use_case(
    job_repo, stage_repo, audit_repo,
    artifact_store, artifact_metadata_repo, uuid_generator,
    image_group_repo=None,
):
    return ParseCatalogUseCase(
        job_repo=job_repo,
        stage_repo=stage_repo,
        audit_repo=audit_repo,
        artifact_store=artifact_store,
        artifact_metadata_repo=artifact_metadata_repo,
        uuid_generator=uuid_generator,
        image_group_repo=image_group_repo,
    )


# ======================================================================
# Part A: Parse-Catalog Enhancement Tests
# ======================================================================


@pytest.mark.unit
class TestExtractImageGroupId:
    """Tests for _extract_image_group_id() — reads Catalog.Identifier."""

    def _get_use_case(self):
        return _build_use_case(
            InMemoryJobRepository(),
            InMemoryStageRepository(),
            InMemoryAuditEventRepository(),
            InMemoryArtifactStore(),
            InMemoryArtifactMetadataRepository(),
            FakeUUIDGenerator(),
        )

    def test_valid_identifier(self):
        uc = self._get_use_case()
        catalog = {"Catalog": {"Identifier": "image-build"}}
        result = uc._extract_image_group_id(catalog)
        assert result == ImageGroupId("image-build")

    def test_missing_catalog_key_raises(self):
        uc = self._get_use_case()
        with pytest.raises(InvalidCatalogFormatError, match="Catalog"):
            uc._extract_image_group_id({})

    def test_catalog_not_dict_raises(self):
        uc = self._get_use_case()
        with pytest.raises(InvalidCatalogFormatError, match="Catalog"):
            uc._extract_image_group_id({"Catalog": "not-a-dict"})

    def test_missing_identifier_raises(self):
        uc = self._get_use_case()
        with pytest.raises(InvalidCatalogFormatError, match="Identifier"):
            uc._extract_image_group_id({"Catalog": {"Name": "test"}})

    def test_empty_identifier_raises(self):
        uc = self._get_use_case()
        with pytest.raises(InvalidCatalogFormatError, match="Identifier"):
            uc._extract_image_group_id({"Catalog": {"Identifier": ""}})

    def test_whitespace_identifier_raises(self):
        uc = self._get_use_case()
        with pytest.raises(InvalidCatalogFormatError, match="Identifier"):
            uc._extract_image_group_id({"Catalog": {"Identifier": "   "}})

    def test_identifier_exceeds_128_chars_raises(self):
        uc = self._get_use_case()
        long_id = "x" * 129
        with pytest.raises(InvalidCatalogFormatError, match="cannot exceed 128"):
            uc._extract_image_group_id({"Catalog": {"Identifier": long_id}})

    def test_identifier_exactly_128_chars_ok(self):
        uc = self._get_use_case()
        valid_id = "x" * 128
        result = uc._extract_image_group_id({"Catalog": {"Identifier": valid_id}})
        assert result == ImageGroupId(valid_id)


@pytest.mark.unit
class TestCheckImageGroupUniqueness:
    """Tests for _check_image_group_uniqueness()."""

    def test_unique_id_passes(self):
        ig_repo = InMemoryImageGroupRepository()
        uc = _build_use_case(
            InMemoryJobRepository(),
            InMemoryStageRepository(),
            InMemoryAuditEventRepository(),
            InMemoryArtifactStore(),
            InMemoryArtifactMetadataRepository(),
            FakeUUIDGenerator(),
            image_group_repo=ig_repo,
        )
        # Should not raise
        uc._check_image_group_uniqueness(ImageGroupId("new-group-id"))

    def test_duplicate_id_raises_409(self):
        ig_repo = InMemoryImageGroupRepository()
        # Pre-seed an existing ImageGroup
        from core.image_group.entities import ImageGroup
        existing = ImageGroup(
            id=ImageGroupId("existing-group"),
            job_id=JobId("00000000-0000-0000-0000-000000000001"),
            status=ImageGroupStatus.BUILT,
        )
        ig_repo.save(existing)

        uc = _build_use_case(
            InMemoryJobRepository(),
            InMemoryStageRepository(),
            InMemoryAuditEventRepository(),
            InMemoryArtifactStore(),
            InMemoryArtifactMetadataRepository(),
            FakeUUIDGenerator(),
            image_group_repo=ig_repo,
        )
        with pytest.raises(DuplicateImageGroupError):
            uc._check_image_group_uniqueness(ImageGroupId("existing-group"))

    def test_no_repo_skips_check(self):
        uc = _build_use_case(
            InMemoryJobRepository(),
            InMemoryStageRepository(),
            InMemoryAuditEventRepository(),
            InMemoryArtifactStore(),
            InMemoryArtifactMetadataRepository(),
            FakeUUIDGenerator(),
            image_group_repo=None,
        )
        # Should not raise even without repo
        uc._check_image_group_uniqueness(ImageGroupId("any-id"))


@pytest.mark.unit
class TestExtractCatalogMetadata:
    """Tests for _extract_catalog_metadata() — reads Catalog.FunctionalLayer."""

    def _get_use_case(self):
        return _build_use_case(
            InMemoryJobRepository(),
            InMemoryStageRepository(),
            InMemoryAuditEventRepository(),
            InMemoryArtifactStore(),
            InMemoryArtifactMetadataRepository(),
            FakeUUIDGenerator(),
        )

    def test_extracts_roles_and_images(self):
        uc = self._get_use_case()
        catalog = _make_catalog_json()
        meta = uc._extract_catalog_metadata(catalog, ImageGroupId("omnia-cluster-v1.2"))

        assert meta["image_group_id"] == "omnia-cluster-v1.2"
        assert sorted(meta["roles"]) == ["kube_node", "slurm_node"]
        assert meta["role_images"]["slurm_node"] == "slurm_node.img"
        assert meta["role_images"]["kube_node"] == "kube_node.img"
        assert meta["version"] == "1.0"

    def test_default_image_name_derived_from_role(self):
        uc = self._get_use_case()
        catalog = {
            "Catalog": {
                "Identifier": "my-group",
                "FunctionalLayer": [
                    {"Name": "worker", "FunctionalPackages": ["pkg1"]},
                ],
            }
        }
        meta = uc._extract_catalog_metadata(catalog, ImageGroupId("my-group"))
        assert meta["role_images"]["worker"] == "worker.img"

    def test_empty_functional_layer(self):
        uc = self._get_use_case()
        catalog = {"Catalog": {"Identifier": "my-group", "Version": "1.0"}}
        meta = uc._extract_catalog_metadata(catalog, ImageGroupId("my-group"))
        assert meta["roles"] == []
        assert meta["role_images"] == {}

    def test_skips_invalid_layer_entries(self):
        uc = self._get_use_case()
        catalog = {
            "Catalog": {
                "Identifier": "my-group",
                "FunctionalLayer": [
                    {"Name": "valid_role", "FunctionalPackages": []},
                    "not-a-dict",
                    {"Name": "", "FunctionalPackages": []},
                ],
            }
        }
        meta = uc._extract_catalog_metadata(catalog, ImageGroupId("my-group"))
        assert meta["roles"] == ["valid_role"]
        assert meta["role_images"] == {"valid_role": "valid_role.img"}


@pytest.mark.unit
class TestParseCatalogWithImageGroup:
    """Integration tests for full parse-catalog flow with ImageGroup features."""

    def test_successful_parse_includes_image_group_id(self):
        """Parse-catalog should return image_group_id in result."""
        job_repo = InMemoryJobRepository()
        stage_repo = InMemoryStageRepository()
        ig_repo = InMemoryImageGroupRepository()

        _setup_job_and_stage(job_repo, stage_repo)

        uc = _build_use_case(
            job_repo, stage_repo,
            InMemoryAuditEventRepository(),
            InMemoryArtifactStore(),
            InMemoryArtifactMetadataRepository(),
            FakeUUIDGenerator(),
            image_group_repo=ig_repo,
        )

        catalog = _make_catalog_json("test-cluster-v1")
        command = _make_command(content=_make_catalog_bytes(catalog))

        with patch(
            "orchestrator.catalog.use_cases.parse_catalog.generate_root_json_from_catalog"
        ):
            result = uc.execute(command)

        assert result.image_group_id == "test-cluster-v1"
        assert "kube_node" in result.roles
        assert "slurm_node" in result.roles
        assert result.role_images["slurm_node"] == "slurm_node.img"

    def test_duplicate_image_group_raises_409(self):
        """Parse-catalog should fail with DuplicateImageGroupError for existing group."""
        job_repo = InMemoryJobRepository()
        stage_repo = InMemoryStageRepository()
        ig_repo = InMemoryImageGroupRepository()

        _setup_job_and_stage(job_repo, stage_repo)

        # Pre-seed existing ImageGroup with the same Identifier
        from core.image_group.entities import ImageGroup
        existing = ImageGroup(
            id=ImageGroupId("existing-cluster"),
            job_id=JobId("00000000-0000-0000-0000-000000000099"),
            status=ImageGroupStatus.BUILT,
        )
        ig_repo.save(existing)

        uc = _build_use_case(
            job_repo, stage_repo,
            InMemoryAuditEventRepository(),
            InMemoryArtifactStore(),
            InMemoryArtifactMetadataRepository(),
            FakeUUIDGenerator(),
            image_group_repo=ig_repo,
        )

        catalog = _make_catalog_json("existing-cluster")
        command = _make_command(content=_make_catalog_bytes(catalog))

        with pytest.raises(DuplicateImageGroupError):
            uc.execute(command)

    def test_catalog_metadata_artifact_stored(self):
        """Parse-catalog should store catalog-metadata artifact."""
        job_repo = InMemoryJobRepository()
        stage_repo = InMemoryStageRepository()
        artifact_store = InMemoryArtifactStore()
        metadata_repo = InMemoryArtifactMetadataRepository()

        _setup_job_and_stage(job_repo, stage_repo)

        uc = _build_use_case(
            job_repo, stage_repo,
            InMemoryAuditEventRepository(),
            artifact_store, metadata_repo,
            FakeUUIDGenerator(),
            image_group_repo=InMemoryImageGroupRepository(),
        )

        catalog = _make_catalog_json("cluster-v2")
        command = _make_command(content=_make_catalog_bytes(catalog))

        with patch(
            "orchestrator.catalog.use_cases.parse_catalog.generate_root_json_from_catalog"
        ):
            uc.execute(command)

        # Verify catalog-metadata artifact was stored
        record = metadata_repo.find_by_job_stage_and_label(
            job_id=JobId(VALID_JOB_ID),
            stage_name=StageName(StageType.PARSE_CATALOG.value),
            label="catalog-metadata",
        )
        assert record is not None

        # Verify content
        from core.artifacts.value_objects import ArtifactKind
        raw = artifact_store.retrieve(record.artifact_ref.key, ArtifactKind.FILE)
        metadata = json.loads(raw.decode("utf-8"))
        assert metadata["image_group_id"] == "cluster-v2"
        assert "slurm_node" in metadata["role_images"]
        assert metadata["role_images"]["slurm_node"] == "slurm_node.img"


# ======================================================================
# Part B: Result Poller Build-Image Completion Tests
# ======================================================================


@pytest.mark.unit
class TestResultPollerBuildImageCompletion:
    """Tests for build-image completion handler in ResultPoller."""

    def test_is_build_image_stage(self):
        from orchestrator.common.result_poller import ResultPoller
        assert ResultPoller._is_build_image_stage("build-image-x86_64")
        assert ResultPoller._is_build_image_stage("build-image-aarch64")
        assert ResultPoller._is_build_image_stage("build-image")
        assert not ResultPoller._is_build_image_stage("parse-catalog")
        assert not ResultPoller._is_build_image_stage("deploy")

    @patch("orchestrator.common.result_poller._discover_s3_image_paths")
    def test_on_build_image_success_creates_records(self, mock_discover):
        """Build-image success should create ImageGroup + Images."""
        from orchestrator.common.result_poller import ResultPoller

        # Mock S3 discovery to return fake paths (no real s3cmd needed)
        mock_discover.return_value = {
            "slurm_node": [
                "s3://boot-images/efi-images/slurm_node/img-dir/",
                "s3://boot-images/slurm_node/img-dir/",
            ],
            "kube_node": [
                "s3://boot-images/efi-images/kube_node/img-dir/",
                "s3://boot-images/kube_node/img-dir/",
            ],
        }

        ig_repo = InMemoryImageGroupRepository()
        image_repo = InMemoryImageRepository()
        artifact_store = InMemoryArtifactStore()
        metadata_repo = InMemoryArtifactMetadataRepository()

        # Pre-seed catalog metadata artifact
        catalog_metadata = {
            "image_group_id": "test-cluster",
            "roles": ["slurm_node", "kube_node"],
            "role_images": {
                "slurm_node": "slurm_node.img",
                "kube_node": "kube_node.img",
            },
        }
        content = json.dumps(catalog_metadata).encode("utf-8")
        from core.artifacts.value_objects import StoreHint, ArtifactKind
        from core.artifacts.entities import ArtifactRecord
        hint = StoreHint(namespace="catalog", label="catalog-metadata",
                         tags={"job_id": VALID_JOB_ID})
        ref = artifact_store.store(hint=hint, kind=ArtifactKind.FILE,
                                   content=content, content_type="application/json")
        record = ArtifactRecord(
            id="test-record-id",
            job_id=JobId(VALID_JOB_ID),
            stage_name=StageName("parse-catalog"),
            label="catalog-metadata",
            artifact_ref=ref,
            kind=ArtifactKind.FILE,
            content_type="application/json",
            tags={},
        )
        metadata_repo.save(record)

        poller = ResultPoller(
            result_service=MagicMock(),
            job_repo=InMemoryJobRepository(),
            stage_repo=InMemoryStageRepository(),
            audit_repo=InMemoryAuditEventRepository(),
            uuid_generator=FakeUUIDGenerator(),
            image_group_repo=ig_repo,
            image_repo=image_repo,
            artifact_store=artifact_store,
            artifact_metadata_repo=metadata_repo,
        )

        # Create a mock result
        mock_result = MagicMock()
        mock_result.job_id = JobId(VALID_JOB_ID)
        mock_result.stage_name = "build-image-x86_64"

        poller._on_build_image_success(mock_result)

        # Verify ImageGroup was created
        ig = ig_repo.find_by_id(ImageGroupId("test-cluster"))
        assert ig is not None
        assert ig.status == ImageGroupStatus.BUILT
        assert str(ig.job_id) == VALID_JOB_ID

        # Verify one Image per role (paths semicolon-delimited)
        images = image_repo.find_by_image_group_id(
            ImageGroupId("test-cluster")
        )
        assert len(images) == 2
        role_names = {img.role for img in images}
        assert role_names == {"slurm_node", "kube_node"}
        for img in images:
            paths = img.image_name.split(";")
            assert len(paths) == 2
            assert all(p.startswith("s3://") for p in paths)

    def test_on_build_image_success_no_metadata_skips(self):
        """Build-image success without catalog metadata should skip."""
        from orchestrator.common.result_poller import ResultPoller

        ig_repo = InMemoryImageGroupRepository()
        poller = ResultPoller(
            result_service=MagicMock(),
            job_repo=InMemoryJobRepository(),
            stage_repo=InMemoryStageRepository(),
            audit_repo=InMemoryAuditEventRepository(),
            uuid_generator=FakeUUIDGenerator(),
            image_group_repo=ig_repo,
            image_repo=InMemoryImageRepository(),
            artifact_store=InMemoryArtifactStore(),
            artifact_metadata_repo=InMemoryArtifactMetadataRepository(),
        )

        mock_result = MagicMock()
        mock_result.job_id = JobId(VALID_JOB_ID)

        poller._on_build_image_success(mock_result)

        # No ImageGroup should have been created
        ig = ig_repo.find_by_id(ImageGroupId("test-cluster"))
        assert ig is None

    def test_on_build_image_success_no_repos_skips(self):
        """Build-image success without repos should skip gracefully."""
        from orchestrator.common.result_poller import ResultPoller

        poller = ResultPoller(
            result_service=MagicMock(),
            job_repo=InMemoryJobRepository(),
            stage_repo=InMemoryStageRepository(),
            audit_repo=InMemoryAuditEventRepository(),
            uuid_generator=FakeUUIDGenerator(),
            # No image_group_repo or image_repo
        )

        mock_result = MagicMock()
        mock_result.job_id = JobId(VALID_JOB_ID)

        # Should not raise
        poller._on_build_image_success(mock_result)
