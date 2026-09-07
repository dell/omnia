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

"""Unit tests for InMemoryArtifactStore."""

import hashlib
from pathlib import Path

import pytest

from core.artifacts.exceptions import (
    ArtifactAlreadyExistsError,
    ArtifactNotFoundError,
    ArtifactValidationError,
)
from core.artifacts.value_objects import ArtifactKind, StoreHint
from infra.artifact_store.in_memory_artifact_store import InMemoryArtifactStore


class TestStoreFile:
    """Tests for storing FILE artifacts."""

    def test_store_file_returns_artifact_ref(
        self, artifact_store, file_hint, sample_content
    ) -> None:
        """Test that storing a file artifact returns a valid ArtifactRef."""
        ref = artifact_store.store(
            hint=file_hint,
            kind=ArtifactKind.FILE,
            content=sample_content,
            content_type="application/json",
        )
        assert ref.key is not None
        assert ref.digest is not None
        assert ref.size_bytes == len(sample_content)
        assert ref.uri.startswith("memory://")

    def test_store_file_computes_sha256(
        self, artifact_store, file_hint, sample_content
    ) -> None:
        """Test that storing a file computes correct SHA256 digest."""
        ref = artifact_store.store(
            hint=file_hint,
            kind=ArtifactKind.FILE,
            content=sample_content,
            content_type="application/json",
        )
        expected = hashlib.sha256(sample_content).hexdigest()
        assert str(ref.digest) == expected

    def test_store_file_rejects_overwrite(
        self, artifact_store, file_hint, sample_content
    ) -> None:
        """Test that storing duplicate file artifacts raises ArtifactAlreadyExistsError."""
        artifact_store.store(
            hint=file_hint,
            kind=ArtifactKind.FILE,
            content=sample_content,
            content_type="application/json",
        )
        with pytest.raises(ArtifactAlreadyExistsError):
            artifact_store.store(
                hint=file_hint,
                kind=ArtifactKind.FILE,
                content=sample_content,
                content_type="application/json",
            )

    def test_store_file_without_content_raises(
        self, artifact_store, file_hint
    ) -> None:
        """Test that storing file without content raises ValueError."""
        with pytest.raises(ValueError, match="content is required"):
            artifact_store.store(
                hint=file_hint,
                kind=ArtifactKind.FILE,
                content_type="application/json",
            )

    def test_store_file_with_file_map_raises(
        self, artifact_store, file_hint, sample_content
    ) -> None:
        """Test that storing file with file_map raises ValueError."""
        with pytest.raises(ValueError, match="must not be provided for FILE"):
            artifact_store.store(
                hint=file_hint,
                kind=ArtifactKind.FILE,
                content=sample_content,
                file_map={"a.json": b"{}"},
                content_type="application/json",
            )


class TestStoreArchive:
    """Tests for storing ARCHIVE artifacts."""

    def test_store_archive_from_file_map(
        self, artifact_store, archive_hint, sample_file_map
    ) -> None:
        """Test that storing archive from file_map returns valid ArtifactRef."""
        ref = artifact_store.store(
            hint=archive_hint,
            kind=ArtifactKind.ARCHIVE,
            file_map=sample_file_map,
            content_type="application/zip",
        )
        assert ref.key is not None
        assert ref.size_bytes > 0

    def test_store_archive_from_directory(
        self, artifact_store, archive_hint, tmp_path
    ) -> None:
        """Test that storing archive from directory returns valid ArtifactRef."""
        # Create temp directory with files
        (tmp_path / "a.json").write_bytes(b'{"a": 1}')
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.json").write_bytes(b'{"b": 2}')

        ref = artifact_store.store(
            hint=archive_hint,
            kind=ArtifactKind.ARCHIVE,
            source_directory=tmp_path,
            content_type="application/zip",
        )
        assert ref.key is not None
        assert ref.size_bytes > 0

    def test_store_archive_without_inputs_raises(
        self, artifact_store, archive_hint
    ) -> None:
        """Test that storing archive without file_map or source_directory raises ValueError."""
        with pytest.raises(ValueError, match="Either file_map or source_directory"):
            artifact_store.store(
                hint=archive_hint,
                kind=ArtifactKind.ARCHIVE,
                content_type="application/zip",
            )

    def test_store_archive_with_both_inputs_raises(
        self, artifact_store, archive_hint, tmp_path
    ) -> None:
        """Test that storing archive with both file_map and source_directory raises ValueError."""
        with pytest.raises(ValueError, match="not both"):
            artifact_store.store(
                hint=archive_hint,
                kind=ArtifactKind.ARCHIVE,
                file_map={"a.json": b"{}"},
                source_directory=tmp_path,
                content_type="application/zip",
            )

    def test_store_archive_with_content_raises(
        self, artifact_store, archive_hint
    ) -> None:
        """Test that storing archive with content parameter raises ValueError."""
        with pytest.raises(ValueError, match="must not be provided for ARCHIVE"):
            artifact_store.store(
                hint=archive_hint,
                kind=ArtifactKind.ARCHIVE,
                content=b"raw bytes",
                content_type="application/zip",
            )

    def test_store_archive_nonexistent_dir_raises(
        self, artifact_store, archive_hint
    ) -> None:
        """Test that storing archive with nonexistent directory raises ValueError."""
        with pytest.raises(ValueError, match="does not exist"):
            artifact_store.store(
                hint=archive_hint,
                kind=ArtifactKind.ARCHIVE,
                source_directory=Path("/nonexistent/dir"),
                content_type="application/zip",
            )


class TestRetrieve:
    """Tests for retrieving artifacts."""

    def test_retrieve_file(
        self, artifact_store, file_hint, sample_content
    ) -> None:
        """Test that retrieving a file artifact returns original content."""
        ref = artifact_store.store(
            hint=file_hint,
            kind=ArtifactKind.FILE,
            content=sample_content,
            content_type="application/json",
        )
        result = artifact_store.retrieve(
            key=ref.key, kind=ArtifactKind.FILE
        )
        assert result == sample_content

    def test_retrieve_archive(
        self, artifact_store, archive_hint, sample_file_map, tmp_path
    ) -> None:
        """Test that retrieving an archive extracts files to destination."""
        ref = artifact_store.store(
            hint=archive_hint,
            kind=ArtifactKind.ARCHIVE,
            file_map=sample_file_map,
            content_type="application/zip",
        )
        dest = tmp_path / "output"
        result = artifact_store.retrieve(
            key=ref.key, kind=ArtifactKind.ARCHIVE, destination=dest
        )
        assert isinstance(result, Path)
        # Check unpacked files exist
        for rel_path in sample_file_map:
            assert (result / rel_path).exists()

    def test_retrieve_archive_without_destination(
        self, artifact_store, archive_hint, sample_file_map
    ) -> None:
        """Test that retrieving archive without destination raises ValueError."""
        ref = artifact_store.store(
            hint=archive_hint,
            kind=ArtifactKind.ARCHIVE,
            file_map=sample_file_map,
            content_type="application/zip",
        )
        result = artifact_store.retrieve(
            key=ref.key, kind=ArtifactKind.ARCHIVE
        )
        assert isinstance(result, Path)
        assert result.is_dir()

    def test_retrieve_not_found_raises(self, artifact_store) -> None:
        """Test that retrieving nonexistent artifact raises ArtifactNotFoundError."""
        from core.artifacts.value_objects import ArtifactKey

        key = ArtifactKey("nonexistent/key/file.bin")
        with pytest.raises(ArtifactNotFoundError):
            artifact_store.retrieve(key=key, kind=ArtifactKind.FILE)


class TestExistsAndDelete:
    """Tests for exists and delete operations."""

    def test_exists_true_after_store(
        self, artifact_store, file_hint, sample_content
    ) -> None:
        """Test that exists returns True after storing artifact."""
        ref = artifact_store.store(
            hint=file_hint,
            kind=ArtifactKind.FILE,
            content=sample_content,
            content_type="application/json",
        )
        assert artifact_store.exists(ref.key) is True

    def test_exists_false_before_store(self, artifact_store) -> None:
        """Test that exists returns False for nonexistent artifact."""
        from core.artifacts.value_objects import ArtifactKey

        key = ArtifactKey("nonexistent/key/file.bin")
        assert artifact_store.exists(key) is False

    def test_delete_returns_true(
        self, artifact_store, file_hint, sample_content
    ) -> None:
        """Test that delete returns True and removes existing artifact."""
        ref = artifact_store.store(
            hint=file_hint,
            kind=ArtifactKind.FILE,
            content=sample_content,
            content_type="application/json",
        )
        assert artifact_store.delete(ref.key) is True
        assert artifact_store.exists(ref.key) is False

    def test_delete_returns_false_not_found(self, artifact_store) -> None:
        """Test that delete returns False for nonexistent artifact."""
        from core.artifacts.value_objects import ArtifactKey

        key = ArtifactKey("nonexistent/key/file.bin")
        assert artifact_store.delete(key) is False


class TestValidation:
    """Tests for content validation."""

    def test_disallowed_content_type_raises(
        self, artifact_store, file_hint
    ) -> None:
        """Test that disallowed content type raises ArtifactValidationError."""
        with pytest.raises(ArtifactValidationError, match="not allowed"):
            artifact_store.store(
                hint=file_hint,
                kind=ArtifactKind.FILE,
                content=b"data",
                content_type="image/png",
            )

    def test_oversized_content_raises(self, file_hint) -> None:
        """Test that oversized content raises ArtifactValidationError."""
        store = InMemoryArtifactStore(max_artifact_size_bytes=10)
        with pytest.raises(ArtifactValidationError, match="exceeds maximum"):
            store.store(
                hint=file_hint,
                kind=ArtifactKind.FILE,
                content=b"x" * 11,
                content_type="application/json",
            )


class TestGenerateKey:
    """Tests for deterministic key generation."""

    def test_deterministic_key(self, artifact_store, file_hint) -> None:
        """Test that generate_key returns same key for same hint."""
        key1 = artifact_store.generate_key(file_hint, ArtifactKind.FILE)
        key2 = artifact_store.generate_key(file_hint, ArtifactKind.FILE)
        assert key1 == key2

    def test_different_hints_different_keys(self, artifact_store) -> None:
        """Test that different hints generate different keys."""
        hint1 = StoreHint(namespace="ns", label="a", tags={"k": "v1"})
        hint2 = StoreHint(namespace="ns", label="a", tags={"k": "v2"})
        key1 = artifact_store.generate_key(hint1, ArtifactKind.FILE)
        key2 = artifact_store.generate_key(hint2, ArtifactKind.FILE)
        assert key1 != key2

    def test_file_key_has_bin_extension(self, artifact_store, file_hint) -> None:
        """Test that file keys have .bin extension."""
        key = artifact_store.generate_key(file_hint, ArtifactKind.FILE)
        assert key.value.endswith(".bin")

    def test_archive_key_has_zip_extension(
        self, artifact_store, archive_hint
    ) -> None:
        """Test that archive keys have .zip extension."""
        key = artifact_store.generate_key(archive_hint, ArtifactKind.ARCHIVE)
        assert key.value.endswith(".zip")
