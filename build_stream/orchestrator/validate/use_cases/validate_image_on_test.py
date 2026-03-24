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

"""ValidateImageOnTest use case implementation."""

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
from core.localrepo.value_objects import (
    ExecutionTimeout,
    ExtraVars,
    PlaybookPath,
)
from core.validate.entities import ValidateImageOnTestRequest
from core.validate.exceptions import (
    StageGuardViolationError,
    ValidationExecutionError,
)
from core.validate.services import ValidateQueueService

from orchestrator.validate.commands import ValidateImageOnTestCommand
from orchestrator.validate.dtos import ValidateImageOnTestResponse

logger = logging.getLogger(__name__)

DISCOVERY_PLAYBOOK_NAME = "discovery.yml"
DEFAULT_TIMEOUT_MINUTES = 60


class ValidateImageOnTestUseCase:
    """Use case for triggering the validate-image-on-test stage.

    This use case orchestrates stage execution with the following guarantees:
    - Stage guard enforcement: BuildImage stage(s) must be completed
    - Job ownership verification: Client must own the job
    - Audit trail: Emits STAGE_STARTED event
    - NFS queue submission: Submits playbook request to NFS queue for watcher service

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

    def execute(self, command: ValidateImageOnTestCommand) -> ValidateImageOnTestResponse:
        """Execute the validate-image-on-test stage.

        Args:
            command: ValidateImageOnTest command with job details.

        Returns:
            ValidateImageOnTestResponse DTO with acceptance details.

        Raises:
            JobNotFoundError: If job does not exist or client mismatch.
            StageGuardViolationError: If upstream build-image stage not completed.
            ValidationExecutionError: If queue submission fails.
        """
        self._validate_job(command)
        stage = self._validate_stage(command)
        self._enforce_stage_guard(command)

        request = self._create_request(command)
        self._submit_to_queue(command, request, stage)
        self._emit_stage_started_event(command)

        return self._to_response(command, request)

    def _validate_job(self, command: ValidateImageOnTestCommand) -> None:
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

    def _validate_stage(self, command: ValidateImageOnTestCommand) -> Stage:
        """Validate stage exists and is in PENDING state."""
        stage_name = StageName(StageType.VALIDATE_IMAGE_ON_TEST.value)
        stage = self._stage_repo.find_by_job_and_name(command.job_id, stage_name)

        if stage is None:
            raise JobNotFoundError(
                job_id=str(command.job_id),
                correlation_id=str(command.correlation_id),
            )

        if stage.stage_state != StageState.PENDING:
            raise InvalidStateTransitionError(
                entity_type="Stage",
                entity_id=f"{command.job_id}/validate-image-on-test",
                from_state=stage.stage_state.value,
                to_state="IN_PROGRESS",
                correlation_id=str(command.correlation_id),
            )

        return stage

    def _enforce_stage_guard(self, command: ValidateImageOnTestCommand) -> None:
        """Enforce that at least one build-image stage has completed.

        The validate-image-on-test stage requires that at least one of the
        build-image stages (x86_64 or aarch64) has completed successfully.
        """
        x86_stage_name = StageName(StageType.BUILD_IMAGE_X86_64.value)
        aarch64_stage_name = StageName(StageType.BUILD_IMAGE_AARCH64.value)

        x86_stage = self._stage_repo.find_by_job_and_name(
            command.job_id, x86_stage_name
        )
        aarch64_stage = self._stage_repo.find_by_job_and_name(
            command.job_id, aarch64_stage_name
        )

        x86_completed = (
            x86_stage is not None
            and x86_stage.stage_state == StageState.COMPLETED
        )
        aarch64_completed = (
            aarch64_stage is not None
            and aarch64_stage.stage_state == StageState.COMPLETED
        )

        if not x86_completed and not aarch64_completed:
            # Determine which stages exist and their states for error message
            x86_state = x86_stage.stage_state.value if x86_stage else "NOT_FOUND"
            aarch64_state = aarch64_stage.stage_state.value if aarch64_stage else "NOT_FOUND"
            
            raise UpstreamStageNotCompletedError(
                job_id=str(command.job_id),
                required_stage="build-image-x86_64 or build-image-aarch64",
                actual_state=f"x86_64: {x86_state}, aarch64: {aarch64_state}",
                correlation_id=str(command.correlation_id),
            )

    def _create_request(
        self,
        command: ValidateImageOnTestCommand,
    ) -> ValidateImageOnTestRequest:
        """Create ValidateImageOnTestRequest entity."""
        playbook_path = PlaybookPath(DISCOVERY_PLAYBOOK_NAME)

        # Get image_key from the API request
        image_key = command.image_key

        extra_vars_dict = {
            "job_id": str(command.job_id),
            "image_key": image_key,
        }
        extra_vars = ExtraVars(extra_vars_dict)

        return ValidateImageOnTestRequest(
            job_id=str(command.job_id),
            stage_name=StageType.VALIDATE_IMAGE_ON_TEST.value,
            playbook_path=playbook_path,
            extra_vars=extra_vars,
            correlation_id=str(command.correlation_id),
            timeout=ExecutionTimeout(DEFAULT_TIMEOUT_MINUTES),
            submitted_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            request_id=str(self._uuid_generator.generate()),
        )

    def _submit_to_queue(
        self,
        command: ValidateImageOnTestCommand,
        request: ValidateImageOnTestRequest,
        stage: Stage,
    ) -> None:
        """Submit playbook request to NFS queue for watcher service."""
        try:
            stage.start()
            self._stage_repo.save(stage)
        except Exception as save_exc:
            # If save fails, stage was modified elsewhere, continue with queue submission
            log_secure_info(
                "Stage start save failed, continuing with queue submission: %s",
                str(save_exc)
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
                
                # Update job state to FAILED when stage fails
                JobStateHelper.handle_stage_failure(
                    job_repo=self._job_repo,
                    audit_repo=self._audit_repo,
                    uuid_generator=self._uuid_generator,
                    job_id=command.job_id,
                    stage_name=StageType.VALIDATE_IMAGE_ON_TEST.value,
                    error_code=error_code,
                    error_summary=error_summary,
                    correlation_id=str(command.correlation_id),
                    client_id=str(command.client_id),
                )
            except Exception as save_exc:
                # If save fails, stage was modified elsewhere
                log_secure_info(
                    "Stage fail save failed, stage already modified elsewhere: %s",
                    str(save_exc)
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
            "Validate-image-on-test request submitted to queue for job %s, "
            "correlation_id=%s",
            command.job_id,
            command.correlation_id,
        )

    def _emit_stage_started_event(
        self,
        command: ValidateImageOnTestCommand,
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
                "stage_name": StageType.VALIDATE_IMAGE_ON_TEST.value,
            },
        )
        self._audit_repo.save(event)

    def _to_response(
        self,
        command: ValidateImageOnTestCommand,
        request: ValidateImageOnTestRequest,
    ) -> ValidateImageOnTestResponse:
        """Map to response DTO."""
        return ValidateImageOnTestResponse(
            job_id=str(command.job_id),
            stage_name=StageType.VALIDATE_IMAGE_ON_TEST.value,
            status="accepted",
            submitted_at=request.submitted_at,
            correlation_id=str(command.correlation_id),
        )
