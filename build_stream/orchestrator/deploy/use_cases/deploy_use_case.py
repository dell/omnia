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

"""Deploy use case implementation."""

from datetime import datetime, timezone

from api.logging_utils import log_secure_info

from core.image_group.repositories import ImageGroupRepository
from core.image_group.state_machine import STATUS_FLOW, guard_check
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
from core.deploy.entities import DeployPlaybookRequest
from core.deploy.exceptions import DeployExecutionError
from core.deploy.services import DeployQueueService

from orchestrator.deploy.commands.deploy_command import DeployCommand
from orchestrator.deploy.dtos.deploy_response import DeployResponseDTO

PROVISION_PLAYBOOK_NAME = "provision.yml"
DEFAULT_TIMEOUT_MINUTES = 60


class DeployUseCase:
    """Use case for triggering the deploy stage.

    Orchestrates deployment with:
    - Job existence and ownership verification
    - Upstream build stage guard enforcement
    - ImageGroup guard checks (exists, ID match, status in retryable set)
    - ImageGroup status transition: any retryable status -> DEPLOYING
    - Stage record creation (IN_PROGRESS)
    - NFS queue submission for provision playbook
    - Audit trail emission

    Note: Deploy is an intermediate stage. It does NOT mark the job as
    completed on success. Job completion is handled by downstream stages
    (restart -> validate).
    """

    def __init__(
        self,
        job_repo: JobRepository,
        stage_repo: StageRepository,
        audit_repo: AuditEventRepository,
        image_group_repo: ImageGroupRepository,
        queue_service: DeployQueueService,
        uuid_generator: UUIDGenerator,
    ) -> None:  # pylint: disable=too-many-arguments,too-many-positional-arguments
        """Initialize use case with repository and service dependencies.

        Args:
            job_repo: Job repository implementation.
            stage_repo: Stage repository implementation.
            audit_repo: Audit event repository implementation.
            image_group_repo: ImageGroup repository implementation.
            queue_service: Deploy queue service for NFS submission.
            uuid_generator: UUID generator for identifiers.
        """
        self._job_repo = job_repo
        self._stage_repo = stage_repo
        self._audit_repo = audit_repo
        self._image_group_repo = image_group_repo
        self._queue_service = queue_service
        self._uuid_generator = uuid_generator

    def execute(self, command: DeployCommand) -> DeployResponseDTO:
        """Execute the deploy stage.

        Args:
            command: Deploy command with job details.

        Returns:
            DeployResponseDTO with acceptance details.

        Raises:
            JobNotFoundError: If job does not exist or client mismatch.
            ImageGroupNotFoundError: If no ImageGroup for this job.
            ImageGroupMismatchError: If supplied ID doesn't match.
            InvalidStateTransitionError: If ImageGroup not in BUILT status.
            UpstreamStageNotCompletedError: If build-image not completed.
            DeployExecutionError: If queue submission fails.
        """
        # [1] Validate job
        self._validate_job(command)

        # [2] Enforce upstream build stage guard
        self._enforce_stage_guard(command)

        # [3] Fetch ImageGroup and validate
        image_group = self._image_group_repo.find_by_job_id_for_update(command.job_id)
        guard_check(
            image_group=image_group,
            stage_name="deploy",
            requested_image_group_id=str(command.image_group_id),
        )

        # [4] Transition ImageGroup status -> DEPLOYING
        on_start_status, _, _ = STATUS_FLOW["deploy"]
        self._image_group_repo.update_status(
            image_group_id=image_group.id,
            new_status=on_start_status,  # DEPLOYING
        )

        # [5] Validate stage record
        stage = self._validate_stage(command)

        # [6] Create deploy request and submit to queue
        request = self._create_request(command)
        self._submit_to_queue(command, request, stage)

        # [7] Emit audit event
        self._emit_stage_started_event(command)

        # [8] Return response
        return self._to_response(command, request)

    def _validate_job(self, command: DeployCommand):
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

    def _enforce_stage_guard(self, command: DeployCommand) -> None:
        """Enforce that at least one build-image stage has completed.

        The deploy stage requires that at least one of the build-image
        stages (x86_64 or aarch64) has completed successfully.
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
            x86_state = x86_stage.stage_state.value if x86_stage else "NOT_FOUND"
            aarch64_state = aarch64_stage.stage_state.value if aarch64_stage else "NOT_FOUND"

            raise UpstreamStageNotCompletedError(
                job_id=str(command.job_id),
                required_stage="build-image-x86_64 or build-image-aarch64",
                actual_state=f"x86_64: {x86_state}, aarch64: {aarch64_state}",
                correlation_id=str(command.correlation_id),
            )

    def _validate_stage(self, command: DeployCommand) -> Stage:
        """Validate stage exists; reset to PENDING if in a retryable terminal state."""
        stage_name = StageName(StageType.DEPLOY.value)
        stage = self._stage_repo.find_by_job_and_name(command.job_id, stage_name)

        if stage is None:
            raise JobNotFoundError(
                job_id=str(command.job_id),
                correlation_id=str(command.correlation_id),
            )

        if stage.stage_state in {StageState.FAILED, StageState.COMPLETED}:
            stage.reset()
            self._stage_repo.save(stage)

        if stage.stage_state != StageState.PENDING:
            raise InvalidStateTransitionError(
                entity_type="Stage",
                entity_id=f"{command.job_id}/deploy",
                from_state=stage.stage_state.value,
                to_state="IN_PROGRESS",
                correlation_id=str(command.correlation_id),
            )

        return stage

    def _create_request(self, command: DeployCommand) -> DeployPlaybookRequest:
        """Create deploy playbook request entity."""
        playbook_path = PlaybookPath(PROVISION_PLAYBOOK_NAME)

        extra_vars_dict = {
            "job_id": str(command.job_id),
            "image_key": str(command.image_group_id),
            "image_group_id": str(command.image_group_id),
        }
        extra_vars = ExtraVars(extra_vars_dict)

        return DeployPlaybookRequest(
            job_id=str(command.job_id),
            stage_name=StageType.DEPLOY.value,
            playbook_path=playbook_path,
            extra_vars=extra_vars,
            correlation_id=str(command.correlation_id),
            timeout=ExecutionTimeout(DEFAULT_TIMEOUT_MINUTES),
            submitted_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            request_id=str(self._uuid_generator.generate()),
        )

    def _submit_to_queue(
        self,
        command: DeployCommand,
        request: DeployPlaybookRequest,
        stage: Stage,
    ) -> None:
        """Submit playbook request to NFS queue for watcher service."""
        try:
            stage.start()
            self._stage_repo.save(stage)
        except Exception as save_exc:
            log_secure_info(
                "warning",
                f"Stage start save failed, continuing with queue submission: {save_exc}",
                job_id=str(command.job_id),
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
                stage.fail(error_code=error_code, error_summary=error_summary)
                self._stage_repo.save(stage)

                JobStateHelper.handle_stage_failure(
                    job_repo=self._job_repo,
                    audit_repo=self._audit_repo,
                    uuid_generator=self._uuid_generator,
                    job_id=command.job_id,
                    stage_name=StageType.DEPLOY.value,
                    error_code=error_code,
                    error_summary=error_summary,
                    correlation_id=str(command.correlation_id),
                    client_id=str(command.client_id),
                )
            except Exception as save_exc:
                log_secure_info(
                    "warning",
                    f"Stage fail save failed, stage already modified elsewhere: {save_exc}",
                    job_id=str(command.job_id),
                )
            log_secure_info(
                "error",
                f"Queue submission failed for job {command.job_id}",
                str(command.correlation_id),
            )
            raise DeployExecutionError(
                message=f"Failed to submit deploy request: {exc}",
                correlation_id=str(command.correlation_id),
            ) from exc

        log_secure_info(
            "info",
            f"Deploy request submitted to queue for job {command.job_id}",
            identifier=str(command.correlation_id),
            job_id=str(command.job_id),
        )

    def _emit_stage_started_event(self, command: DeployCommand) -> None:
        """Emit an audit event for stage start."""
        event = AuditEvent(
            event_id=str(self._uuid_generator.generate()),
            job_id=command.job_id,
            event_type="STAGE_STARTED",
            correlation_id=command.correlation_id,
            client_id=command.client_id,
            timestamp=datetime.now(timezone.utc),
            details={"stage_name": StageType.DEPLOY.value},
        )
        self._audit_repo.save(event)

    def _to_response(
        self,
        command: DeployCommand,
        request: DeployPlaybookRequest,
    ) -> DeployResponseDTO:
        """Map to response DTO."""
        return DeployResponseDTO(
            job_id=str(command.job_id),
            stage_name=StageType.DEPLOY.value,
            status="accepted",
            submitted_at=request.submitted_at,
            image_group_id=str(command.image_group_id),
            correlation_id=str(command.correlation_id),
        )
