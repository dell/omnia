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

"""CleanUp Job use case (hard delete with playbook-based image cleanup + NFS cleanup).

Implements the orchestration for the enhanced ``DELETE /api/v1/jobs/{job_id}``
endpoint:

1. Resolve Job + ImageGroup (1:1 mapping) and validate ownership.
2. Validate ImageGroup state (block when ``DEPLOYING``/``RESTARTING``/
   ``VALIDATING``; reject if already ``CLEANED``).
3. Submit a cleanup playbook request to the NFS queue
   (``image_build_manager.yml --tags cleanup_images -e skip_approval=true``)
   so the playbook watcher can delete the S3 images associated with the
   image group non-interactively. ``skip_approval`` is required because the
   playbook otherwise gates deletion behind an interactive confirmation
   prompt (``ansible.builtin.pause``) intended for manual CLI runs; without
   it, the playbook watcher (headless, no TTY) always resolves the prompt to
   "not approved" and silently skips every deletion task.
4. Remove the per-Job NFS artifact directory (synchronous, local operation).
5. Transition ImageGroup -> ``CLEANING`` (a non-terminal, retryable state).
   The Job is *not* tombstoned yet and the ImageGroup is *not* marked
   ``CLEANED`` at this point, because S3 deletion is asynchronous: the
   playbook watcher executes the request out-of-band and reports back via
   the NFS result queue. ``ResultPoller`` observes that result and performs
   the final ``CLEANING`` -> ``CLEANED`` transition (and Job tombstoning)
   only once the playbook actually reports success.
6. Emit an audit event describing the cleanup submission outcome.

Note: if no queue service is configured (e.g. certain dev/test wiring),
cleanup falls back to the previous synchronous behavior of marking
ImageGroup/Job as ``CLEANED`` immediately, since there is nothing to wait
on asynchronously in that case.
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
from core.localrepo.entities import PlaybookRequest
from core.localrepo.value_objects import (
    ExecutionTimeout,
    ExtraVars,
    PlaybookPath,
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
CLEANUP_PLAYBOOK_NAME = "image_build_manager.yml"
CLEANUP_PLAYBOOK_TAGS = "cleanup_images"
CLEANUP_TIMEOUT_MINUTES = 30


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
        uuid_generator: UUIDGenerator,
        queue_service=None,
        nfs_artifact_base: Optional[str] = None,
    ) -> None:
        self._job_repo = job_repo
        self._stage_repo = stage_repo
        self._audit_repo = audit_repo
        self._image_group_repo = image_group_repo
        self._image_repo = image_repo
        self._uuid_generator = uuid_generator
        self._queue_service = queue_service
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
        """Run the actual image cleanup (via playbook) + NFS cleanup and update statuses."""
        # 1. Image cleanup: submit image_build_manager.yml --tags cleanup_images
        #    to the NFS queue. The playbook handles S3 object deletion.
        cleanup_submitted = self._submit_cleanup_playbook(ctx, correlation_id)

        # 2. NFS artifact removal.
        nfs_deleted = self._delete_nfs_artifacts(
            job_id=ctx.image_group.job_id, correlation_id=correlation_id
        )

        # 3. Cancel any non-terminal stages for audit cleanliness.
        self._cancel_non_terminal_stages(ctx.image_group.job_id)

        # 4. Status transition. When the cleanup playbook was submitted
        #    successfully, the actual S3 deletion happens asynchronously on
        #    the OIM host; move to the non-terminal CLEANING state and let
        #    ResultPoller finalize to CLEANED once the playbook reports
        #    success. Only fall back to an immediate CLEANED transition
        #    when there's no queue service to report back to us (nothing
        #    to wait on).
        final_status = (
            ImageGroupStatus.CLEANING
            if cleanup_submitted
            else ImageGroupStatus.CLEANED
        )
        self._image_group_repo.update_status(
            image_group_id=ctx.image_group.id,
            new_status=final_status,
        )
        if hasattr(self._image_group_repo, "session"):
            try:
                self._image_group_repo.session.commit()
            except Exception:  # pylint: disable=broad-except
                # nosec B110 - Best-effort commit, failure is logged separately
                pass

        if final_status == ImageGroupStatus.CLEANED:
            # No queue service available: nothing will report back
            # asynchronously, so tombstone the job now (legacy/dev-only path).
            self._tombstone_job(ctx.job)

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
                event_type=(
                    "JOB_CLEANED"
                    if final_status == ImageGroupStatus.CLEANED
                    else "JOB_CLEANUP_SUBMITTED"
                ),
                correlation_id=correlation_id,
                client_id=client_id,
                timestamp=datetime.now(timezone.utc),
                details={
                    "image_group_id": ctx.image_group_id_str,
                    "cleanup_type": cleanup_type,
                    "reason": audit_reason,
                    "cleanup_playbook_submitted": cleanup_submitted,
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
            f"Cleanup {'completed' if final_status == ImageGroupStatus.CLEANED else 'submitted'}: "
            f"job_id={ctx.image_group.job_id}, "
            f"image_group_id={ctx.image_group_id_str}, "
            f"type={cleanup_type}, cleanup_playbook_submitted={cleanup_submitted}, "
            f"nfs_deleted={nfs_deleted}",
            job_id=str(ctx.image_group.job_id),
        )

        return CleanupResult(
            job_id=str(ctx.image_group.job_id),
            image_group_id=ctx.image_group_id_str,
            status=final_status.value,
            cleanup_type=cleanup_type,
            s3_objects_deleted=0,
            nfs_files_deleted=nfs_deleted,
            cleaned_at=cleaned_at,
        )

    def _cancel_non_terminal_stages(self, job_id) -> None:
        """Best-effort: cancel any non-terminal stages for audit cleanliness."""
        try:
            stages = self._stage_repo.find_all_by_job(job_id)
        except Exception:  # pylint: disable=broad-except
            self._rollback_image_group_session()
            return

        for stage in stages:
            if stage.stage_state.is_terminal():
                continue
            try:
                stage.cancel()
                self._stage_repo.save(stage)
            except Exception:  # pylint: disable=broad-except
                # Never block cleanup on a stage save failure.
                self._rollback_image_group_session()

    def _rollback_image_group_session(self) -> None:
        """Best-effort session rollback after a non-fatal error."""
        if hasattr(self._image_group_repo, "session"):
            try:
                self._image_group_repo.session.rollback()
            except Exception:  # pylint: disable=broad-except
                # nosec B110 - Best-effort rollback, failure is acceptable
                pass

    def _tombstone_job(self, job) -> None:
        """Best-effort job tombstoning (ignored if already tombstoned)."""
        try:
            job.tombstone()
            self._job_repo.save(job)
        except Exception:  # pylint: disable=broad-except
            # nosec B110 - Best-effort tombstoning, failure is acceptable
            pass

    def _submit_cleanup_playbook(
        self, ctx: _CleanupContext, correlation_id: str
    ) -> bool:
        """Submit image_build_manager.yml --tags cleanup_images to NFS queue.

        The playbook is responsible for deleting S3 images matching the
        image-group identifier.  Submission is fire-and-forget: the API
        returns immediately and the playbook watcher handles execution.

        Returns:
            True if the cleanup request was submitted successfully,
            False if no queue service is available or submission failed.
        """
        if self._queue_service is None:
            log_secure_info(
                "warning",
                f"Cleanup playbook skipped: no queue service configured "
                f"for image_group={ctx.image_group_id_str}",
                job_id=str(ctx.image_group.job_id),
            )
            return False

        try:
            request = PlaybookRequest(
                job_id=str(ctx.image_group.job_id),
                stage_name="cleanup",
                playbook_path=PlaybookPath(CLEANUP_PLAYBOOK_NAME),
                extra_vars=ExtraVars(values={
                    "cleanup_image_pattern": ctx.image_group_id_str,
                    # Required so the playbook's interactive approval
                    # prompt (ansible.builtin.pause) is bypassed. The
                    # playbook watcher runs headlessly (no TTY), so without
                    # this the prompt always resolves to "not approved" and
                    # every S3/registry deletion task is silently skipped.
                    "skip_approval": "true",
                }),
                correlation_id=correlation_id,
                timeout=ExecutionTimeout(CLEANUP_TIMEOUT_MINUTES),
                submitted_at=_now_iso(),
                request_id=str(self._uuid_generator.generate()),
                tags=CLEANUP_PLAYBOOK_TAGS,
            )
            self._queue_service.submit_request(
                request=request,
                correlation_id=correlation_id,
            )
            log_secure_info(
                "info",
                f"Cleanup playbook submitted: image_group={ctx.image_group_id_str}, "
                f"cleanup_image_pattern={ctx.image_group_id_str}, "
                f"correlation_id={correlation_id}",
                job_id=str(ctx.image_group.job_id),
            )
            return True
        except Exception as exc:  # pylint: disable=broad-except
            log_secure_info(
                "warning",
                f"Cleanup playbook submission failed for "
                f"image_group={ctx.image_group_id_str}: {exc}",
                job_id=str(ctx.image_group.job_id),
            )
            return False

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
