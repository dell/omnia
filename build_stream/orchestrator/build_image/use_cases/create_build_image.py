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

"""CreateBuildImage use case implementation."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from api.logging_utils import log_secure_info

from core.build_image.entities import BuildImageRequest
from core.build_image.exceptions import (
    InvalidArchitectureError,
    InvalidImageKeyError,
    InvalidFunctionalGroupsError,
    InventoryHostMissingError,
)
from core.build_image.repositories import (
    BuildStreamConfigRepository,
    BuildImageInventoryRepository,
)
from infra.repositories import NfsInputRepository
from core.build_image.services import (
    BuildImageConfigService,
    BuildImageQueueService,
)
from core.build_image.value_objects import (
    Architecture,
    ImageKey,
    FunctionalGroups,
    InventoryHost,
)
from core.localrepo.value_objects import (
    ExecutionTimeout,
    ExtraVars,
    PlaybookPath,
)
from core.jobs.entities import AuditEvent, Stage
from core.jobs.exceptions import (
    JobNotFoundError,
    StageAlreadyCompletedError,
    InvalidStateTransitionError,
)
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

from orchestrator.build_image.commands import CreateBuildImageCommand
from orchestrator.build_image.dtos import BuildImageResponse

logger = logging.getLogger(__name__)

PLAYBOOK_PATHS = {
    "x86_64": "/omnia/build_image_x86_64/build_image_x86_64.yml",
    "aarch64": "/omnia/build_image_aarch64/build_image_aarch64.yml",
}

DEFAULT_TIMEOUT_MINUTES = 60


class CreateBuildImageUseCase:
    """Use case for triggering the build-image stage.

    This use case orchestrates stage execution with the following guarantees:
    - Stage guard enforcement: Only PENDING stages can be started
    - Job ownership verification: Client must own the job
    - Architecture validation: Only x86_64 and aarch64 supported
    - Inventory host validation: Required for aarch64 builds
    - Inventory file creation: Creates inventory file for aarch64 builds
    - Audit trail: Emits STAGE_STARTED event
    - NFS queue submission: Submits playbook request to NFS queue for watcher service

    Attributes:
        job_repo: Job repository port.
        stage_repo: Stage repository port.
        audit_repo: Audit event repository port.
        config_service: Build image configuration service.
        queue_service: Build image queue service.
        inventory_repo: Build image inventory repository.
        uuid_generator: UUID generator for events and request IDs.
    """

    def __init__(
        self,
        job_repo: JobRepository,
        stage_repo: StageRepository,
        audit_repo: AuditEventRepository,
        config_service: BuildImageConfigService,
        queue_service: BuildImageQueueService,
        inventory_repo: NfsInputRepository,
        uuid_generator: UUIDGenerator,
    ) -> None:  # pylint: disable=too-many-arguments,too-many-positional-arguments
        """Initialize use case with repository and service dependencies.

        Args:
            job_repo: Job repository implementation.
            stage_repo: Stage repository implementation.
            audit_repo: Audit event repository implementation.
            config_service: Build image configuration service.
            queue_service: Build image queue service.
            inventory_repo: Build image inventory repository.
            uuid_generator: UUID generator for identifiers.
        """
        self._job_repo = job_repo
        self._stage_repo = stage_repo
        self._audit_repo = audit_repo
        self._config_service = config_service
        self._queue_service = queue_service
        self._inventory_repo = inventory_repo
        self._uuid_generator = uuid_generator

    def execute(self, command: CreateBuildImageCommand) -> BuildImageResponse:
        """Execute the build-image stage.

        Args:
            command: CreateBuildImage command with job details.

        Returns:
            BuildImageResponse DTO with acceptance details.

        Raises:
            JobNotFoundError: If job does not exist or client mismatch.
            InvalidStateTransitionError: If stage is not in PENDING state.
            InvalidArchitectureError: If architecture is not supported.
            InvalidImageKeyError: If image key format is invalid.
            InvalidFunctionalGroupsError: If functional groups are invalid.
            InventoryHostMissingError: If aarch64 requires host but none configured.
            QueueUnavailableError: If NFS queue is not accessible.
        """
        self._validate_job(command)
        architecture = self._validate_architecture(command)
        stage = self._validate_stage(command, architecture)
        image_key = self._validate_image_key(command)
        functional_groups = self._validate_functional_groups(command)

        inventory_host = self._get_inventory_host(command, architecture, stage)
        
        # Create inventory file for aarch64 builds
        inventory_file_path = None
        if inventory_host:
            inventory_file_path = self._create_inventory_file(
                command, inventory_host, stage
            )

        request = self._build_playbook_request(
            command,
            architecture,
            image_key,
            functional_groups,
            inventory_file_path,
        )
        self._submit_to_queue(command, request, stage, architecture)

        self._emit_stage_started_event(command, architecture, image_key)

        return self._to_response(command, request, architecture, image_key)

    def _validate_job(self, command: CreateBuildImageCommand):
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

    def _validate_stage(self, command: CreateBuildImageCommand, architecture: Architecture) -> Stage:
        """Validate stage exists and is in PENDING state, with prerequisite completed."""
        from core.jobs.value_objects import StageState
        
        # Check prerequisite stage is completed
        prerequisite_stage = self._stage_repo.find_by_job_and_name(
            command.job_id, 
            StageName(StageType.CREATE_LOCAL_REPOSITORY.value)
        )
        if prerequisite_stage is None:
            raise JobNotFoundError(
                job_id=str(command.job_id),
                correlation_id=str(command.correlation_id),
            )
        
        if prerequisite_stage.stage_state != StageState.COMPLETED:
            raise InvalidStateTransitionError(
                entity_type="Stage",
                entity_id=f"{command.job_id}/create-local-repository",
                from_state=prerequisite_stage.stage_state.value,
                to_state="COMPLETED",
                correlation_id=str(command.correlation_id),
            )
        
        # Use architecture-specific stage type
        if architecture.is_x86_64:
            stage_type = StageType.BUILD_IMAGE_X86_64
        else:
            stage_type = StageType.BUILD_IMAGE_AARCH64
            
        stage_name = StageName(stage_type.value)
        stage = self._stage_repo.find_by_job_and_name(command.job_id, stage_name)

        if stage is None:
            raise JobNotFoundError(
                job_id=str(command.job_id),
                correlation_id=str(command.correlation_id),
            )
        
        # Only allow PENDING stages to transition to IN_PROGRESS
        if stage.stage_state == StageState.COMPLETED:
            raise StageAlreadyCompletedError(
                job_id=str(command.job_id),
                stage_name=stage_type.value,
                correlation_id=str(command.correlation_id),
            )
        
        if stage.stage_state != StageState.PENDING:
            raise InvalidStateTransitionError(
                entity_type="Stage",
                entity_id=f"{command.job_id}/{stage_type.value}",
                from_state=stage.stage_state.value,
                to_state="IN_PROGRESS",
                correlation_id=str(command.correlation_id),
            )

        return stage

    def _validate_architecture(
        self,
        command: CreateBuildImageCommand,
    ) -> Architecture:
        """Validate and create Architecture value object."""
        try:
            return Architecture(command.architecture)
        except ValueError as exc:
            raise InvalidArchitectureError(
                message=str(exc),
                correlation_id=str(command.correlation_id),
            ) from exc

    def _validate_image_key(self, command: CreateBuildImageCommand) -> ImageKey:
        """Validate and create ImageKey value object."""
        try:
            return ImageKey(command.image_key)
        except ValueError as exc:
            raise InvalidImageKeyError(
                message=str(exc),
                correlation_id=str(command.correlation_id),
            ) from exc

    def _validate_functional_groups(
        self,
        command: CreateBuildImageCommand,
    ) -> FunctionalGroups:
        """Validate and create FunctionalGroups value object."""
        try:
            return FunctionalGroups(command.functional_groups)
        except ValueError as exc:
            raise InvalidFunctionalGroupsError(
                message=str(exc),
                correlation_id=str(command.correlation_id),
            ) from exc

    def _get_inventory_host(
        self,
        command: CreateBuildImageCommand,
        architecture: Architecture,
        stage: Stage,
    ):
        """Get inventory host for aarch64 builds.

        Priority:
        1. Use inventory_host from command if provided (from API request)
        2. Fall back to config service (from build_stream_config.yml)

        If inventory host retrieval fails, the stage is transitioned to FAILED
        and the error is re-raised to prevent playbook invocation.
        """
        # If inventory_host is provided in the command, use it directly
        if command.inventory_host:
            try:
                return InventoryHost(command.inventory_host)
            except ValueError as exc:
                stage.start()
                stage.fail(
                    error_code="INVALID_INVENTORY_HOST",
                    error_summary=f"Invalid inventory host format: {str(exc)}",
                )
                self._stage_repo.save(stage)
                log_secure_info(
                    "error",
                    f"Invalid inventory host for job {command.job_id}",
                    str(command.correlation_id),
                )
                raise InventoryHostMissingError(
                    message=f"Invalid inventory host format: {str(exc)}",
                    correlation_id=str(command.correlation_id),
                ) from exc
        
        # Fall back to config service for backward compatibility
        try:
            return self._config_service.get_inventory_host(
                job_id=str(command.job_id),
                architecture=architecture,
                correlation_id=str(command.correlation_id),
            )
        except InventoryHostMissingError as exc:
            stage.start()
            stage.fail(
                error_code="INVENTORY_HOST_MISSING",
                error_summary=exc.message,
            )
            self._stage_repo.save(stage)
            log_secure_info(
                "error",
                f"Inventory host missing for job {command.job_id}",
                str(command.correlation_id),
            )
            raise

    def _create_inventory_file(
        self,
        command: CreateBuildImageCommand,
        inventory_host: InventoryHost,
        stage: Stage,
    ) -> Optional[Path]:
        """Create inventory file for aarch64 builds.

        Args:
            command: CreateBuildImage command.
            inventory_host: Inventory host IP.
            stage: Current stage entity.

        Returns:
            Path to created inventory file.

        Raises:
            IOError: If inventory file creation fails.
        """
        try:
            inventory_file_path = self._inventory_repo.create_inventory_file(
                inventory_host=inventory_host,
                job_id=str(command.job_id),
            )
            logger.info(
                "Created inventory file for job %s at %s",
                command.job_id,
                inventory_file_path,
            )
            return inventory_file_path
        except IOError as exc:
            stage.start()
            stage.fail(
                error_code="INVENTORY_FILE_CREATION_FAILED",
                error_summary=f"Failed to create inventory file: {str(exc)}",
            )
            self._stage_repo.save(stage)
            log_secure_info(
                "error",
                f"Failed to create inventory file for job {command.job_id}",
                str(command.correlation_id),
            )
            raise

    def _build_playbook_request(
        self,
        command: CreateBuildImageCommand,
        architecture: Architecture,
        image_key: ImageKey,
        functional_groups: FunctionalGroups,
        inventory_file_path: Optional[Path],
    ) -> BuildImageRequest:
        """Compatibility shim matching historical naming used by execute()."""
        return self._create_request(
            command,
            architecture,
            image_key,
            functional_groups,
            inventory_file_path,
        )

    def _create_request(
        self,
        command: CreateBuildImageCommand,
        architecture: Architecture,
        image_key: ImageKey,
        functional_groups: FunctionalGroups,
        inventory_file_path: Optional[Path],
    ) -> BuildImageRequest:
        """Create BuildImageRequest entity."""
        # Determine playbook path based on architecture
        full_path = PLAYBOOK_PATHS[architecture.value]
        playbook_name = full_path.split("/")[-1]  # Extract filename from full path
        playbook_path = PlaybookPath(playbook_name)

        # Build extra vars dictionary
        extra_vars_dict = {
            "job_id": str(command.job_id),
            "image_key": str(image_key),
            "functional_groups": functional_groups.to_list(),
        }

        extra_vars = ExtraVars(extra_vars_dict)

        return BuildImageRequest(
            job_id=str(command.job_id),
            stage_name="build-image-x86_64" if architecture.is_x86_64 else "build-image-aarch64",
            playbook_path=playbook_path,
            extra_vars=extra_vars,
            inventory_file_path=str(inventory_file_path) if inventory_file_path else None,
            correlation_id=str(command.correlation_id),
            timeout=ExecutionTimeout(60),  # TODO: Make configurable
            submitted_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            request_id=str(self._uuid_generator.generate()),
        )

    def _submit_to_queue(
        self,
        command: CreateBuildImageCommand,
        request: BuildImageRequest,
        stage: Stage,
        architecture: Architecture,
    ) -> None:
        """Submit playbook request to NFS queue for watcher service."""
        stage.start()
        self._stage_repo.save(stage)

        self._queue_service.submit_request(
            request=request,
            correlation_id=str(command.correlation_id),
        )

        # Use architecture-specific stage type for logging
        stage_type = StageType.BUILD_IMAGE_X86_64 if architecture.is_x86_64 else StageType.BUILD_IMAGE_AARCH64
        logger.info(
            "Build image request submitted to queue for job %s, stage=%s, "
            "arch=%s, correlation_id=%s",
            command.job_id,
            stage_type.value,
            str(architecture),
            command.correlation_id,
        )

    def _emit_stage_started_event(
        self,
        command: CreateBuildImageCommand,
        architecture: Architecture,
        image_key: ImageKey,
    ) -> None:
        """Emit an audit event for stage start."""
        # Use architecture-specific stage type for audit event
        stage_type = StageType.BUILD_IMAGE_X86_64 if architecture.is_x86_64 else StageType.BUILD_IMAGE_AARCH64
        event = AuditEvent(
            event_id=str(self._uuid_generator.generate()),
            job_id=command.job_id,
            event_type="STAGE_STARTED",
            correlation_id=command.correlation_id,
            client_id=command.client_id,
            timestamp=datetime.now(timezone.utc),
            details={
                "stage_name": stage_type.value,
                "architecture": str(architecture),
                "image_key": str(image_key),
            },
        )
        self._audit_repo.save(event)

    def _to_response(
        self,
        command: CreateBuildImageCommand,
        request: BuildImageRequest,
        architecture: Architecture,
        image_key: ImageKey,
    ) -> BuildImageResponse:
        """Map to response DTO."""
        # Use architecture-specific stage type for response
        stage_type = StageType.BUILD_IMAGE_X86_64 if architecture.is_x86_64 else StageType.BUILD_IMAGE_AARCH64
        return BuildImageResponse(
            job_id=str(command.job_id),
            stage_name=stage_type.value,
            status="accepted",
            submitted_at=request.submitted_at,
            correlation_id=str(command.correlation_id),
            architecture=str(architecture),
            image_key=str(image_key),
            functional_groups=command.functional_groups,
        )
