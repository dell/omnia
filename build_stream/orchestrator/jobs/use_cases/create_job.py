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

# pylint: disable=too-many-arguments,too-many-positional-arguments,too-few-public-methods

"""CreateJob use case implementation."""

from datetime import datetime, timezone
from typing import List, Optional

from core.jobs.entities import Job, Stage, IdempotencyRecord, AuditEvent
from core.jobs.exceptions import (
    JobAlreadyExistsError,
    IdempotencyConflictError,
)
from core.jobs.repositories import (
    JobRepository,
    StageRepository,
    IdempotencyRepository,
    AuditEventRepository,
    JobIdGenerator,
    UUIDGenerator,
)
from core.jobs.services import FingerprintService
from core.jobs.value_objects import JobId, StageName, StageType, RequestFingerprint

from ..commands import CreateJobCommand
from ..dtos import JobResponse


class CreateJobUseCase:
    """Use case for creating a new job with idempotency support.

    This use case orchestrates job creation with the following guarantees:
    - Idempotency: Same idempotency key returns same result
    - Atomicity: All-or-nothing persistence (job + stages + idempotency record)
    - Audit trail: Emits JOB_CREATED event
    - Initial stages: Creates all 5 stages in PENDING state

    Attributes:
        job_repo: Job repository port.
        stage_repo: Stage repository port.
        idempotency_repo: Idempotency repository port.
        audit_repo: Audit event repository port.
    """

    def __init__(
        self,
        job_repo: JobRepository,
        stage_repo: StageRepository,
        idempotency_repo: IdempotencyRepository,
        audit_repo: AuditEventRepository,
        job_id_generator: JobIdGenerator,
        uuid_generator: UUIDGenerator,
    ) -> None:
        """Initialize use case with repository dependencies.

        Args:
            job_repo: Job repository implementation.
            stage_repo: Stage repository implementation.
            idempotency_repo: Idempotency repository implementation.
            audit_repo: Audit event repository implementation.
            job_id_generator: Job identifier generator to use.
            uuid_generator: UUID generator for events and other identifiers.
        """
        self._job_repo = job_repo
        self._stage_repo = stage_repo
        self._idempotency_repo = idempotency_repo
        self._audit_repo = audit_repo
        self._job_id_generator = job_id_generator
        self._uuid_generator = uuid_generator

    def execute(self, command: CreateJobCommand) -> JobResponse:
        """Execute job creation with idempotency.

        Args:
            command: CreateJob command with job details.

        Returns:
            JobResponse DTO with created job details.

        Raises:
            JobAlreadyExistsError: If job_id already exists.
            IdempotencyConflictError: If idempotency key exists with different fingerprint.
        """
        fingerprint = self._compute_fingerprint(command)
        existing_job = self._check_idempotency(command, fingerprint)
        if existing_job is not None:
            return self._to_response(existing_job, is_new=False)

        job_id = self._generate_job_id(command)

        job = self._build_job(command, job_id)
        stages = self._create_initial_stages(job_id)

        self._save_job_and_stages(job, stages)
        self._save_idempotency_record(command, job_id, fingerprint)
        self._emit_job_created_event(command, job_id, stages)

        return self._to_response(job)

    def _generate_job_id(self, command: CreateJobCommand) -> JobId:
        """Generate a new JobId and ensure it is not already used."""
        job_id = self._job_id_generator.generate()
        if self._job_repo.exists(job_id):
            raise JobAlreadyExistsError(
                job_id=str(job_id),
                correlation_id=str(command.correlation_id),
            )
        return job_id

    def _check_idempotency(
        self,
        command: CreateJobCommand,
        fingerprint: RequestFingerprint,
    ) -> Optional[Job]:
        """Return existing job for idempotent retries, or raise on conflicts."""
        existing_record = self._idempotency_repo.find_by_key(command.idempotency_key)
        if existing_record is None:
            return None

        if not existing_record.matches_fingerprint(fingerprint):
            raise IdempotencyConflictError(
                idempotency_key=str(command.idempotency_key),
                existing_job_id=str(existing_record.job_id),
                correlation_id=str(command.correlation_id),
            )

        return self._job_repo.find_by_id(existing_record.job_id)

    def _build_job(self, command: CreateJobCommand, job_id: JobId) -> Job:
        """Build the Job aggregate for a create request."""
        return Job(
            job_id=job_id,
            client_id=command.client_id,
            request_client_id=command.request_client_id,
            client_name=command.client_name,
        )

    def _save_job_and_stages(self, job: Job, stages: List[Stage]) -> None:
        """Persist the job aggregate and its initial stages."""
        self._job_repo.save(job)
        self._stage_repo.save_all(stages)

    def _save_idempotency_record(
        self,
        command: CreateJobCommand,
        job_id: JobId,
        fingerprint: RequestFingerprint,
    ) -> None:
        """Persist idempotency record for create job."""
        now = self._now_utc()
        record = IdempotencyRecord(
            idempotency_key=command.idempotency_key,
            job_id=job_id,
            request_fingerprint=fingerprint,
            client_id=command.client_id,
            created_at=now,
            expires_at=now.replace(hour=23, minute=59, second=59),
        )
        self._idempotency_repo.save(record)

    def _emit_job_created_event(
        self,
        command: CreateJobCommand,
        job_id: JobId,
        stages: List[Stage],
    ) -> None:
        """Emit an audit event for job creation."""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            job_id=job_id,
            event_type="JOB_CREATED",
            correlation_id=command.correlation_id,
            client_id=command.client_id,
            timestamp=self._now_utc(),
            details={
                "client_name": command.client_name,
                "stage_count": len(stages),
            },
        )
        self._audit_repo.save(event)

    def _to_response(self, job: Job, is_new: bool = True) -> JobResponse:
        """Map domain entity to response DTO."""
        return JobResponse.from_entity(job, is_new=is_new)

    def _now_utc(self) -> datetime:
        """Return current UTC timestamp."""
        return datetime.now(timezone.utc)

    def _compute_fingerprint(self, command: CreateJobCommand) -> RequestFingerprint:
        """Compute request fingerprint for idempotency.
        Fingerprint includes only request payload, not auth-derived fields."""

        request_body = {}
        if command.client_name:
            request_body["client_name"] = command.client_name
        return FingerprintService.compute(request_body)

    def _create_initial_stages(self, job_id: JobId) -> List[Stage]:
        """Create initial stages for the job.

        Creates all 9 stages in PENDING state:
        - PARSE_CATALOG
        - GENERATE_INPUT_FILES
        - CREATE_LOCAL_REPOSITORY
        - UPDATE_LOCAL_REPOSITORY
        - CREATE_IMAGE_REPOSITORY
        - BUILD_IMAGE
        - VALIDATE_IMAGE
        - VALIDATE_IMAGE_ON_TEST
        - PROMOTE

        Returns:
            List of Stage entities in PENDING state.
        """
        stages = []
        for stage_type in StageType:
            stage = Stage(
                job_id=job_id,
                stage_name=StageName(stage_type.value),
            )
            stages.append(stage)

        return stages

    def _generate_event_id(self) -> str:
        """Generate event ID for audit events.
        
        Returns:
            UUID v4 string for event identifier.
        """
        return str(self._uuid_generator.generate())
