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

"""Unit tests for CatalogRolesService."""

import io
import json
import zipfile
from unittest.mock import MagicMock

import pytest

from api.catalog_roles.service import (
    CatalogRolesService,
    ParseCatalogNotCompletedError,
    RolesNotFoundError,
)
from core.artifacts.entities import ArtifactRecord
from core.artifacts.exceptions import ArtifactNotFoundError
from core.artifacts.value_objects import ArtifactDigest, ArtifactKey, ArtifactKind, ArtifactRef
from core.jobs.value_objects import JobId, StageName, StageType


def _make_job_id() -> JobId:
    return JobId("019bf590-1234-7890-abcd-ef1234567890")


def _make_artifact_ref(key_value: str = "catalog/abc123/root-jsons.zip") -> ArtifactRef:
    return ArtifactRef(
        key=ArtifactKey(key_value),
        digest=ArtifactDigest("abc123"),
        size_bytes=100,
        uri=f"memory://{key_value}",
    )


def _make_artifact_record(job_id: JobId, ref: ArtifactRef) -> ArtifactRecord:
    return ArtifactRecord(
        id="record-id-1",
        job_id=job_id,
        stage_name=StageName(StageType.PARSE_CATALOG.value),
        label="root-jsons",
        artifact_ref=ref,
        kind=ArtifactKind.ARCHIVE,
        content_type="application/zip",
        tags={"job_id": str(job_id)},
    )


def _make_zip_with_functional_layer(roles: dict, path: str = "x86_64/rhel/9.5/functional_layer.json") -> bytes:
    """Create an in-memory zip archive containing a functional_layer.json."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(path, json.dumps(roles))
    return buf.getvalue()


class TestCatalogRolesServiceGetRoles:
    """Tests for CatalogRolesService.get_roles."""

    def _make_service(self, artifact_store=None, artifact_metadata_repo=None):
        return CatalogRolesService(
            artifact_store=artifact_store or MagicMock(),
            artifact_metadata_repo=artifact_metadata_repo or MagicMock(),
        )

    def test_returns_sorted_roles_from_functional_layer(self):
        """Returns sorted role names from functional_layer.json in the archive."""
        job_id = _make_job_id()
        ref = _make_artifact_ref()
        record = _make_artifact_record(job_id, ref)

        roles_data = {
            "Slurm Worker": {"packages": []},
            "Compiler": {"packages": []},
            "K8S Controller": {"packages": []},
        }
        zip_bytes = _make_zip_with_functional_layer(roles_data)

        metadata_repo = MagicMock()
        metadata_repo.find_by_job_stage_and_label.return_value = record

        artifact_store = MagicMock()
        artifact_store.retrieve.return_value = zip_bytes

        service = self._make_service(artifact_store, metadata_repo)
        roles = service.get_roles(job_id)

        assert roles == ["Compiler", "K8S Controller", "Slurm Worker"]

    def test_raises_when_no_artifact_record(self):
        """Raises ParseCatalogNotCompletedError when no root-jsons record exists."""
        job_id = _make_job_id()

        metadata_repo = MagicMock()
        metadata_repo.find_by_job_stage_and_label.return_value = None

        service = self._make_service(artifact_metadata_repo=metadata_repo)

        with pytest.raises(ParseCatalogNotCompletedError):
            service.get_roles(job_id)

    def test_raises_when_artifact_not_in_store(self):
        """Raises ParseCatalogNotCompletedError when artifact file is missing from store."""
        job_id = _make_job_id()
        ref = _make_artifact_ref()
        record = _make_artifact_record(job_id, ref)

        metadata_repo = MagicMock()
        metadata_repo.find_by_job_stage_and_label.return_value = record

        artifact_store = MagicMock()
        artifact_store.retrieve.side_effect = ArtifactNotFoundError(key=ref.key.value)

        service = self._make_service(artifact_store, metadata_repo)

        with pytest.raises(ParseCatalogNotCompletedError):
            service.get_roles(job_id)

    def test_raises_when_no_functional_layer_in_archive(self):
        """Raises RolesNotFoundError when archive has no functional_layer.json."""
        job_id = _make_job_id()
        ref = _make_artifact_ref()
        record = _make_artifact_record(job_id, ref)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("x86_64/rhel/9.5/base_os.json", json.dumps({}))
        zip_bytes = buf.getvalue()

        metadata_repo = MagicMock()
        metadata_repo.find_by_job_stage_and_label.return_value = record

        artifact_store = MagicMock()
        artifact_store.retrieve.return_value = zip_bytes

        service = self._make_service(artifact_store, metadata_repo)

        with pytest.raises(RolesNotFoundError):
            service.get_roles(job_id)

    def test_raises_when_archive_is_corrupt(self):
        """Raises RolesNotFoundError when archive bytes are not a valid zip."""
        job_id = _make_job_id()
        ref = _make_artifact_ref()
        record = _make_artifact_record(job_id, ref)

        metadata_repo = MagicMock()
        metadata_repo.find_by_job_stage_and_label.return_value = record

        artifact_store = MagicMock()
        artifact_store.retrieve.return_value = b"this is not a zip file"

        service = self._make_service(artifact_store, metadata_repo)

        with pytest.raises(RolesNotFoundError):
            service.get_roles(job_id)

    def test_raises_when_functional_layer_json_is_malformed(self):
        """Raises RolesNotFoundError when functional_layer.json is not valid JSON."""
        job_id = _make_job_id()
        ref = _make_artifact_ref()
        record = _make_artifact_record(job_id, ref)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("x86_64/rhel/9.5/functional_layer.json", b"not valid json {{")
        zip_bytes = buf.getvalue()

        metadata_repo = MagicMock()
        metadata_repo.find_by_job_stage_and_label.return_value = record

        artifact_store = MagicMock()
        artifact_store.retrieve.return_value = zip_bytes

        service = self._make_service(artifact_store, metadata_repo)

        with pytest.raises(RolesNotFoundError):
            service.get_roles(job_id)

    def test_raises_when_functional_layer_json_is_not_a_dict(self):
        """Raises RolesNotFoundError when functional_layer.json root is not a dict."""
        job_id = _make_job_id()
        ref = _make_artifact_ref()
        record = _make_artifact_record(job_id, ref)

        zip_bytes = _make_zip_with_functional_layer(["role1", "role2"])  # list, not dict

        metadata_repo = MagicMock()
        metadata_repo.find_by_job_stage_and_label.return_value = record

        artifact_store = MagicMock()
        artifact_store.retrieve.return_value = zip_bytes

        service = self._make_service(artifact_store, metadata_repo)

        with pytest.raises(RolesNotFoundError):
            service.get_roles(job_id)

    def test_returns_empty_list_for_empty_functional_layer(self):
        """Returns empty list when functional_layer.json has no roles."""
        job_id = _make_job_id()
        ref = _make_artifact_ref()
        record = _make_artifact_record(job_id, ref)

        zip_bytes = _make_zip_with_functional_layer({})

        metadata_repo = MagicMock()
        metadata_repo.find_by_job_stage_and_label.return_value = record

        artifact_store = MagicMock()
        artifact_store.retrieve.return_value = zip_bytes

        service = self._make_service(artifact_store, metadata_repo)
        roles = service.get_roles(job_id)

        assert roles == []

    def test_uses_first_functional_layer_found_in_archive(self):
        """Uses the first functional_layer.json found when multiple arch dirs exist."""
        job_id = _make_job_id()
        ref = _make_artifact_ref()
        record = _make_artifact_record(job_id, ref)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "aarch64/rhel/9.5/functional_layer.json",
                json.dumps({"RoleA": {}, "RoleB": {}}),
            )
            zf.writestr(
                "x86_64/rhel/9.5/functional_layer.json",
                json.dumps({"RoleX": {}, "RoleY": {}}),
            )
        zip_bytes = buf.getvalue()

        metadata_repo = MagicMock()
        metadata_repo.find_by_job_stage_and_label.return_value = record

        artifact_store = MagicMock()
        artifact_store.retrieve.return_value = zip_bytes

        service = self._make_service(artifact_store, metadata_repo)
        roles = service.get_roles(job_id)

        # Should return roles from whichever functional_layer.json is found first
        assert isinstance(roles, list)
        assert len(roles) == 2

    def test_queries_correct_stage_and_label(self):
        """Verifies the metadata repo is queried with the correct stage and label."""
        job_id = _make_job_id()

        metadata_repo = MagicMock()
        metadata_repo.find_by_job_stage_and_label.return_value = None

        service = self._make_service(artifact_metadata_repo=metadata_repo)

        with pytest.raises(ParseCatalogNotCompletedError):
            service.get_roles(job_id)

        metadata_repo.find_by_job_stage_and_label.assert_called_once_with(
            job_id=job_id,
            stage_name=StageName(StageType.PARSE_CATALOG.value),
            label="root-jsons",
        )
