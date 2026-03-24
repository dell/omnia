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

"""Repository interfaces (Protocols) for Artifact domain.

These define the contracts that infrastructure implementations must satisfy.
"""

from pathlib import Path
from typing import Dict, List, Optional, Protocol, Union

from core.jobs.value_objects import JobId, StageName

from .entities import ArtifactRecord
from .value_objects import ArtifactKey, ArtifactKind, ArtifactRef, StoreHint


class ArtifactStore(Protocol):
    """Port for persisting and retrieving immutable artifact content.

    Unified API: callers pass ArtifactKind to indicate shape.
    The store dispatches internally based on kind.

    For ARCHIVE kind, callers provide either:
      - file_map: Dict[str, bytes] for in-memory content subsets
      - source_directory: Path for zipping an entire directory

    For FILE kind, callers provide:
      - content: bytes
    """

    def store(
        self,
        hint: StoreHint,
        kind: ArtifactKind,
        content: Optional[bytes] = None,
        file_map: Optional[Dict[str, bytes]] = None,
        source_directory: Optional[Path] = None,
        content_type: str = "application/octet-stream",
    ) -> ArtifactRef:
        """Store an artifact.

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
        ...

    def retrieve(
        self,
        key: ArtifactKey,
        kind: ArtifactKind,
        destination: Optional[Path] = None,
    ) -> Union[bytes, Path]:
        """Retrieve an artifact.

        For FILE kind: returns bytes (destination ignored).
        For ARCHIVE kind: unpacks to destination and returns the path.
            If destination is None, creates a temp directory.

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
        ...

    def exists(self, key: ArtifactKey) -> bool:
        """Check if an artifact exists.

        Args:
            key: Artifact key to check.

        Returns:
            True if artifact exists, False otherwise.
        """
        ...

    def delete(self, key: ArtifactKey) -> bool:
        """Delete an artifact.

        Args:
            key: Artifact key to delete.

        Returns:
            True if artifact was deleted, False if not found.
        """
        ...

    def generate_key(self, hint: StoreHint, kind: ArtifactKind) -> ArtifactKey:
        """Generate a deterministic artifact key from hints.

        Args:
            hint: Store hints for key generation.
            kind: FILE or ARCHIVE (affects extension).

        Returns:
            Deterministic ArtifactKey.
        """
        ...


class ArtifactMetadataRepository(Protocol):
    """Port for persisting artifact metadata records.

    Used for cross-stage artifact lookup by (job_id, stage_name, label).
    """

    def save(self, record: ArtifactRecord) -> None:
        """Persist an artifact metadata record.

        Args:
            record: ArtifactRecord to persist.
        """
        ...

    def find_by_job_stage_and_label(
        self,
        job_id: JobId,
        stage_name: StageName,
        label: str,
    ) -> Optional[ArtifactRecord]:
        """Find an artifact record by job, stage, and label.

        Args:
            job_id: Parent job identifier.
            stage_name: Stage that produced the artifact.
            label: Artifact label.

        Returns:
            ArtifactRecord if found, None otherwise.
        """
        ...

    def find_by_job(self, job_id: JobId) -> List[ArtifactRecord]:
        """Find all artifact records for a job.

        Args:
            job_id: Parent job identifier.

        Returns:
            List of ArtifactRecord (may be empty).
        """
        ...

    def delete_by_job(self, job_id: JobId) -> int:
        """Delete all artifact records for a job.

        Args:
            job_id: Parent job identifier.

        Returns:
            Number of records deleted.
        """
        ...
