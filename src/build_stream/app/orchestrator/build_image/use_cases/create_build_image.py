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

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from api.logging_utils import log_secure_info

from core.build_image.entities import BuildImageRequest
from core.build_image.services import (
    BuildImageConfigService,
    BuildImageQueueService,
)
from core.cleanup.exceptions import RetentionLimitExceededError
from core.common.playbook_registry import get_playbook_path
from core.image_group.repositories import ImageGroupRepository
from core.jobs.entities import AuditEvent, Stage
from core.jobs.exceptions import (
    JobNotFoundError,
    StageNotFoundError,
    StageAlreadyCompletedError,
    InvalidStateTransitionError,
    UpstreamStageNotCompletedError,
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
from infra.repositories import NfsInputRepository
from orchestrator.build_image.commands import CreateBuildImageCommand
from orchestrator.build_image.dtos import BuildImageResponse


# Domain-segregated (Omnia 2.3+): a single image_build_manager.yml entry
# point handles every architecture.  Callers no longer select a playbook
# per architecture -- the playbook reads the catalog and dispatches
# internally.  Resolved here at import time so a missing registry entry
# fails fast at startup rather than on the first build request.
if get_playbook_path("image_build_manager.yml") is None:
    raise RuntimeError(
        "Playbook 'image_build_manager.yml' not found in playbook_paths.yml. "
        "Verify that playbook_paths.yml is present and OMNIA_SRC_PATH is set correctly."
    )

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
        image_group_repo: Optional[ImageGroupRepository] = None,
        retention_limit: Optional[int] = None,
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
            image_group_repo: Optional ImageGroup repository (used for
                the image-retention-limit guard). When omitted the
                guard is silently skipped (e.g. dev/test profiles).
            retention_limit: Maximum allowed number of non-CLEANED
                ImageGroups (default: read from
                ``IMAGE_RETENTION_LIMIT`` env var or 50).
        """
        self._job_repo = job_repo
        self._stage_repo = stage_repo
        self._audit_repo = audit_repo
        self._config_service = config_service
        self._queue_service = queue_service
        self._inventory_repo = inventory_repo
        self._uuid_generator = uuid_generator
        self._image_group_repo = image_group_repo
        if retention_limit is not None:
            self._retention_limit = retention_limit
        else:
            try:
                self._retention_limit = int(
                    os.environ.get("IMAGE_RETENTION_LIMIT", "50")
                )
            except (TypeError, ValueError):
                self._retention_limit = 50

    def execute(self, command: CreateBuildImageCommand) -> BuildImageResponse:
        """Execute the build-image stage.

        Domain-segregated (Omnia 2.3+): The image_build_manager.yml playbook
        reads the catalog directly and builds all images for all architectures.

        Args:
            command: CreateBuildImage command with job_id only.

        Returns:
            BuildImageResponse DTO with acceptance details.

        Raises:
            JobNotFoundError: If job does not exist or client mismatch.
            InvalidStateTransitionError: If stage is not in PENDING state.
            QueueUnavailableError: If NFS queue is not accessible.
        """
        self._validate_job(command)
        stage = self._validate_stage_unified(command)
        request = self._build_unified_playbook_request(command)
        self._submit_to_queue_unified(command, request, stage)
        self._emit_stage_started_event_unified(command)
        return self._to_response_unified(command, request)

    def _enforce_retention_limit(
        self, command: CreateBuildImageCommand
    ) -> None:
        """Block new builds when the image retention limit is reached."""
        if self._image_group_repo is None:
            return
        try:
            current_count = self._image_group_repo.count_non_cleaned()
        except Exception as exc:  # pylint: disable=broad-except
            log_secure_info(
                "warning",
                f"Retention limit check skipped due to error: {exc}",
                job_id=str(command.job_id),
            )
            return

        if current_count > self._retention_limit:
            log_secure_info(
                "warning",
                f"Build aborted: retention limit reached "
                f"({current_count}/{self._retention_limit}) for "
                f"job_id={command.job_id}",
                job_id=str(command.job_id),
            )
            raise RetentionLimitExceededError(
                current_count=current_count,
                limit=self._retention_limit,
            )

    def _persist_build_image_metadata(
        self,
        job_id: str,
        image_key: str,
        architecture: str,
        functional_groups: list,
    ) -> None:
        """Persist build-image metadata to NFS for the result poller.

        The metadata is written to ``<artifact_base>/artifacts/<job_id>/build_image_meta.json``
        so the result poller can reconstruct complete S3 image paths
        once the build completes.
        """
        try:
            base = os.environ.get(
                "NFS_ARTIFACT_BASE",
                os.path.join(os.getenv("OMNIA_DATA_PATH", "/opt/omnia"), "build_stream_root")
            )
            job_dir = Path(base) / "artifacts" / job_id
            job_dir.mkdir(parents=True, exist_ok=True)
            meta_path = job_dir / "build_image_meta.json"
            payload = {
                "image_key": image_key,
                "architecture": architecture,
                "functional_groups": functional_groups,
                "written_at": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            }
            meta_path.write_text(json.dumps(payload), encoding="utf-8")
            log_secure_info(
                "info",
                f"Persisted build_image_meta to {meta_path}",
                job_id=job_id,
            )
        except OSError as exc:
            # Non-fatal: result poller will fall back to legacy naming.
            log_secure_info(
                "warning",
                f"Could not persist build_image_meta for job={job_id}: "
                f"{exc}",
                job_id=job_id,
            )

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

    def _verify_upstream_stage_completed(
        self, command: CreateBuildImageCommand
    ) -> None:
        """Verify that create-local-repository stage is COMPLETED."""
        prerequisite_stage = self._stage_repo.find_by_job_and_name(
            command.job_id,
            StageName(StageType.CREATE_LOCAL_REPOSITORY.value)
        )
        if (
            prerequisite_stage is None
            or prerequisite_stage.stage_state != StageState.COMPLETED
        ):
            raise UpstreamStageNotCompletedError(
                job_id=str(command.job_id),
                required_stage="create-local-repository",
                actual_state=(
                    prerequisite_stage.stage_state.value
                    if prerequisite_stage
                    else "NOT_FOUND"
                ),
                correlation_id=str(command.correlation_id),
            )

    # ========================================================================
    # Unified Domain-Segregated Methods (Omnia 2.3+)
    # ========================================================================

    def _validate_stage_unified(self, command: CreateBuildImageCommand) -> Stage:
        """Validate unified BUILD_IMAGE stage exists; reset if FAILED for retry.

        Follows the same pattern as create-local-repository and other stages:
        - FAILED  → auto-reset to PENDING (retry) + resume job state
        - COMPLETED → reject (build stages are immutable once complete)
        - IN_PROGRESS → reject (already running)
        - PENDING → proceed
        """
        # Verify upstream stage is completed
        self._verify_upstream_stage_completed(command)

        # Use unified BUILD_IMAGE stage
        stage = self._stage_repo.find_by_job_and_name(
            command.job_id,
            StageName(StageType.BUILD_IMAGE.value),
        )

        if stage is None:
            raise StageNotFoundError(
                job_id=str(command.job_id),
                stage_name=StageType.BUILD_IMAGE.value,
                correlation_id=str(command.correlation_id),
            )

        # Reset FAILED stages for retry (build stages don't support re-run from COMPLETED)
        if stage.stage_state == StageState.FAILED:
            prev_state = stage.stage_state.value
            stage.reset()
            self._stage_repo.save(stage)
            log_secure_info(
                "info",
                f"Resetting {StageType.BUILD_IMAGE.value} stage from {prev_state} to PENDING "
                f"for retry (attempt {stage.attempt}): job_id={command.job_id}",
                job_id=str(command.job_id),
            )
            # Resume job from FAILED to IN_PROGRESS so CI polling doesn't exit early
            JobStateHelper.handle_job_resume(
                job_repo=self._job_repo,
                audit_repo=self._audit_repo,
                uuid_generator=self._uuid_generator,
                job_id=command.job_id,
                stage_name=StageType.BUILD_IMAGE.value,
                correlation_id=str(command.correlation_id),
                client_id=str(command.client_id),
            )

        # Only allow PENDING stages to transition to IN_PROGRESS
        if stage.stage_state == StageState.COMPLETED:
            raise StageAlreadyCompletedError(
                job_id=str(command.job_id),
                stage_name=StageType.BUILD_IMAGE.value,
                correlation_id=str(command.correlation_id),
            )

        if stage.stage_state != StageState.PENDING:
            raise InvalidStateTransitionError(
                entity_type="Stage",
                entity_id=f"{command.job_id}/{StageType.BUILD_IMAGE.value}",
                from_state=stage.stage_state.value,
                to_state="IN_PROGRESS",
                correlation_id=str(command.correlation_id),
            )

        return stage

    def _build_unified_playbook_request(
        self, command: CreateBuildImageCommand
    ) -> BuildImageRequest:
        """Create unified playbook request with job_id only."""
        # Use image_build_manager.yml playbook
        full_path = get_playbook_path("image_build_manager.yml")
        if full_path is None:
            raise RuntimeError(
                "Playbook 'image_build_manager.yml' not found in playbook_paths.yml"
            )
        playbook_name = full_path.split("/")[-1]
        playbook_path = PlaybookPath(playbook_name)

        # Only pass job_id - playbook reads catalog for everything else.
        # Rebuild control is handled by build_image.force_rebuild in the
        # pipeline configuration (build_stream_config.yml), not here.
        extra_vars_dict = {
            "job_id": str(command.job_id),
        }
        extra_vars = ExtraVars(extra_vars_dict)

        return BuildImageRequest(
            job_id=str(command.job_id),
            stage_name=StageType.BUILD_IMAGE.value,
            playbook_path=playbook_path,
            extra_vars=extra_vars,
            inventory_file_path=None,  # Not needed, playbook handles inventory
            correlation_id=str(command.correlation_id),
            timeout=ExecutionTimeout(60),
            submitted_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            request_id=str(self._uuid_generator.generate()),
            tags="execute",
        )

    def _submit_to_queue_unified(
        self,
        command: CreateBuildImageCommand,
        request: BuildImageRequest,
        stage: Stage,
    ) -> None:
        """Submit unified playbook request to NFS queue."""
        try:
            stage.start()
            self._stage_repo.save(stage)
        except Exception as save_exc:  # pylint: disable=broad-exception-caught
            log_secure_info(
                "warning",
                f"Stage start save failed, continuing with queue submission: {save_exc}",
            )

        # Submit request to NFS queue
        self._queue_service.submit_request(
            request=request,
            correlation_id=str(command.correlation_id),
        )

        log_secure_info(
            'info',
            f"Playbook request submitted to queue for job {command.job_id}, "
            f"stage={StageType.BUILD_IMAGE.value}, "
            f"correlation_id={command.correlation_id}",
        )

    def _emit_stage_started_event_unified(
        self, command: CreateBuildImageCommand
    ) -> None:
        """Emit audit event for unified BUILD_IMAGE stage start."""
        event = AuditEvent(
            event_id=str(self._uuid_generator.generate()),
            job_id=command.job_id,
            event_type="STAGE_STARTED",
            correlation_id=command.correlation_id,
            client_id=command.client_id,
            timestamp=datetime.now(timezone.utc),
            details={
                "stage": StageType.BUILD_IMAGE.value,
                "mode": "unified",
                "note": "Playbook reads catalog and builds all architectures",
            },
        )
        self._audit_repo.save(event)

    def _to_response_unified(
        self, command: CreateBuildImageCommand, request: BuildImageRequest
    ) -> BuildImageResponse:
        """Map unified request to response DTO."""
        return BuildImageResponse(
            job_id=str(command.job_id),
            stage_name=StageType.BUILD_IMAGE.value,
            status="accepted",
            submitted_at=request.submitted_at,
            correlation_id=str(command.correlation_id),
            architecture=None,
            image_key=None,
            functional_groups=None,
        )
