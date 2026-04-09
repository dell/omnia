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

"""CreateRestart use case implementation."""

import logging
from datetime import datetime, timezone

from api.logging_utils import log_secure_info

from core.localrepo.entities import PlaybookRequest
from core.localrepo.value_objects import (
    ExecutionTimeout,
    ExtraVars,
    PlaybookPath,
)
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
from core.localrepo.services import PlaybookQueueRequestService

from orchestrator.restart.commands import CreateRestartCommand
from orchestrator.restart.dtos import RestartResponse

logger = logging.getLogger(__name__)

PLAYBOOK_NAME = "set_pxe_boot.yml"
DEFAULT_TIMEOUT_MINUTES = 30


class CreateRestartUseCase:
    """Use case for triggering the restart stage.

    This use case orchestrates stage execution with the following guarantees:
    - Stage guard enforcement: Only PENDING stages can be started
    - Job ownership verification: Client must own the job
    - PlaybookRequest construction and NFS queue submission
    - Audit trail: Emits STAGE_STARTED event
    - No extra_vars: The playbook runs without additional variables

    Attributes:
        job_repo: Job repository port.
        stage_repo: Stage repository port.
        audit_repo: Audit event repository port.
        queue_service: Playbook queue request service.
        uuid_generator: UUID generator for events and request IDs.
    """

    def __init__(
        self,
        job_repo: JobRepository,
        stage_repo: StageRepository,
        audit_repo: AuditEventRepository,
        queue_service: PlaybookQueueRequestService,
        uuid_generator: UUIDGenerator,
    ) -> None:  # pylint: disable=too-many-arguments,too-many-positional-arguments
        """Initialize use case with repository and service dependencies.

        Args:
            job_repo: Job repository implementation.
            stage_repo: Stage repository implementation.
            audit_repo: Audit event repository implementation.
            queue_service: Playbook queue request service.
            uuid_generator: UUID generator for identifiers.
        """
        self._job_repo = job_repo
        self._stage_repo = stage_repo
        self._audit_repo = audit_repo
        self._queue_service = queue_service
        self._uuid_generator = uuid_generator

    def execute(self, command: CreateRestartCommand) -> RestartResponse:
        """Execute the restart stage.

        Args:
            command: CreateRestart command with job details.

        Returns:
            RestartResponse DTO with acceptance details.

        Raises:
            JobNotFoundError: If job does not exist or client mismatch.
            StageNotFoundError: If restart stage does not exist for the job.
            InvalidStateTransitionError: If stage is not in PENDING state.
            TerminalStateViolationError: If stage is in a terminal state.
            QueueUnavailableError: If NFS queue is not accessible.
        """
        job = self._validate_job(command)
        stage = self._validate_stage(command)
        image_group_id = self._get_image_group_id(job)

        request = self._build_playbook_request(command)
        self._submit_to_queue(command, request, stage)

        self._emit_stage_started_event(command)

        return self._to_response(command, request, image_group_id)

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
        """Validate stage exists and is in PENDING state."""
        stage_name = StageName(StageType.RESTART.value)
        stage = self._stage_repo.find_by_job_and_name(command.job_id, stage_name)

        if stage is None:
            raise StageNotFoundError(
                job_id=str(command.job_id),
                stage_name=StageType.RESTART.value,
                correlation_id=str(command.correlation_id),
            )

        if stage.stage_state.is_terminal():
            raise TerminalStateViolationError(
                entity_type="Stage",
                entity_id=f"{command.job_id}/{StageType.RESTART.value}",
                state=stage.stage_state.value,
                correlation_id=str(command.correlation_id),
            )

        if stage.stage_state != StageState.PENDING:
            raise InvalidStateTransitionError(
                entity_type="Stage",
                entity_id=f"{command.job_id}/{StageType.RESTART.value}",
                from_state=stage.stage_state.value,
                to_state="IN_PROGRESS",
                correlation_id=str(command.correlation_id),
            )

        return stage

    def _get_image_group_id(self, job) -> str:
        """Extract image_group_id from job parameters/metadata."""
        params = getattr(job, "parameters", None) or {}
        return params.get("image_group_id", "")

    def _build_playbook_request(
        self,
        command: CreateRestartCommand,
    ) -> PlaybookRequest:
        """Create PlaybookRequest entity for the restart stage."""
        playbook_path = PlaybookPath(PLAYBOOK_NAME)

        return PlaybookRequest(
            job_id=str(command.job_id),
            stage_name=StageType.RESTART.value,
            playbook_path=playbook_path,
            extra_vars=ExtraVars(values={}),
            correlation_id=str(command.correlation_id),
            timeout=ExecutionTimeout(DEFAULT_TIMEOUT_MINUTES),
            submitted_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            request_id=str(self._uuid_generator.generate()),
        )

    def _submit_to_queue(
        self,
        command: CreateRestartCommand,
        request: PlaybookRequest,
        stage: Stage,
    ) -> None:
        """Submit playbook request to NFS queue for watcher service."""
        stage.start()
        self._stage_repo.save(stage)

        self._queue_service.submit_request(
            request=request,
            correlation_id=str(command.correlation_id),
        )

        logger.info(
            "Restart request submitted to queue for job %s, stage=%s, "
            "correlation_id=%s",
            command.job_id,
            StageType.RESTART.value,
            command.correlation_id,
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
            },
        )
        self._audit_repo.save(event)

    def _to_response(
        self,
        command: CreateRestartCommand,
        request: PlaybookRequest,
        image_group_id: str,
    ) -> RestartResponse:
        """Map to response DTO."""
        return RestartResponse(
            job_id=str(command.job_id),
            stage_name=StageType.RESTART.value,
            status="accepted",
            submitted_at=request.submitted_at,
            image_group_id=image_group_id,
            correlation_id=str(command.correlation_id),
        )
