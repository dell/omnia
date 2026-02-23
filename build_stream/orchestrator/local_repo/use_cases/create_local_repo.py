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

"""CreateLocalRepo use case implementation."""

import logging
from datetime import datetime, timezone

from api.logging_utils import log_secure_info

from core.jobs.entities import AuditEvent, Stage
from core.jobs.exceptions import JobNotFoundError
from core.jobs.repositories import (
    AuditEventRepository,
    JobRepository,
    StageRepository,
    UUIDGenerator,
)
from core.jobs.value_objects import (
    StageName,
    StageType,
)
from core.localrepo.entities import PlaybookRequest
from core.localrepo.exceptions import (
    InputDirectoryInvalidError,
    InputFilesMissingError,
)
from core.localrepo.services import (
    InputFileService,
    PlaybookQueueRequestService,
)
from core.localrepo.value_objects import (
    ExecutionTimeout,
    ExtraVars,
    PlaybookPath,
)

from orchestrator.local_repo.commands import CreateLocalRepoCommand
from orchestrator.local_repo.dtos import LocalRepoResponse

logger = logging.getLogger(__name__)

DEFAULT_PLAYBOOK_NAME = "local_repo.yml"


class CreateLocalRepoUseCase:
    """Use case for triggering the create-local-repository stage.

    This use case orchestrates stage execution with the following guarantees:
    - Stage guard enforcement: Only PENDING stages can be started
    - Job ownership verification: Client must own the job
    - Input file validation: Prerequisites checked before playbook execution
    - Audit trail: Emits STAGE_STARTED event
    - NFS queue submission: Submits playbook request to NFS queue for watcher service

    Attributes:
        job_repo: Job repository port.
        stage_repo: Stage repository port.
        audit_repo: Audit event repository port.
        input_file_service: Input file validation and preparation service.
        playbook_queue_service: NFS queue service for submitting playbook requests.
        uuid_generator: UUID generator for events and request IDs.
    """

    def __init__(
        self,
        job_repo: JobRepository,
        stage_repo: StageRepository,
        audit_repo: AuditEventRepository,
        input_file_service: InputFileService,
        playbook_queue_service: PlaybookQueueRequestService,
        uuid_generator: UUIDGenerator,
    ) -> None:  # pylint: disable=too-many-arguments,too-many-positional-arguments
        """Initialize use case with repository and service dependencies.

        Args:
            job_repo: Job repository implementation.
            stage_repo: Stage repository implementation.
            audit_repo: Audit event repository implementation.
            input_file_service: Input file service for validation.
            playbook_queue_service: NFS queue service for submitting requests.
            uuid_generator: UUID generator for identifiers.
        """
        self._job_repo = job_repo
        self._stage_repo = stage_repo
        self._audit_repo = audit_repo
        self._input_file_service = input_file_service
        self._playbook_queue_service = playbook_queue_service
        self._uuid_generator = uuid_generator

    def execute(self, command: CreateLocalRepoCommand) -> LocalRepoResponse:
        """Execute the create-local-repository stage.

        Args:
            command: CreateLocalRepo command with job details.

        Returns:
            LocalRepoResponse DTO with acceptance details.

        Raises:
            JobNotFoundError: If job does not exist or client mismatch.
            InvalidStateTransitionError: If stage is not in PENDING state.
            InputFilesMissingError: If prerequisite input files are missing.
            InputDirectoryInvalidError: If input directory is invalid.
            QueueUnavailableError: If NFS queue is not accessible.
        """
        self._validate_job(command)
        stage = self._validate_stage(command)

        self._prepare_input_files(command, stage)

        request = self._build_playbook_request(command)
        self._submit_to_queue(command, request, stage)

        self._emit_stage_started_event(command)

        return self._to_response(command, request)

    def _validate_job(self, command: CreateLocalRepoCommand):
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

    def _validate_stage(self, command: CreateLocalRepoCommand) -> Stage:
        """Validate stage exists and is in PENDING state."""
        stage_name = StageName(StageType.CREATE_LOCAL_REPOSITORY.value)
        stage = self._stage_repo.find_by_job_and_name(command.job_id, stage_name)

        if stage is None:
            raise JobNotFoundError(
                job_id=str(command.job_id),
                correlation_id=str(command.correlation_id),
            )

        return stage

    def _prepare_input_files(
        self,
        command: CreateLocalRepoCommand,
        stage: Stage,
    ) -> None:
        """Prepare input files as prerequisite for playbook execution.

        If input preparation fails, the stage is transitioned to FAILED
        and the error is re-raised to prevent playbook invocation.
        """
        try:
            self._input_file_service.prepare_playbook_input(
                job_id=str(command.job_id),
                correlation_id=str(command.correlation_id),
            )
        except (InputFilesMissingError, InputDirectoryInvalidError) as exc:
            stage.start()
            stage.fail(
                error_code=type(exc).__name__.upper(),
                error_summary=exc.message,
            )
            self._stage_repo.save(stage)
            log_secure_info(
                "error",
                f"Input preparation failed for job {command.job_id}",
                str(command.correlation_id),
            )
            raise

    def _build_playbook_request(
        self,
        command: CreateLocalRepoCommand,
    ) -> PlaybookRequest:
        """Build a PlaybookRequest entity from the command."""
        return PlaybookRequest(
            job_id=str(command.job_id),
            stage_name=StageType.CREATE_LOCAL_REPOSITORY.value,
            playbook_path=PlaybookPath(DEFAULT_PLAYBOOK_NAME),
            extra_vars=ExtraVars(values={}),
            correlation_id=str(command.correlation_id),
            timeout=ExecutionTimeout.default(),
            submitted_at=datetime.now(timezone.utc).isoformat() + "Z",
            request_id=str(self._uuid_generator.generate()),
        )

    def _submit_to_queue(
        self,
        command: CreateLocalRepoCommand,
        request: PlaybookRequest,
        stage: Stage,
    ) -> None:
        """Submit playbook request to NFS queue for watcher service."""
        stage.start()
        self._stage_repo.save(stage)

        # Submit request to NFS queue
        self._playbook_queue_service.submit_request(
            request=request,
            correlation_id=str(command.correlation_id),
        )

        logger.info(
            "Playbook request submitted to queue for job %s, stage=%s, correlation_id=%s",
            command.job_id,
            StageType.CREATE_LOCAL_REPOSITORY.value,
            command.correlation_id,
        )


    def _emit_stage_started_event(
        self,
        command: CreateLocalRepoCommand,
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
                "stage_name": StageType.CREATE_LOCAL_REPOSITORY.value,
            },
        )
        self._audit_repo.save(event)

    def _to_response(
        self,
        command: CreateLocalRepoCommand,
        request: PlaybookRequest,
    ) -> LocalRepoResponse:
        """Map to response DTO."""
        return LocalRepoResponse(
            job_id=str(command.job_id),
            stage_name=StageType.CREATE_LOCAL_REPOSITORY.value,
            status="accepted",
            submitted_at=request.submitted_at,
            correlation_id=str(command.correlation_id),
        )
