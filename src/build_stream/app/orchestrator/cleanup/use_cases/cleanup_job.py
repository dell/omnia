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

"""CleanUp Job use case (hard delete with S3 + NFS cleanup).

Implements the orchestration for the enhanced ``DELETE /api/v1/jobs/{job_id}``
endpoint:

1. Resolve Job + ImageGroup (1:1 mapping) and validate ownership.
2. Validate ImageGroup state (block when ``DEPLOYING``/``RESTARTING``/
   ``VALIDATING``; reject if already ``CLEANED``).
3. Query the ``images`` table for all S3 paths and delete each via
   ``s3cmd``.
4. Remove the per-Job NFS artifact directory.
5. Transition ImageGroup -> ``CLEANED`` and Job -> ``CLEANED`` (cancelling
   any non-terminal stages along the way for audit completeness).
6. Emit an audit event describing the cleanup outcome.
"""

import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from api.logging_utils import log_secure_info
from core.cleanup.exceptions import (
    AlreadyCleanedError,
    CleanupNfsFailedError,
    CleanupStateInvalidError,
)
from core.cleanup.s3_service import S3CleanupService
from core.image_group.entities import Image, ImageGroup
from core.image_group.repositories import (
    ImageGroupRepository,
    ImageRepository,
)
from core.image_group.value_objects import ImageGroupStatus
from core.jobs.entities import AuditEvent
from core.jobs.exceptions import JobNotFoundError
from core.jobs.repositories import (
    AuditEventRepository,
    JobRepository,
    StageRepository,
    UUIDGenerator,
)
from orchestrator.cleanup.commands.cleanup_job import CleanupJobCommand
from orchestrator.cleanup.dtos.cleanup_response import CleanupResult

# Image-group statuses where a cleanup is forbidden because a stage is
# actively running.
ACTIVE_STATUSES = {
    ImageGroupStatus.DEPLOYING.value,
    ImageGroupStatus.RESTARTING.value,
    ImageGroupStatus.VALIDATING.value,
}

DEFAULT_NFS_ARTIFACT_BASE = "/opt/omnia/build_stream_root"


@dataclass
class _CleanupContext:
    """Internal helper bundling resolved entities for clarity."""

    job: object
    image_group: ImageGroup
    images: List[Image]
    image_group_id_str: str


class CleanupJobUseCase:
    """Hard-delete a Job's artifacts and S3 images.

    Used by both the synchronous ``DELETE`` API and the automated
    cron-based cleanup of FAILED ImageGroups.
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        job_repo: JobRepository,
        stage_repo: StageRepository,
        audit_repo: AuditEventRepository,
        image_group_repo: ImageGroupRepository,
        image_repo: ImageRepository,
        s3_cleanup_service: S3CleanupService,
        uuid_generator: UUIDGenerator,
        nfs_artifact_base: Optional[str] = None,
    ) -> None:
        self._job_repo = job_repo
        self._stage_repo = stage_repo
        self._audit_repo = audit_repo
        self._image_group_repo = image_group_repo
        self._image_repo = image_repo
        self._s3_cleanup_service = s3_cleanup_service
        self._uuid_generator = uuid_generator
        self._nfs_artifact_base = (
            nfs_artifact_base
            or os.environ.get("NFS_ARTIFACT_BASE", DEFAULT_NFS_ARTIFACT_BASE)
        )

    # ------------------------------------------------------------------
    # Public entry-point: API-driven (manual) cleanup
    # ------------------------------------------------------------------

    def execute(self, command: CleanupJobCommand) -> CleanupResult:
        """Execute manual cleanup for the given Job.

        Args:
            command: CleanupJobCommand with job_id, client_id, and
                correlation_id.

        Returns:
            CleanupResult describing the outcome.

        Raises:
            JobNotFoundError: Job missing or not owned by this client.
            CleanupStateInvalidError: ImageGroup in active state.
            AlreadyCleanedError: Job already cleaned.
            CleanupS3FailedError: S3 deletion failed (see core.cleanup.exceptions).
            CleanupNfsFailedError: NFS removal failed.
        """
        ctx = self._resolve(
            job_id_str=str(command.job_id),
            client_id_str=str(command.client_id),
            correlation_id_str=str(command.correlation_id),
        )
        return self._perform_cleanup(
            ctx=ctx,
            cleanup_type="manual",
            client_id=str(command.client_id),
            correlation_id=str(command.correlation_id),
        )

    # ------------------------------------------------------------------
    # Public entry-point: cron-based automated cleanup
    # ------------------------------------------------------------------

    def execute_auto(
        self,
        job_id_str: str,
        correlation_id: str,
        reason: str = "auto_cleanup_validation_failed",
    ) -> CleanupResult:
        """Execute cleanup as part of the automated cron job.

        No client ownership is enforced because the cron runs in the
        BuildStream container with full privileges.

        Args:
            job_id_str: Job identifier as a string.
            correlation_id: Tracing identifier.
            reason: Audit reason tag (default
                ``auto_cleanup_validation_failed``).

        Returns:
            CleanupResult describing the outcome.
        """
        ctx = self._resolve(
            job_id_str=job_id_str,
            client_id_str=None,
            correlation_id_str=correlation_id,
        )
        return self._perform_cleanup(
            ctx=ctx,
            cleanup_type="auto",
            client_id="cron",
            correlation_id=correlation_id,
            audit_reason=reason,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(
        self,
        job_id_str: str,
        client_id_str: Optional[str],
        correlation_id_str: str,
    ) -> _CleanupContext:
        """Validate ownership, fetch ImageGroup + images."""
        from core.jobs.value_objects import JobId  # local to avoid cycles

        validated_job_id = JobId(job_id_str)

        job = self._job_repo.find_by_id(validated_job_id)
        if job is None:
            raise JobNotFoundError(job_id_str, correlation_id_str)

        if (
            client_id_str is not None
            and str(job.client_id) != client_id_str
        ):
            raise JobNotFoundError(job_id_str, correlation_id_str)

        image_group = self._image_group_repo.find_by_job_id(validated_job_id)
        if image_group is None:
            # Nothing to clean from S3, but caller may still want NFS
            # cleanup. Raise JobNotFoundError to keep API contract simple
            # for the common case where build-image was never reached.
            raise JobNotFoundError(job_id_str, correlation_id_str)

        image_group_id_str = str(image_group.id)
        current_status = (
            image_group.status.value
            if hasattr(image_group.status, "value")
            else str(image_group.status)
        )

        if current_status == ImageGroupStatus.CLEANED.value:
            raise AlreadyCleanedError(job_id_str)

        if current_status in ACTIVE_STATUSES:
            raise CleanupStateInvalidError(
                image_group_id=image_group_id_str,
                current_status=current_status,
            )

        # Eager load images via the repository (the `find_by_job_id`
        # eager-loads but we use the explicit repo for cron usages).
        images = list(image_group.images or [])
        if not images:
            try:
                images = self._image_repo.find_by_image_group_id(
                    image_group.id
                )
            except Exception:  # pylint: disable=broad-except
                images = []

        return _CleanupContext(
            job=job,
            image_group=image_group,
            images=images,
            image_group_id_str=image_group_id_str,
        )

    def _perform_cleanup(
        self,
        ctx: _CleanupContext,
        cleanup_type: str,
        client_id: str,
        correlation_id: str,
        audit_reason: str = "cleanup_manual",
    ) -> CleanupResult:
        """Run the actual S3 + NFS cleanup and update statuses."""
        # 1. S3 image deletion: iterate over each stored complete path.
        s3_deleted = self._delete_s3_images(ctx, correlation_id)

        # 2. NFS artifact removal.
        nfs_deleted = self._delete_nfs_artifacts(
            job_id=ctx.image_group.job_id, correlation_id=correlation_id
        )

        # 3. Cancel any non-terminal stages for audit cleanliness.
        try:
            stages = self._stage_repo.find_all_by_job(ctx.image_group.job_id)
            for stage in stages:
                if not stage.stage_state.is_terminal():
                    try:
                        stage.cancel()
                        self._stage_repo.save(stage)
                    except Exception:  # pylint: disable=broad-except
                        # Best-effort; never block cleanup on stage save.
                        # Rollback immediately to reset session state
                        if hasattr(self._image_group_repo, "session"):
                            try:
                                self._image_group_repo.session.rollback()
                            except Exception:  # pylint: disable=broad-except
                                pass
                        pass
        except Exception:  # pylint: disable=broad-except
            # Rollback the session to reset state after any stage cancellation error
            if hasattr(self._image_group_repo, "session"):
                try:
                    self._image_group_repo.session.rollback()
                except Exception:  # pylint: disable=broad-except
                    pass
            pass

        # 4. Status transitions: ImageGroup -> CLEANED, Job -> CLEANED.
        self._image_group_repo.update_status(
            image_group_id=ctx.image_group.id,
            new_status=ImageGroupStatus.CLEANED,
        )
        if hasattr(self._image_group_repo, "session"):
            try:
                self._image_group_repo.session.commit()
            except Exception:  # pylint: disable=broad-except
                pass

        # Mark the job as CLEANED via tombstone (existing API). This
        # preserves the audit trail without deleting the row.
        try:
            ctx.job.tombstone()
            self._job_repo.save(ctx.job)
        except Exception:  # pylint: disable=broad-except
            # If already tombstoned, ignore.
            pass

        cleaned_at = (
            datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

        # 5. Audit event.
        try:
            event = AuditEvent(
                event_id=str(self._uuid_generator.generate()),
                job_id=ctx.image_group.job_id,
                event_type="JOB_CLEANED",
                correlation_id=correlation_id,
                client_id=client_id,
                timestamp=datetime.now(timezone.utc),
                details={
                    "image_group_id": ctx.image_group_id_str,
                    "cleanup_type": cleanup_type,
                    "reason": audit_reason,
                    "s3_objects_deleted": s3_deleted,
                    "nfs_files_deleted": nfs_deleted,
                    "image_count": len(ctx.images),
                },
            )
            self._audit_repo.save(event)
        except Exception:  # pylint: disable=broad-except
            log_secure_info(
                "warning",
                f"Failed to record cleanup audit event for job="
                f"{ctx.image_group.job_id}",
                job_id=str(ctx.image_group.job_id),
            )

        log_secure_info(
            "info",
            f"Cleanup completed: job_id={ctx.image_group.job_id}, "
            f"image_group_id={ctx.image_group_id_str}, "
            f"type={cleanup_type}, s3_deleted={s3_deleted}, "
            f"nfs_deleted={nfs_deleted}",
            job_id=str(ctx.image_group.job_id),
        )

        return CleanupResult(
            job_id=str(ctx.image_group.job_id),
            image_group_id=ctx.image_group_id_str,
            status=ImageGroupStatus.CLEANED.value,
            cleanup_type=cleanup_type,
            s3_objects_deleted=s3_deleted,
            nfs_files_deleted=nfs_deleted,
            cleaned_at=cleaned_at,
        )

    def _delete_s3_images(
        self, ctx: _CleanupContext, correlation_id: str
    ) -> int:
        """Delete every stored S3 image_path and return total objects removed."""
        if not ctx.images:
            log_secure_info(
                "info",
                f"S3 cleanup skipped: no image records for "
                f"image_group={ctx.image_group_id_str}",
                job_id=str(ctx.image_group.job_id),
            )
            return 0

        total_deleted = 0
        for img in ctx.images:
            raw_path = (img.image_name or "").strip()
            if not raw_path:
                continue
            # image_name may contain multiple S3 paths separated by ";"
            # (e.g., EFI image dir + full disk image dir for the same role).
            individual_paths = [p.strip() for p in raw_path.split(";") if p.strip()]
            for image_path in individual_paths:
                if not image_path.startswith("s3://"):
                    # Legacy entries (pre-CleanUp release) stored only the
                    # filename; skip with a warning instead of raising.
                    log_secure_info(
                        "warning",
                        f"Skipping non-S3 legacy image_name='{image_path}' "
                        f"for image_group={ctx.image_group_id_str}",
                        job_id=str(ctx.image_group.job_id),
                    )
                    continue
                result = self._s3_cleanup_service.delete_image_path(image_path)
                total_deleted += result.objects_deleted
        log_secure_info(
            "info",
            f"S3 cleanup totals: image_group={ctx.image_group_id_str}, "
            f"objects_deleted={total_deleted}, "
            f"correlation_id={correlation_id}",
            job_id=str(ctx.image_group.job_id),
        )
        return total_deleted

    def _delete_nfs_artifacts(self, job_id, correlation_id: str) -> int:
        """Remove the per-Job NFS artifact directory.

        Returns the number of files deleted (best-effort count).
        """
        artifact_dir = os.path.join(self._nfs_artifact_base, "artifacts", str(job_id))
        if not os.path.exists(artifact_dir):
            log_secure_info(
                "info",
                f"NFS cleanup skipped: directory not found at "
                f"{artifact_dir}",
                job_id=str(job_id),
            )
            return 0

        try:
            file_count = 0
            for _root, _dirs, files in os.walk(artifact_dir):
                file_count += len(files)
            shutil.rmtree(artifact_dir)
            log_secure_info(
                "info",
                f"NFS cleanup removed {file_count} files from "
                f"{artifact_dir} (correlation_id={correlation_id})",
                job_id=str(job_id),
            )
            return file_count
        except OSError as exc:
            raise CleanupNfsFailedError(
                job_id=str(job_id),
                path=artifact_dir,
                error=str(exc),
            ) from exc
