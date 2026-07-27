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

"""Job response DTO."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class JobResponse:
    """Response DTO for job operations.

    Immutable data transfer object for returning job information
    to the API layer. All timestamps are ISO 8601 formatted strings.

    Attributes:
        job_id: Unique job identifier.
        client_id: Client who owns this job.
        catalog_digest: SHA-256 digest of catalog used.
        job_state: Current lifecycle state.
        created_at: Job creation timestamp (ISO 8601).
        updated_at: Last modification timestamp (ISO 8601).
        version: Optimistic locking version.
        tombstoned: Soft delete flag.
        is_new: True if job was newly created, False if retrieved from idempotency.
    """

    job_id: str
    client_id: str
    request_client_id: str
    client_name: Optional[str]
    job_state: str
    created_at: str
    updated_at: str
    version: int
    tombstoned: bool
    is_new: bool = True

    @staticmethod
    def from_entity(job, is_new: bool = True) -> "JobResponse":
        """Create response DTO from Job entity.

        Args:
            job: Job domain entity.
            is_new: True if job was newly created, False if retrieved from idempotency.

        Returns:
            JobResponse DTO with serialized values.
        """
        return JobResponse(
            job_id=str(job.job_id),
            client_id=str(job.client_id),
            request_client_id=job.request_client_id,
            client_name=job.client_name,
            job_state=job.job_state.value,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat(),
            version=job.version,
            tombstoned=job.tombstoned,
            is_new=is_new,
        )
