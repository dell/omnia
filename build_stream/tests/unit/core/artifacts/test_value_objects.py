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

"""Unit tests for Artifact domain value objects."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from core.artifacts.value_objects import (
    ArtifactDigest,
    ArtifactKey,
    ArtifactKind,
    ArtifactRef,
    SafePath,
    StoreHint,
)


# ---------------------------------------------------------------------------
# SafePath
# ---------------------------------------------------------------------------

class TestSafePath:
    """Tests for SafePath value object."""

    def test_valid_path(self) -> None:
        sp = SafePath(value=Path("/opt/artifacts/store"))
        assert sp.value == Path("/opt/artifacts/store")

    def test_from_string(self) -> None:
        sp = SafePath.from_string("/opt/artifacts/store")
        assert sp.value == Path("/opt/artifacts/store")

    def test_empty_path_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            SafePath(value=Path(""))

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            SafePath(value=Path("   "))

    def test_path_too_long_raises(self) -> None:
        long_path = "a" * (SafePath.MAX_LENGTH + 1)
        with pytest.raises(ValueError, match="cannot exceed"):
            SafePath.from_string(long_path)

    def test_traversal_dot_dot_raises(self) -> None:
        with pytest.raises(ValueError, match="traversal"):
            SafePath.from_string("/opt/../etc/passwd")

    def test_relative_path_with_dots_in_name_allowed(self) -> None:
        sp = SafePath.from_string("/opt/my..file.tar.gz")
        assert "my..file.tar.gz" in str(sp)

    def test_traversal_encoded_raises(self) -> None:
        with pytest.raises(ValueError, match="traversal"):
            SafePath.from_string("/opt/%2e%2e/etc")

    def test_null_byte_raises(self) -> None:
        with pytest.raises(ValueError, match="null bytes"):
            SafePath.from_string("/opt/file\x00.json")

    def test_immutable(self) -> None:
        sp = SafePath(value=Path("/opt/store"))
        with pytest.raises(FrozenInstanceError):
            sp.value = Path("/other")  # type: ignore[misc]

    def test_str_representation(self) -> None:
        sp = SafePath.from_string("/opt/store")
        assert str(sp) == str(Path("/opt/store"))


# ---------------------------------------------------------------------------
# ArtifactKey
# ---------------------------------------------------------------------------

class TestArtifactKey:
    """Tests for ArtifactKey value object."""

    def test_valid_key(self) -> None:
        key = ArtifactKey("catalog/abc123/file.bin")
        assert key.value == "catalog/abc123/file.bin"

    def test_empty_key_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            ArtifactKey("")

    def test_whitespace_key_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            ArtifactKey("   ")

    def test_key_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot exceed"):
            ArtifactKey("a" * 513)

    def test_traversal_dot_dot_raises(self) -> None:
        with pytest.raises(ValueError, match="traversal"):
            ArtifactKey("../../../etc/passwd")

    def test_traversal_backslash_raises(self) -> None:
        with pytest.raises(ValueError, match="traversal or backslash"):
            ArtifactKey("catalog\\file.bin")

    def test_absolute_path_raises(self) -> None:
        with pytest.raises(ValueError, match="absolute path"):
            ArtifactKey("/etc/passwd")

    def test_null_byte_raises(self) -> None:
        with pytest.raises(ValueError, match="null bytes"):
            ArtifactKey("file\x00.json")

    def test_immutable(self) -> None:
        key = ArtifactKey("catalog/file.bin")
        with pytest.raises(FrozenInstanceError):
            key.value = "other"  # type: ignore[misc]

    def test_str_representation(self) -> None:
        key = ArtifactKey("catalog/file.bin")
        assert str(key) == "catalog/file.bin"


# ---------------------------------------------------------------------------
# ArtifactDigest
# ---------------------------------------------------------------------------

class TestArtifactDigest:
    """Tests for ArtifactDigest value object."""

    def test_valid_digest(self) -> None:
        digest = ArtifactDigest("a" * 64)
        assert digest.value == "a" * 64

    def test_short_digest_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid SHA-256"):
            ArtifactDigest("a" * 63)

    def test_long_digest_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot exceed"):
            ArtifactDigest("a" * 65)

    def test_uppercase_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid SHA-256"):
            ArtifactDigest("A" * 64)

    def test_non_hex_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid SHA-256"):
            ArtifactDigest("g" * 64)

    def test_immutable(self) -> None:
        digest = ArtifactDigest("a" * 64)
        with pytest.raises(FrozenInstanceError):
            digest.value = "b" * 64  # type: ignore[misc]

    def test_str_representation(self) -> None:
        digest = ArtifactDigest("a" * 64)
        assert str(digest) == "a" * 64


# ---------------------------------------------------------------------------
# ArtifactRef
# ---------------------------------------------------------------------------

class TestArtifactRef:
    """Tests for ArtifactRef value object."""

    def test_valid_ref(self, valid_artifact_key, valid_digest) -> None:
        ref = ArtifactRef(
            key=valid_artifact_key,
            digest=valid_digest,
            size_bytes=1024,
            uri="memory://test",
        )
        assert ref.size_bytes == 1024

    def test_zero_size_allowed(self, valid_artifact_key, valid_digest) -> None:
        ref = ArtifactRef(
            key=valid_artifact_key,
            digest=valid_digest,
            size_bytes=0,
            uri="memory://test",
        )
        assert ref.size_bytes == 0

    def test_negative_size_raises(self, valid_artifact_key, valid_digest) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            ArtifactRef(
                key=valid_artifact_key,
                digest=valid_digest,
                size_bytes=-1,
                uri="memory://test",
            )

    def test_empty_uri_raises(self, valid_artifact_key, valid_digest) -> None:
        with pytest.raises(ValueError, match="URI cannot be empty"):
            ArtifactRef(
                key=valid_artifact_key,
                digest=valid_digest,
                size_bytes=100,
                uri="",
            )

    def test_uri_too_long_raises(self, valid_artifact_key, valid_digest) -> None:
        with pytest.raises(ValueError, match="URI length cannot exceed"):
            ArtifactRef(
                key=valid_artifact_key,
                digest=valid_digest,
                size_bytes=100,
                uri="x" * 4097,
            )

    def test_immutable(self, valid_artifact_ref) -> None:
        with pytest.raises(FrozenInstanceError):
            valid_artifact_ref.size_bytes = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ArtifactKind
# ---------------------------------------------------------------------------

class TestArtifactKind:
    """Tests for ArtifactKind enum."""

    def test_file_value(self) -> None:
        assert ArtifactKind.FILE.value == "FILE"

    def test_archive_value(self) -> None:
        assert ArtifactKind.ARCHIVE.value == "ARCHIVE"

    def test_string_comparison(self) -> None:
        assert ArtifactKind.FILE == "FILE"
        assert ArtifactKind.ARCHIVE == "ARCHIVE"


# ---------------------------------------------------------------------------
# StoreHint
# ---------------------------------------------------------------------------

class TestStoreHint:
    """Tests for StoreHint value object."""

    def test_valid_hint(self) -> None:
        hint = StoreHint(
            namespace="catalog",
            label="catalog-file",
            tags={"job_id": "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"},
        )
        assert hint.namespace == "catalog"
        assert hint.label == "catalog-file"

    def test_empty_namespace_raises(self) -> None:
        with pytest.raises(ValueError, match="namespace cannot be empty"):
            StoreHint(namespace="", label="file", tags={})

    def test_namespace_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="namespace length cannot exceed"):
            StoreHint(namespace="a" * 129, label="file", tags={})

    def test_empty_label_raises(self) -> None:
        with pytest.raises(ValueError, match="label cannot be empty"):
            StoreHint(namespace="ns", label="", tags={})

    def test_label_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="label length cannot exceed"):
            StoreHint(namespace="ns", label="a" * 129, tags={})

    def test_too_many_tags_raises(self) -> None:
        tags = {f"key{i}": f"val{i}" for i in range(21)}
        with pytest.raises(ValueError, match="cannot have more than"):
            StoreHint(namespace="ns", label="file", tags=tags)

    def test_tag_key_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="Tag key length"):
            StoreHint(namespace="ns", label="file", tags={"k" * 65: "v"})

    def test_tag_value_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="Tag value length"):
            StoreHint(namespace="ns", label="file", tags={"k": "v" * 257})

    def test_empty_tags_allowed(self) -> None:
        hint = StoreHint(namespace="ns", label="file", tags={})
        assert hint.tags == {}

    def test_immutable(self) -> None:
        hint = StoreHint(namespace="ns", label="file", tags={})
        with pytest.raises(FrozenInstanceError):
            hint.namespace = "other"  # type: ignore[misc]
