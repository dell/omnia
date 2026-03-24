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

"""In-memory implementation of ArtifactMetadataRepository for dev/test."""

from typing import Dict, List, Optional, Tuple

from core.artifacts.entities import ArtifactRecord
from core.jobs.value_objects import JobId, StageName


class InMemoryArtifactMetadataRepository:
    """In-memory artifact metadata repository for development and testing.

    Stores ArtifactRecord instances in a dictionary keyed by
    (job_id, stage_name, label) triple for cross-stage lookup.
    """

    def __init__(self) -> None:
        """Initialize empty in-memory repository."""
        self._records: Dict[Tuple[str, str, str], ArtifactRecord] = {}

    def save(self, record: ArtifactRecord) -> None:
        """Persist an artifact metadata record.

        Args:
            record: ArtifactRecord to persist.
        """
        key = (
            str(record.job_id),
            str(record.stage_name),
            record.label,
        )
        self._records[key] = record

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
        key = (str(job_id), str(stage_name), label)
        return self._records.get(key)

    def find_by_job(self, job_id: JobId) -> List[ArtifactRecord]:
        """Find all artifact records for a job.

        Args:
            job_id: Parent job identifier.

        Returns:
            List of ArtifactRecord (may be empty).
        """
        job_str = str(job_id)
        return [
            record
            for (j, _, _), record in self._records.items()
            if j == job_str
        ]

    def delete_by_job(self, job_id: JobId) -> int:
        """Delete all artifact records for a job.

        Args:
            job_id: Parent job identifier.

        Returns:
            Number of records deleted.
        """
        job_str = str(job_id)
        keys_to_delete = [
            key for key in self._records if key[0] == job_str
        ]
        for key in keys_to_delete:
            del self._records[key]
        return len(keys_to_delete)
