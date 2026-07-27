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

"""Value objects for Artifact domain.

All value objects are immutable and defined by their values, not identity.
"""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import ClassVar, Dict, Optional


class ArtifactKind(str, Enum):
    """Shape of artifact content.

    FILE: Single file (e.g., catalog.json).
    ARCHIVE: Multiple files packed as a zip archive.
    """

    FILE = "FILE"
    ARCHIVE = "ARCHIVE"


@dataclass(frozen=True)
class SafePath:
    """Validated filesystem path value object.

    Wraps pathlib.Path with security validation to prevent
    path traversal attacks and enforce length constraints.

    Attributes:
        value: The validated Path object.

    Raises:
        ValueError: If path is empty, too long, or contains traversal sequences.
    """

    value: Path

    MAX_LENGTH: ClassVar[int] = 4096
    ENCODED_TRAVERSAL_PATTERNS: ClassVar[tuple] = ("%2e%2e", "%2E%2E")

    def __post_init__(self) -> None:
        """Validate path safety and length."""
        str_value = str(self.value)
        # Path("") resolves to "." in Python, so check original parts too
        if not str_value or not str_value.strip() or str_value == ".":
            raise ValueError("SafePath cannot be empty")
        if len(str_value) > self.MAX_LENGTH:
            raise ValueError(
                f"SafePath length cannot exceed {self.MAX_LENGTH} characters, "
                f"got {len(str_value)}"
            )
        # Check for '..' as a path component (directory traversal)
        if ".." in self.value.parts:
            raise ValueError(
                "SafePath must not contain path traversal component: .."
            )
        for pattern in self.ENCODED_TRAVERSAL_PATTERNS:
            if pattern in str_value:
                raise ValueError(
                    f"SafePath must not contain path traversal sequence: {pattern}"
                )
        if "\x00" in str_value:
            raise ValueError("SafePath must not contain null bytes")

    @classmethod
    def from_string(cls, path_str: str) -> "SafePath":
        """Create SafePath from a string.

        Args:
            path_str: String representation of the path.

        Returns:
            Validated SafePath instance.
        """
        return cls(value=Path(path_str))

    def __str__(self) -> str:
        """Return string representation."""
        return str(self.value)


@dataclass(frozen=True)
class ArtifactKey:
    """Unique key identifying an artifact in the store.

    Generated deterministically from StoreHint components.

    Attributes:
        value: Key string (e.g., "catalog/abc123/catalog-file.json").

    Raises:
        ValueError: If value is empty, too long, or contains traversal.
    """

    value: str

    MIN_LENGTH: ClassVar[int] = 1
    MAX_LENGTH: ClassVar[int] = 512

    def __post_init__(self) -> None:
        """Validate key format and length."""
        if not self.value or not self.value.strip():
            raise ValueError("ArtifactKey cannot be empty")
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"ArtifactKey length cannot exceed {self.MAX_LENGTH} characters, "
                f"got {len(self.value)}"
            )
        if ".." in self.value or "\\" in self.value:
            raise ValueError(
                f"ArtifactKey must not contain path traversal or backslash: {self.value}"
            )
        if self.value.startswith("/"):
            raise ValueError(
                f"ArtifactKey must not be an absolute path: {self.value}"
            )
        if "\x00" in self.value:
            raise ValueError("ArtifactKey must not contain null bytes")

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


@dataclass(frozen=True)
class ArtifactDigest:
    """SHA-256 hex digest of artifact content.

    Attributes:
        value: 64-character lowercase hex string.

    Raises:
        ValueError: If value does not match SHA-256 pattern.
    """

    value: str

    SHA256_PATTERN: ClassVar[str] = r"^[0-9a-f]{64}$"
    MAX_LENGTH: ClassVar[int] = 64

    def __post_init__(self) -> None:
        """Validate SHA-256 format."""
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"ArtifactDigest length cannot exceed {self.MAX_LENGTH} characters, "
                f"got {len(self.value)}"
            )
        if not re.match(self.SHA256_PATTERN, self.value):
            raise ValueError(
                f"Invalid SHA-256 hex digest: {self.value}. "
                f"Expected 64 lowercase hexadecimal characters."
            )

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


@dataclass(frozen=True)
class ArtifactRef:
    """Immutable reference to a stored artifact.

    Returned by ArtifactStore.store() after successful storage.

    Attributes:
        key: Unique artifact key.
        digest: SHA-256 content digest.
        size_bytes: Content size in bytes.
        uri: Storage-specific location URI.

    Raises:
        ValueError: If any field is invalid.
    """

    key: ArtifactKey
    digest: ArtifactDigest
    size_bytes: int
    uri: str

    URI_MAX_LENGTH: ClassVar[int] = 4096

    def __post_init__(self) -> None:
        """Validate artifact reference fields."""
        if self.size_bytes < 0:
            raise ValueError(
                f"size_bytes must be non-negative, got {self.size_bytes}"
            )
        if not self.uri:
            raise ValueError("ArtifactRef URI cannot be empty")
        if len(self.uri) > self.URI_MAX_LENGTH:
            raise ValueError(
                f"ArtifactRef URI length cannot exceed {self.URI_MAX_LENGTH} "
                f"characters, got {len(self.uri)}"
            )


@dataclass(frozen=True)
class StoreHint:
    """Hints for deterministic artifact key generation.

    Callers provide hints so the store can generate a deterministic,
    collision-free key. The namespace groups artifacts logically,
    the label identifies the artifact within a stage, and tags
    provide additional disambiguation (e.g., job_id).

    Attributes:
        namespace: Logical grouping (e.g., "catalog", "input-files").
        label: Human-readable artifact name (e.g., "catalog-file", "root-jsons").
        tags: Key-value metadata for disambiguation and queryability.

    Raises:
        ValueError: If namespace or label is invalid.
    """

    namespace: str
    label: str
    tags: Dict[str, str]

    NAMESPACE_MAX_LENGTH: ClassVar[int] = 128
    LABEL_MAX_LENGTH: ClassVar[int] = 128
    MAX_TAGS: ClassVar[int] = 20
    TAG_KEY_MAX_LENGTH: ClassVar[int] = 64
    TAG_VALUE_MAX_LENGTH: ClassVar[int] = 256

    def __post_init__(self) -> None:
        """Validate hint fields."""
        if not self.namespace or not self.namespace.strip():
            raise ValueError("StoreHint namespace cannot be empty")
        if len(self.namespace) > self.NAMESPACE_MAX_LENGTH:
            raise ValueError(
                f"StoreHint namespace length cannot exceed "
                f"{self.NAMESPACE_MAX_LENGTH} characters, got {len(self.namespace)}"
            )
        if not self.label or not self.label.strip():
            raise ValueError("StoreHint label cannot be empty")
        if len(self.label) > self.LABEL_MAX_LENGTH:
            raise ValueError(
                f"StoreHint label length cannot exceed "
                f"{self.LABEL_MAX_LENGTH} characters, got {len(self.label)}"
            )
        if len(self.tags) > self.MAX_TAGS:
            raise ValueError(
                f"StoreHint cannot have more than {self.MAX_TAGS} tags, "
                f"got {len(self.tags)}"
            )
        for key, val in self.tags.items():
            if len(key) > self.TAG_KEY_MAX_LENGTH:
                raise ValueError(
                    f"Tag key length cannot exceed {self.TAG_KEY_MAX_LENGTH} "
                    f"characters, got {len(key)}"
                )
            if len(val) > self.TAG_VALUE_MAX_LENGTH:
                raise ValueError(
                    f"Tag value length cannot exceed {self.TAG_VALUE_MAX_LENGTH} "
                    f"characters, got {len(val)}"
                )
