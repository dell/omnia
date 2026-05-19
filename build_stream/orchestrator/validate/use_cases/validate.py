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

"""Validate use case implementation."""

import logging
from datetime import datetime, timezone

from api.logging_utils import log_secure_info

from core.jobs.entities import AuditEvent, Stage
from core.jobs.exceptions import (
    JobNotFoundError,
    UpstreamStageNotCompletedError,
    InvalidStateTransitionError,
)
from core.jobs.repositories import (
    AuditEventRepository,
    JobRepository,
    StageRepository,
    UUIDGenerator,
)
from core.jobs.services import JobStateHelper
from core.jobs.value_objects import (
    StageName,
    StageState,
    StageType,
)
from core.validate.entities import ValidateRequest
from core.validate.exceptions import (
    StageGuardViolationError,
    ValidationExecutionError,
)
from core.validate.services import ValidateQueueService

from orchestrator.validate.commands import ValidateCommand
from orchestrator.validate.dtos import ValidateResponse

logger = logging.getLogger(__name__)

ARTIFACTS_BASE = "/opt/omnia/build_stream_root/artifacts"
CONFIG_PATH = "/opt/omnia/automation/omnia_test_config.yml"
DEFAULT_TIMEOUT_MINUTES = 120


class ValidateUseCase:
    """Use case for triggering the validate stage.

    This use case orchestrates stage execution with the following guarantees:
    - Stage guard enforcement: Restart stage must be completed (or job FAILED/PASSED for retry)
    - No active validate stage (QUEUED/IN_PROGRESS) allowed
    - Job ownership verification: Client must own the job
    - Audit trail: Emits STAGE_STARTED event
    - NFS queue submission: Submits molecule request to NFS queue for Playbook Watcher

    Attributes:
        job_repo: Job repository port.
        stage_repo: Stage repository port.
        audit_repo: Audit event repository port.
        queue_service: Validate queue service.
        uuid_generator: UUID generator for events and request IDs.
    """

    def __init__(
        self,
        job_repo: JobRepository,
        stage_repo: StageRepository,
        audit_repo: AuditEventRepository,
        queue_service: ValidateQueueService,
        uuid_generator: UUIDGenerator,
    ) -> None:  # pylint: disable=too-many-arguments,too-many-positional-arguments
        """Initialize use case with repository and service dependencies.

        Args:
            job_repo: Job repository implementation.
            stage_repo: Stage repository implementation.
            audit_repo: Audit event repository implementation.
            queue_service: Validate queue service.
            uuid_generator: UUID generator for identifiers.
        """
        self._job_repo = job_repo
        self._stage_repo = stage_repo
        self._audit_repo = audit_repo
        self._queue_service = queue_service
        self._uuid_generator = uuid_generator

    def execute(self, command: ValidateCommand) -> ValidateResponse:
        """Execute the validate stage.

        Flow per spec §7.3:
        1. Load job by ID → 404 if missing
        2. Guard check → restart completed, no active validate stage
        3. Create job_stages row: stage_name='validate', status='QUEUED', attempt incremented
        4. Update job status → VALIDATING
        5. Build NFS queue request JSON with command_type: 'test_automation'
        6. Write to /playbook_queue/requests/validate_{job_id}_{timestamp}.json
        7. Return 202

        Args:
            command: ValidateCommand with job details and test automation config.

        Returns:
            ValidateResponse DTO with acceptance details.

        Raises:
            JobNotFoundError: If job does not exist or client mismatch.
            UpstreamStageNotCompletedError: If restart stage not completed.
            InvalidStateTransitionError: If active validate stage exists.
            ValidationExecutionError: If queue submission fails.
        """
        job = self._validate_job(command)
        self._enforce_stage_guard(command)
        attempt = self._get_next_attempt_number(command)
        stage = self._create_stage(command, attempt)
        self._transition_job_to_validating(command)

        request = self._create_request(command, attempt)
        self._submit_to_queue(command, request, stage)
        self._emit_stage_started_event(command)

        return self._to_response(command, request, attempt)

    def _validate_job(self, command: ValidateCommand):
        """Validate job exists and belongs to the requesting client."""
        job = self._job_repo.find_by_id(command.job_id)
        if job is None or job.tombstoned:
            raise JobNotFoundError(
                job_id=str(command.job_id),
                correlation_id=str(command.correlation_id),
            )

        if job.client_id != command.client_id:
            raise JobNotFoundError(
                job_id=str(command.job_id),
                correlation_id=str(command.correlation_id),
            )
        return job

    def _enforce_stage_guard(self, command: ValidateCommand) -> None:
        """Enforce validate stage prerequisites per spec §7.3.

        Guard checks:
        1. Restart stage must be completed (upstream dependency)
        2. No active validate stage (QUEUED or IN_PROGRESS) — returns 409
        """
        # Check restart stage completed
        restart_stage_name = StageName(StageType.RESTART.value)
        restart_stage = self._stage_repo.find_by_job_and_name(
            command.job_id, restart_stage_name
        )

        if restart_stage is None or restart_stage.stage_state != StageState.COMPLETED:
            actual_state = restart_stage.stage_state.value if restart_stage else "NOT_FOUND"
            raise UpstreamStageNotCompletedError(
                job_id=str(command.job_id),
                required_stage="restart",
                actual_state=actual_state,
                correlation_id=str(command.correlation_id),
            )

        # Check no active validate stage (IN_PROGRESS only)
        # PENDING is allowed since it means nothing is running
        validate_stage_name = StageName(StageType.VALIDATE.value)
        validate_stage = self._stage_repo.find_by_job_and_name(
            command.job_id, validate_stage_name
        )
        if validate_stage is not None and validate_stage.stage_state == StageState.IN_PROGRESS:
            raise InvalidStateTransitionError(
                entity_type="Stage",
                entity_id=f"{command.job_id}/validate",
                from_state=validate_stage.stage_state.value,
                to_state=StageState.IN_PROGRESS.value,
                correlation_id=str(command.correlation_id),
            )

    def _get_next_attempt_number(self, command: ValidateCommand) -> int:
        """Calculate the next attempt number for this validate stage.

        Finds all previous validate stages for this job and increments.
        """
        validate_stage_name = StageName(StageType.VALIDATE.value)
        existing_stage = self._stage_repo.find_by_job_and_name(
            command.job_id, validate_stage_name
        )
        if existing_stage is not None and hasattr(existing_stage, 'attempt'):
            return existing_stage.attempt + 1
        return 1

    def _create_stage(self, command: ValidateCommand, attempt: int) -> Stage:
        """Create or update a job_stages record with status QUEUED."""
        validate_stage_name = StageName(StageType.VALIDATE.value)
        existing_stage = self._stage_repo.find_by_job_and_name(
            command.job_id, validate_stage_name
        )
        
        if existing_stage is not None:
            # Update existing stage instead of creating duplicate
            existing_stage.stage_state = StageState.PENDING
            existing_stage.attempt = attempt
            existing_stage.version = existing_stage.version + 1  # Increment version for optimistic locking
            existing_stage.error_code = None  # Clear error fields from previous attempt
            existing_stage.error_summary = None
            existing_stage.ended_at = None  # Clear ended_at from previous attempt
            existing_stage.result_detail = None  # Clear result_detail from previous attempt
            self._stage_repo.save(existing_stage)
            if hasattr(self._stage_repo, 'session'):
                self._stage_repo.session.commit()
            return existing_stage
        else:
            # Create new stage if none exists
            stage = Stage(
                job_id=command.job_id,
                stage_name=validate_stage_name,
                stage_state=StageState.PENDING,
                attempt=attempt,
            )
            self._stage_repo.save(stage)
            if hasattr(self._stage_repo, 'session'):
                self._stage_repo.session.commit()
            return stage

    def _transition_job_to_validating(self, command: ValidateCommand) -> None:
        """Update job status to VALIDATING (IN_PROGRESS)."""
        try:
            job = self._job_repo.find_by_id(command.job_id)
            if job is not None:
                job.start()
                self._job_repo.save(job)
        except Exception as exc:
            log_secure_info(
                "warning",
                f"Failed to transition job to VALIDATING: {exc}",
                str(command.correlation_id),
            )

    def _create_request(
        self,
        command: ValidateCommand,
        attempt: int,
    ) -> ValidateRequest:
        """Create ValidateRequest entity with test_automation-specific fields per spec §7.4."""
        now = datetime.now(timezone.utc)
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        request_id = f"validate_{command.job_id}_{timestamp_str}"
        artifact_dir = (
            f"{ARTIFACTS_BASE}/{command.job_id}/validate/attempt_{attempt}"
        )

        return ValidateRequest(
            request_id=request_id,
            job_id=str(command.job_id),
            stage_type="validate",
            command_type="test_automation",
            scenario_names=command.scenario_names,
            test_suite=command.test_suite,
            timeout_minutes=command.timeout_minutes,
            artifact_dir=artifact_dir,
            config_path=CONFIG_PATH,
            correlation_id=str(command.correlation_id),
            submitted_at=now.isoformat().replace("+00:00", "Z"),
            attempt=attempt,
        )

    def _submit_to_queue(
        self,
        command: ValidateCommand,
        request: ValidateRequest,
        stage: Stage,
    ) -> None:
        """Submit molecule request to NFS queue for Playbook Watcher."""
        try:
            stage.start()
            self._stage_repo.save(stage)
            if hasattr(self._stage_repo, 'session'):
                self._stage_repo.session.commit()
        except Exception as save_exc:
            log_secure_info(
                "warning",
                f"Stage start save failed, continuing with queue submission: {save_exc}",
                str(command.correlation_id),
            )

        try:
            self._queue_service.submit_request(
                request=request,
                correlation_id=str(command.correlation_id),
            )
        except Exception as exc:
            try:
                error_code = "QUEUE_SUBMISSION_FAILED"
                error_summary = str(exc)
                stage.fail(
                    error_code=error_code,
                    error_summary=error_summary,
                )
                self._stage_repo.save(stage)

                JobStateHelper.handle_stage_failure(
                    job_repo=self._job_repo,
                    audit_repo=self._audit_repo,
                    uuid_generator=self._uuid_generator,
                    job_id=command.job_id,
                    stage_name=StageType.VALIDATE.value,
                    error_code=error_code,
                    error_summary=error_summary,
                    correlation_id=str(command.correlation_id),
                    client_id=str(command.client_id),
                )
            except Exception as save_exc:
                log_secure_info(
                    "warning",
                    f"Stage fail save failed, stage already modified elsewhere: {save_exc}",
                    str(command.correlation_id),
                )
            log_secure_info(
                "error",
                f"Queue submission failed for job {command.job_id}",
                str(command.correlation_id),
            )
            raise ValidationExecutionError(
                message=f"Failed to submit validation request: {exc}",
                correlation_id=str(command.correlation_id),
            ) from exc

        logger.info(
            "Validate request submitted to queue for job %s, "
            "scenarios=%s, correlation_id=%s",
            command.job_id,
            command.scenario_names,
            command.correlation_id,
        )

    def _emit_stage_started_event(
        self,
        command: ValidateCommand,
    ) -> None:
        """Emit an audit event for stage start."""
        event = AuditEvent(
            event_id=str(self._uuid_generator.generate()),
            job_id=command.job_id,
            event_type="STAGE_STARTED",
            correlation_id=command.correlation_id,
            client_id=command.client_id,
            timestamp=datetime.now(timezone.utc),
            details={
                "stage_name": StageType.VALIDATE.value,
                "scenario_names": command.scenario_names,
                "test_suite": command.test_suite,
            },
        )
        self._audit_repo.save(event)

    def _to_response(
        self,
        command: ValidateCommand,
        request: ValidateRequest,
        attempt: int,
    ) -> ValidateResponse:
        """Map to response DTO."""
        return ValidateResponse(
            job_id=str(command.job_id),
            stage_name=StageType.VALIDATE.value,
            status="accepted",
            submitted_at=request.submitted_at,
            correlation_id=str(command.correlation_id),
            attempt=attempt,
        )
