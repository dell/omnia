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

"""CreateRestart use case implementation.

Note (Omnia 2.3+):
    The standalone set_pxe_boot.yml playbook invocation has been retired from
    this stage.  PXE boot is now handled implicitly by the orchestrator.yml
    playbook during the deploy stage.  This use case retains all non-playbook
    operations (job/stage validation, state transitions, audit trail) and
    immediately marks the restart stage as COMPLETED so downstream stages
    (validate) can proceed without delay.
"""

from datetime import datetime, timezone

from api.logging_utils import log_secure_info

from core.jobs.entities import AuditEvent, Stage
from core.jobs.exceptions import (
    JobNotFoundError,
    StageNotFoundError,
    InvalidStateTransitionError,
    TerminalStateViolationError,
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
    StageType,
    StageState,
)

from orchestrator.restart.commands import CreateRestartCommand
from orchestrator.restart.dtos import RestartResponse


class CreateRestartUseCase:
    """Use case for triggering the restart stage.

    With the orchestrator-domain integration (Omnia 2.3+), PXE boot is
    performed as part of the orchestrator.yml playbook during the deploy
    stage.  This use case therefore skips explicit playbook invocation and
    immediately completes the restart stage.

    Retained guarantees:
    - Stage guard enforcement: Only PENDING stages can be started
    - Job ownership verification: Client must own the job
    - Audit trail: Emits STAGE_STARTED and STAGE_COMPLETED events
    - Re-run support: COMPLETED/FAILED stages are reset before proceeding

    Attributes:
        job_repo: Job repository port.
        stage_repo: Stage repository port.
        audit_repo: Audit event repository port.
        uuid_generator: UUID generator for events.
    """

    def __init__(
        self,
        job_repo: JobRepository,
        stage_repo: StageRepository,
        audit_repo: AuditEventRepository,
        uuid_generator: UUIDGenerator,
    ) -> None:
        """Initialize use case with repository and service dependencies.

        Args:
            job_repo: Job repository implementation.
            stage_repo: Stage repository implementation.
            audit_repo: Audit event repository implementation.
            uuid_generator: UUID generator for identifiers.
        """
        self._job_repo = job_repo
        self._stage_repo = stage_repo
        self._audit_repo = audit_repo
        self._uuid_generator = uuid_generator

    def execute(self, command: CreateRestartCommand) -> RestartResponse:
        """Execute the restart stage.

        Since PXE boot is now handled by the orchestrator playbook during
        the deploy stage, this method validates preconditions, transitions
        the stage through IN_PROGRESS to COMPLETED synchronously, and emits
        audit events.  No playbook is submitted to the NFS queue.

        Args:
            command: CreateRestart command with job details.

        Returns:
            RestartResponse DTO with acceptance details.

        Raises:
            JobNotFoundError: If job does not exist or client mismatch.
            StageNotFoundError: If restart stage does not exist for the job.
            InvalidStateTransitionError: If stage is not in PENDING state.
            TerminalStateViolationError: If stage is in a terminal state.
        """
        job = self._validate_job(command)
        stage = self._validate_stage(command)
        image_group_id = self._get_image_group_id(job)

        # Transition stage: PENDING -> IN_PROGRESS -> COMPLETED (synchronous)
        self._complete_stage_immediately(command, stage)

        # Audit trail
        self._emit_stage_started_event(command)
        self._emit_stage_completed_event(command)

        submitted_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        log_secure_info(
            "info",
            f"Restart stage completed (PXE boot retired — handled by orchestrator "
            f"playbook during deploy): job_id={command.job_id}",
            job_id=str(command.job_id),
        )

        return self._to_response(command, image_group_id, submitted_at)

    def _validate_job(self, command: CreateRestartCommand):
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

    def _validate_stage(self, command: CreateRestartCommand) -> Stage:
        """Validate stage exists and prepare it for execution.

        The restart stage supports re-runs: if the stage is in COMPLETED or
        FAILED state it is reset back to PENDING so a fresh execution can
        proceed.  IN_PROGRESS is rejected (already running).  CANCELLED is
        rejected (job was deleted).
        """
        stage_name = StageName(StageType.RESTART.value)
        stage = self._stage_repo.find_by_job_and_name(command.job_id, stage_name)

        if stage is None:
            raise StageNotFoundError(
                job_id=str(command.job_id),
                stage_name=StageType.RESTART.value,
                correlation_id=str(command.correlation_id),
            )

        if stage.stage_state == StageState.IN_PROGRESS:
            raise InvalidStateTransitionError(
                entity_type="Stage",
                entity_id=f"{command.job_id}/{StageType.RESTART.value}",
                from_state=stage.stage_state.value,
                to_state="IN_PROGRESS",
                correlation_id=str(command.correlation_id),
            )

        if stage.stage_state == StageState.CANCELLED:
            raise TerminalStateViolationError(
                entity_type="Stage",
                entity_id=f"{command.job_id}/{StageType.RESTART.value}",
                state=stage.stage_state.value,
                correlation_id=str(command.correlation_id),
            )

        if stage.stage_state in {StageState.COMPLETED, StageState.FAILED}:
            prev_state = stage.stage_state.value
            stage.reset()
            self._stage_repo.save(stage)
            log_secure_info(
                "info",
                f"Resetting restart stage from {prev_state} to PENDING "
                f"for retry/re-run (attempt {stage.attempt}): "
                f"job_id={command.job_id}",
                job_id=str(command.job_id),
            )
            # Resume job from FAILED to IN_PROGRESS so CI polling doesn't exit early
            JobStateHelper.handle_job_resume(
                job_repo=self._job_repo,
                audit_repo=self._audit_repo,
                uuid_generator=self._uuid_generator,
                job_id=command.job_id,
                stage_name=StageType.RESTART.value,
                correlation_id=str(command.correlation_id),
                client_id=str(command.client_id),
            )

        return stage

    def _get_image_group_id(self, job) -> str:
        """Extract image_group_id from job parameters/metadata."""
        params = getattr(job, "parameters", None) or {}
        return params.get("image_group_id", "")

    def _complete_stage_immediately(
        self,
        command: CreateRestartCommand,
        stage: Stage,
    ) -> None:
        """Transition stage PENDING -> IN_PROGRESS -> COMPLETED synchronously.

        Since PXE boot is now part of the orchestrator playbook (deploy stage),
        we skip the NFS queue entirely and mark the stage as complete inline.
        Two saves are needed to satisfy optimistic locking (each transition
        increments the version).
        """
        stage.start()
        self._stage_repo.save(stage)

        stage.complete()
        self._stage_repo.save(stage)

        log_secure_info(
            "info",
            f"Restart stage immediately completed (PXE boot retired): "
            f"job_id={command.job_id}, attempt={stage.attempt}",
            job_id=str(command.job_id),
        )

    def _emit_stage_started_event(
        self,
        command: CreateRestartCommand,
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
                "stage_name": StageType.RESTART.value,
                "note": "PXE boot retired — handled by orchestrator playbook during deploy",
            },
        )
        self._audit_repo.save(event)

    def _emit_stage_completed_event(
        self,
        command: CreateRestartCommand,
    ) -> None:
        """Emit an audit event for immediate stage completion."""
        event = AuditEvent(
            event_id=str(self._uuid_generator.generate()),
            job_id=command.job_id,
            event_type="STAGE_COMPLETED",
            correlation_id=command.correlation_id,
            client_id=command.client_id,
            timestamp=datetime.now(timezone.utc),
            details={
                "stage_name": StageType.RESTART.value,
                "note": "Completed immediately — PXE boot handled during deploy stage",
            },
        )
        self._audit_repo.save(event)

    def _to_response(
        self,
        command: CreateRestartCommand,
        image_group_id: str,
        submitted_at: str,
    ) -> RestartResponse:
        """Map to response DTO."""
        return RestartResponse(
            job_id=str(command.job_id),
            stage_name=StageType.RESTART.value,
            status="accepted",
            submitted_at=submitted_at,
            image_group_id=image_group_id,
            correlation_id=str(command.correlation_id),
        )
