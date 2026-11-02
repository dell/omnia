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

# pylint: disable=protected-access,import-outside-toplevel,too-many-arguments
# pylint: disable=too-many-positional-arguments,too-many-locals,too-few-public-methods

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from core.image_group.exceptions import DuplicateImageGroupError
from core.image_group.value_objects import ImageGroupId, ImageGroupStatus
from core.jobs.value_objects import JobId, StageName
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
from orchestrator.catalog.use_cases.parse_catalog import ParseCatalogUseCase


VALID_JOB_ID = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"


class FakeUUIDGenerator:
    """Deterministic UUID generator for tests."""

    def __init__(self):
        self._counter = 0

    def generate(self):
        """Generate a deterministic UUID for testing."""
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
class TestCheckImageGroupUniqueness:
    """Tests for _check_image_group_uniqueness()."""

    def test_unique_id_passes(self):
        """Test unique image group ID passes validation."""
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
        """Test duplicate image group ID raises error."""
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
        """Test that check is skipped when no repo is provided."""
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
        """Helper to build a use case instance."""
        return _build_use_case(
            InMemoryJobRepository(),
            InMemoryStageRepository(),
            InMemoryAuditEventRepository(),
            InMemoryArtifactStore(),
            InMemoryArtifactMetadataRepository(),
            FakeUUIDGenerator(),
        )

    def test_extracts_roles_and_images(self):
        """Test extraction of roles and images from catalog."""
        uc = self._get_use_case()
        catalog = _make_catalog_json()
        meta = uc._extract_catalog_metadata(catalog)

        assert meta["image_group_id"] == "omnia-cluster-v1.2"
        assert sorted(meta["roles"]) == ["kube_node", "slurm_node"]
        assert meta["role_images"]["slurm_node"] == "slurm_node.img"
        assert meta["role_images"]["kube_node"] == "kube_node.img"
        assert meta["version"] == "1.0"

    def test_default_image_name_derived_from_role(self):
        """Test default image name is derived from role name."""
        uc = self._get_use_case()
        catalog = {
            "Catalog": {
                "Identifier": "my-group",
                "FunctionalLayer": [
                    {"Name": "worker", "FunctionalPackages": ["pkg1"]},
                ],
            }
        }
        meta = uc._extract_catalog_metadata(catalog)
        assert meta["role_images"]["worker"] == "worker.img"

    def test_empty_functional_layer(self):
        """Test empty functional layer is handled correctly."""
        uc = self._get_use_case()
        catalog = {"Catalog": {"Identifier": "my-group", "Version": "1.0"}}
        meta = uc._extract_catalog_metadata(catalog)
        assert meta["roles"] == []
        assert meta["role_images"] == {}

    def test_skips_invalid_layer_entries(self):
        """Test that invalid layer entries are skipped."""
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
        meta = uc._extract_catalog_metadata(catalog)
        assert meta["roles"] == ["valid_role"]
        assert meta["role_images"] == {"valid_role": "valid_role.img"}

    @pytest.mark.parametrize(
        "identifier",
        [
            "../../../../etc/passwd",
            "a;id",
            "a$(id)",
            "a b",
            " lead",
            ".hidden",
            "a" * 129,
            123,
            ["x"],
        ],
    )
    def test_rejects_unsafe_identifier(self, identifier):
        """An Identifier outside the safe set is rejected with a 400-class error."""
        from core.catalog.exceptions import InvalidCatalogFormatError

        uc = self._get_use_case()
        catalog = {"Catalog": {"Identifier": identifier, "Version": "1.0"}}
        with pytest.raises(InvalidCatalogFormatError):
            uc._extract_catalog_metadata(catalog)

    @pytest.mark.parametrize("version", ["1 0", "1;id", "../x", {"a": 1}])
    def test_rejects_unsafe_version(self, version):
        """A Version that makes the composite ID unsafe is rejected."""
        from core.catalog.exceptions import InvalidCatalogFormatError

        uc = self._get_use_case()
        catalog = {"Catalog": {"Identifier": "my-group", "Version": version}}
        with pytest.raises(InvalidCatalogFormatError):
            uc._extract_catalog_metadata(catalog)


# ======================================================================
# Part B: Result Poller Build-Image Completion Tests
# ======================================================================


@pytest.mark.unit
class TestResultPollerBuildImageCompletion:
    """Tests for build-image completion handler in ResultPoller."""

    def test_is_build_image_stage(self):
        """Test build-image stage detection."""
        from orchestrator.common.result_poller import ResultPoller
        # Unified design (Omnia 2.3+): only "build-image" stage exists
        assert ResultPoller._is_build_image_stage("build-image")
        # Retired arch-specific stage names are no longer recognized
        assert not ResultPoller._is_build_image_stage("build-image-x86_64")
        assert not ResultPoller._is_build_image_stage("build-image-aarch64")
        # Other stages should not be recognized
        assert not ResultPoller._is_build_image_stage("create-local-repository")
        assert not ResultPoller._is_build_image_stage("deploy")

    @patch("orchestrator.common.result_poller._discover_s3_image_paths")
    def test_on_build_image_success_creates_records(self, mock_discover):
        """Build-image success should create ImageGroup + Images."""

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

        from orchestrator.common.result_poller import ResultPoller
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
        mock_result.stage_name = "build-image"

        poller._on_build_image_success(mock_result)

        # Verify ImageGroup was created
        ig = ig_repo.find_by_id(ImageGroupId("test-cluster"))
        assert ig is not None, "ImageGroup should have been created"
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
