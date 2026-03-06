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

"""Repository port interfaces (Protocols) for Jobs domain.

These define the contracts that infrastructure implementations must satisfy.
Using Protocol instead of ABC allows for structural subtyping (duck typing).
"""

from typing import Protocol, Optional, List
import uuid

from .entities import Job, Stage, IdempotencyRecord, AuditEvent
from .value_objects import JobId, IdempotencyKey, StageName


class JobIdGenerator(Protocol):
    """Generator port for creating Job identifiers."""

    def generate(self) -> JobId:
        """Generate a new Job identifier.

        Returns:
            A new, unique JobId.

        Raises:
            JobIdExhaustionError: If the generator cannot produce more IDs.
        """
        ...


class JobRepository(Protocol):
    """Repository port for Job aggregate persistence."""

    def save(self, job: Job) -> None:
        """Persist a job aggregate.

        Args:
            job: Job entity to persist.

        Raises:
            OptimisticLockError: If version conflict detected.
        """
        ...

    def find_by_id(self, job_id: JobId) -> Optional[Job]:
        """Retrieve a job by its identifier.

        Args:
            job_id: Unique job identifier.

        Returns:
            Job entity if found, None otherwise.
        """
        ...

    def exists(self, job_id: JobId) -> bool:
        """Check if a job exists.

        Args:
            job_id: Unique job identifier.

        Returns:
            True if job exists, False otherwise.
        """
        ...


class StageRepository(Protocol):
    """Repository port for Stage entity persistence."""

    def save(self, stage: Stage) -> None:
        """Persist a single stage.

        Args:
            stage: Stage entity to persist.

        Raises:
            OptimisticLockError: If version conflict detected.
        """
        ...

    def save_all(self, stages: List[Stage]) -> None:
        """Persist multiple stages atomically.

        Args:
            stages: List of stage entities to persist.

        Raises:
            OptimisticLockError: If version conflict detected.
        """
        ...

    def find_by_job_and_name(
        self,
        job_id: JobId,
        stage_name: StageName
    ) -> Optional[Stage]:
        """Retrieve a stage by job and stage name.

        Args:
            job_id: Parent job identifier.
            stage_name: Stage identifier.

        Returns:
            Stage entity if found, None otherwise.
        """
        ...

    def find_all_by_job(self, job_id: JobId) -> List[Stage]:
        """Retrieve all stages for a job.

        Args:
            job_id: Parent job identifier.

        Returns:
            List of stage entities (may be empty).
        """
        ...


class IdempotencyRepository(Protocol):
    """Repository port for IdempotencyRecord persistence."""

    def save(self, record: IdempotencyRecord) -> None:
        """Persist an idempotency record.

        Args:
            record: Idempotency record to persist.
        """
        ...

    def find_by_key(self, key: IdempotencyKey) -> Optional[IdempotencyRecord]:
        """Retrieve an idempotency record by key.

        Args:
            key: Idempotency key.

        Returns:
            IdempotencyRecord if found, None otherwise.
        """
        ...


class AuditEventRepository(Protocol):
    """Repository port for AuditEvent persistence."""

    def save(self, event: AuditEvent) -> None:
        """Persist an audit event.

        Args:
            event: Audit event to persist.
        """
        ...

    def find_by_job(self, job_id: JobId) -> List[AuditEvent]:
        """Retrieve all audit events for a job.

        Args:
            job_id: Job identifier.

        Returns:
            List of audit events (may be empty).
        """
        ...


class UUIDGenerator:
    """Interface for generating UUID objects."""

    def generate(self) -> uuid.UUID:
        """Generate a UUID object.

        Returns:
            uuid.UUID: A UUID object (v4 or v7 format).
        """
        ...
