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

"""Artifact domain entities."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional

from core.jobs.value_objects import JobId, StageName

from .value_objects import ArtifactKind, ArtifactRef


@dataclass
class ArtifactRecord:
    """Metadata entity linking an artifact to its producing context.

    Persisted in the Metadata Store for cross-stage artifact lookup.
    Each (job_id, stage_name, label) triple is unique.

    Attributes:
        id: Unique record identifier.
        job_id: Parent job identifier.
        stage_name: Stage that produced this artifact.
        label: Human-readable artifact label for cross-stage lookup.
        artifact_ref: Reference to the stored artifact content.
        kind: FILE or ARCHIVE.
        content_type: MIME content type.
        tags: Key-value metadata for queryability.
        created_at: Record creation timestamp.
    """

    id: str
    job_id: JobId
    stage_name: StageName
    label: str
    artifact_ref: ArtifactRef
    kind: ArtifactKind
    content_type: str = "application/octet-stream"
    tags: Optional[Dict[str, str]] = None
    created_at: Optional[datetime] = None

    LABEL_MAX_LENGTH: int = 128
    CONTENT_TYPE_MAX_LENGTH: int = 128

    def __post_init__(self) -> None:
        """Validate and initialize record fields."""
        if not self.label or not self.label.strip():
            raise ValueError("ArtifactRecord label cannot be empty")
        if len(self.label) > self.LABEL_MAX_LENGTH:
            raise ValueError(
                f"ArtifactRecord label length cannot exceed "
                f"{self.LABEL_MAX_LENGTH} characters, got {len(self.label)}"
            )
        if len(self.content_type) > self.CONTENT_TYPE_MAX_LENGTH:
            raise ValueError(
                f"ArtifactRecord content_type length cannot exceed "
                f"{self.CONTENT_TYPE_MAX_LENGTH} characters, "
                f"got {len(self.content_type)}"
            )
        if self.tags is None:
            self.tags = {}
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
