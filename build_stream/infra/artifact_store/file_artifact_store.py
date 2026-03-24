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

"""File-based implementation of ArtifactStore for production use."""

import hashlib
import io
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Optional, Set, Union

from core.artifacts.exceptions import (
    ArtifactAlreadyExistsError,
    ArtifactNotFoundError,
    ArtifactStoreError,
    ArtifactValidationError,
)
from core.artifacts.value_objects import (
    ArtifactDigest,
    ArtifactKey,
    ArtifactKind,
    ArtifactRef,
    StoreHint,
)


class FileArtifactStore:
    """File-based artifact store for production use.

    Stores artifacts on a local or network filesystem.
    Supports both FILE and ARCHIVE kinds via unified store/retrieve API.
    """

    DEFAULT_MAX_ARTIFACT_SIZE: int = 50 * 1024 * 1024  # 50 MB
    DEFAULT_ALLOWED_CONTENT_TYPES: Set[str] = {
        "application/json",
        "application/zip",
        "application/octet-stream",
        "text/plain",
    }

    def __init__(
        self,
        base_path: Path,
        max_artifact_size_bytes: int = DEFAULT_MAX_ARTIFACT_SIZE,
        allowed_content_types: Optional[Set[str]] = None,
    ) -> None:
        """Initialize file-based artifact store.

        Args:
            base_path: Base directory path for artifact storage.
            max_artifact_size_bytes: Maximum allowed artifact size.
            allowed_content_types: Set of allowed MIME content types.

        Raises:
            ValueError: If base_path is not a directory or not writable.
        """
        self._base_path = base_path
        self._max_artifact_size_bytes = max_artifact_size_bytes
        self._allowed_content_types = (
            allowed_content_types
            if allowed_content_types is not None
            else self.DEFAULT_ALLOWED_CONTENT_TYPES
        )

        self._base_path.mkdir(parents=True, exist_ok=True)
        if not self._base_path.is_dir():
            raise ValueError(f"base_path is not a directory: {base_path}")

    def store(
        self,
        hint: StoreHint,
        kind: ArtifactKind,
        content: Optional[bytes] = None,
        file_map: Optional[Dict[str, bytes]] = None,
        source_directory: Optional[Path] = None,
        content_type: str = "application/octet-stream",
    ) -> ArtifactRef:
        """Store an artifact (FILE or ARCHIVE).

        Args:
            hint: Hints for deterministic key generation.
            kind: FILE or ARCHIVE.
            content: Raw bytes (required for FILE kind).
            file_map: Mapping of relative paths to bytes (ARCHIVE kind).
            source_directory: Directory to zip (ARCHIVE kind).
            content_type: MIME type of the content.

        Returns:
            ArtifactRef with key, digest, size, and URI.

        Raises:
            ArtifactAlreadyExistsError: If artifact with same key exists.
            ArtifactValidationError: If content fails validation.
            ArtifactStoreError: If storage operation fails.
            ValueError: If wrong inputs for the given kind.
        """
        self._validate_content_type(content_type)
        raw_bytes = self._resolve_content(kind, content, file_map, source_directory)
        self._validate_size(raw_bytes)

        key = self.generate_key(hint, kind)
        artifact_path = self._get_artifact_path(key)

        if artifact_path.exists():
            raise ArtifactAlreadyExistsError(key=key.value)

        try:
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_bytes(raw_bytes)
        except OSError as e:
            raise ArtifactStoreError(
                f"Failed to write artifact to {artifact_path}: {e}"
            ) from e

        digest = ArtifactDigest(hashlib.sha256(raw_bytes).hexdigest())

        return ArtifactRef(
            key=key,
            digest=digest,
            size_bytes=len(raw_bytes),
            uri=f"file://{artifact_path}",
        )

    def retrieve(
        self,
        key: ArtifactKey,
        kind: ArtifactKind,
        destination: Optional[Path] = None,
    ) -> Union[bytes, Path]:
        """Retrieve an artifact.

        For FILE kind: returns bytes.
        For ARCHIVE kind: unpacks to destination and returns the path.

        Args:
            key: Artifact key to retrieve.
            kind: FILE or ARCHIVE.
            destination: Target directory for ARCHIVE unpacking.

        Returns:
            bytes for FILE kind, Path for ARCHIVE kind.

        Raises:
            ArtifactNotFoundError: If artifact does not exist.
            ArtifactStoreError: If retrieval fails.
        """
        artifact_path = self._get_artifact_path(key)

        if not artifact_path.exists():
            raise ArtifactNotFoundError(key=key.value)

        try:
            raw_bytes = artifact_path.read_bytes()
        except OSError as e:
            raise ArtifactStoreError(
                f"Failed to read artifact from {artifact_path}: {e}"
            ) from e

        if kind == ArtifactKind.FILE:
            return raw_bytes

        # ARCHIVE: unpack zip to destination
        if destination is None:
            import tempfile
            destination = Path(tempfile.mkdtemp(prefix="artifact-"))

        destination.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes), "r") as zf:
                zf.extractall(str(destination))
        except (zipfile.BadZipFile, OSError) as e:
            raise ArtifactStoreError(
                f"Failed to extract archive to {destination}: {e}"
            ) from e

        return destination

    def exists(self, key: ArtifactKey) -> bool:
        """Check if an artifact exists.

        Args:
            key: Artifact key to check.

        Returns:
            True if artifact exists, False otherwise.
        """
        artifact_path = self._get_artifact_path(key)
        return artifact_path.exists()

    def delete(self, key: ArtifactKey) -> bool:
        """Delete an artifact.

        Args:
            key: Artifact key to delete.

        Returns:
            True if artifact was deleted, False if not found.
        """
        artifact_path = self._get_artifact_path(key)
        if artifact_path.exists():
            try:
                artifact_path.unlink()
                self._cleanup_empty_dirs(artifact_path.parent)
                return True
            except OSError:
                return False
        return False

    def generate_key(self, hint: StoreHint, kind: ArtifactKind) -> ArtifactKey:
        """Generate a deterministic artifact key from hints.

        Key format: {namespace}/{tag_hash}/{label}.{ext}
        where tag_hash is a short SHA-256 of sorted tags for uniqueness.

        Args:
            hint: Store hints for key generation.
            kind: FILE or ARCHIVE (affects extension).

        Returns:
            Deterministic ArtifactKey.
        """
        tag_str = "|".join(
            f"{k}={v}" for k, v in sorted(hint.tags.items())
        )
        tag_hash = hashlib.sha256(tag_str.encode()).hexdigest()[:12]
        ext = "zip" if kind == ArtifactKind.ARCHIVE else "bin"
        key_value = f"{hint.namespace}/{tag_hash}/{hint.label}.{ext}"
        return ArtifactKey(key_value)

    def _get_artifact_path(self, key: ArtifactKey) -> Path:
        """Get the filesystem path for an artifact key.

        Args:
            key: Artifact key.

        Returns:
            Absolute path to the artifact file.
        """
        return self._base_path / key.value

    def _cleanup_empty_dirs(self, directory: Path) -> None:
        """Recursively remove empty parent directories up to base_path.

        Args:
            directory: Directory to start cleanup from.
        """
        try:
            while directory != self._base_path and directory.is_dir():
                if not any(directory.iterdir()):
                    directory.rmdir()
                    directory = directory.parent
                else:
                    break
        except OSError:
            pass

    def _resolve_content(
        self,
        kind: ArtifactKind,
        content: Optional[bytes],
        file_map: Optional[Dict[str, bytes]],
        source_directory: Optional[Path],
    ) -> bytes:
        """Resolve the raw bytes to store based on kind and inputs.

        Args:
            kind: FILE or ARCHIVE.
            content: Raw bytes for FILE kind.
            file_map: Dict of relative paths to bytes for ARCHIVE kind.
            source_directory: Directory to zip for ARCHIVE kind.

        Returns:
            Raw bytes to store.

        Raises:
            ValueError: If wrong combination of inputs for the given kind.
        """
        if kind == ArtifactKind.FILE:
            if content is None:
                raise ValueError(
                    "content is required for FILE kind"
                )
            if file_map is not None or source_directory is not None:
                raise ValueError(
                    "file_map and source_directory must not be provided for FILE kind"
                )
            return content

        # ARCHIVE kind
        if content is not None:
            raise ValueError(
                "content must not be provided for ARCHIVE kind; "
                "use file_map or source_directory"
            )
        if file_map is not None and source_directory is not None:
            raise ValueError(
                "Provide either file_map or source_directory, not both"
            )
        if file_map is None and source_directory is None:
            raise ValueError(
                "Either file_map or source_directory is required for ARCHIVE kind"
            )

        if file_map is not None:
            return self._zip_file_map(file_map)

        return self._zip_directory(source_directory)  # type: ignore[arg-type]

    def _zip_file_map(self, file_map: Dict[str, bytes]) -> bytes:
        """Create a zip archive from a file map.

        Args:
            file_map: Mapping of relative paths to content bytes.

        Returns:
            Zip archive as bytes.
        """
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for rel_path, data in sorted(file_map.items()):
                zf.writestr(rel_path, data)
        return buf.getvalue()

    def _zip_directory(self, directory: Path) -> bytes:
        """Create a zip archive from a directory.

        Args:
            directory: Directory to zip.

        Returns:
            Zip archive as bytes.

        Raises:
            ValueError: If directory does not exist.
        """
        if not directory.is_dir():
            raise ValueError(f"source_directory does not exist: {directory}")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(directory.rglob("*")):
                if file_path.is_file():
                    rel_path = file_path.relative_to(directory)
                    zf.writestr(str(rel_path), file_path.read_bytes())
        return buf.getvalue()

    def _validate_content_type(self, content_type: str) -> None:
        """Validate content type against allowlist.

        Args:
            content_type: MIME content type.

        Raises:
            ArtifactValidationError: If content type not allowed.
        """
        if content_type not in self._allowed_content_types:
            raise ArtifactValidationError(
                f"Content type not allowed: {content_type}. "
                f"Allowed: {sorted(self._allowed_content_types)}"
            )

    def _validate_size(self, raw_bytes: bytes) -> None:
        """Validate artifact size against maximum.

        Args:
            raw_bytes: Content bytes.

        Raises:
            ArtifactValidationError: If content exceeds max size.
        """
        if len(raw_bytes) > self._max_artifact_size_bytes:
            raise ArtifactValidationError(
                f"Artifact size {len(raw_bytes)} bytes exceeds maximum "
                f"{self._max_artifact_size_bytes} bytes"
            )
