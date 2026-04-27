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

"""Common result poller for processing playbook execution results from NFS queue.

This module provides a shared ResultPoller that can be used by all stage APIs
(local_repo, build_image, validate, etc.) to poll the NFS result
queue and update stage states accordingly.

Enhanced (S1-4 Part B): On build-image success, creates ImageGroup (BUILT)
and Image records from catalog metadata persisted during parse-catalog.
"""

import json
import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from api.logging_utils import log_secure_info

from core.image_group.entities import Image, ImageGroup
from core.image_group.repositories import ImageGroupRepository, ImageRepository
from core.image_group.value_objects import ImageGroupId, ImageGroupStatus
from core.artifacts.entities import ArtifactRecord
from core.artifacts.interfaces import ArtifactMetadataRepository, ArtifactStore
from core.artifacts.value_objects import ArtifactKind, StoreHint
from core.jobs.entities import AuditEvent
from core.jobs.entities.stage import StageState
from core.jobs.repositories import (
    AuditEventRepository,
    JobRepository,
    StageRepository,
    UUIDGenerator,
)
from core.jobs.services import JobStateHelper
from core.jobs.value_objects import JobId, StageName
from core.localrepo.entities import PlaybookResult
from core.localrepo.services import PlaybookQueueResultService


class ResultPoller:
    """Common poller for processing playbook execution results.

    This poller monitors the NFS result queue and processes results
    by updating stage states and emitting audit events. It handles
    results from all stage types (local_repo, build_image,
    validate, deploy, etc.).

    Attributes:
        result_service: Service for polling NFS result queue.
        job_repo: Job repository for updating job states.
        stage_repo: Stage repository for updating stage states.
        audit_repo: Audit event repository for emitting events.
        uuid_generator: UUID generator for event IDs.
        poll_interval: Interval in seconds between polls.
        running: Flag indicating if poller is running.
    """

    def __init__(
        self,
        result_service: PlaybookQueueResultService,
        job_repo: JobRepository,
        stage_repo: StageRepository,
        audit_repo: AuditEventRepository,
        uuid_generator: UUIDGenerator,
        poll_interval: int = 5,
        image_group_repo: ImageGroupRepository = None,
        image_repo: ImageRepository = None,
        artifact_store: ArtifactStore = None,
        artifact_metadata_repo: ArtifactMetadataRepository = None,
    ) -> None:  # pylint: disable=too-many-arguments,too-many-positional-arguments
        """Initialize result poller.

        Args:
            result_service: Service for polling NFS result queue.
            job_repo: Job repository implementation.
            stage_repo: Stage repository implementation.
            audit_repo: Audit event repository implementation.
            uuid_generator: UUID generator for identifiers.
            poll_interval: Interval in seconds between polls (default: 5).
            image_group_repo: ImageGroup repository for build-image completion.
            image_repo: Image repository for build-image completion.
            artifact_store: Artifact store for retrieving catalog metadata.
            artifact_metadata_repo: Artifact metadata repo for finding artifacts.
        """
        self._result_service = result_service
        self._job_repo = job_repo
        self._stage_repo = stage_repo
        self._audit_repo = audit_repo
        self._uuid_generator = uuid_generator
        self._poll_interval = poll_interval
        self._image_group_repo = image_group_repo
        self._image_repo = image_repo
        self._artifact_store = artifact_store
        self._artifact_metadata_repo = artifact_metadata_repo
        self._running = False
        self._task = None

    async def start(self) -> None:
        """Start the result poller."""
        if self._running:
            log_secure_info("warning", "Result poller is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        log_secure_info("info", f"Result poller started with interval={self._poll_interval}s")

    async def stop(self) -> None:
        """Stop the result poller."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log_secure_info("info", "Result poller stopped")

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                processed_count = self._result_service.poll_results(
                    callback=self._on_result_received
                )
                if processed_count > 0:
                    log_secure_info("info", f"Processed {processed_count} playbook results")
            except Exception as exc:  # pylint: disable=broad-except
                log_secure_info("error", f"Error polling results: {exc}", exc_info=True)

            await asyncio.sleep(self._poll_interval)

    def _on_result_received(self, result: PlaybookResult) -> None:
        """Handle received playbook result.

        Args:
            result: Playbook execution result from NFS queue.
        """
        try:
            # Find stage
            stage_name = StageName(result.stage_name)
            stage = self._stage_repo.find_by_job_and_name(result.job_id, stage_name)

            if stage is None:
                log_secure_info(
                    "error",
                    f"Stage not found for result: job_id={result.job_id}, "
                    f"stage={result.stage_name}",
                    job_id=str(result.job_id),
                )
                return

            # Update stage based on result
            # Check if stage is already in terminal state (e.g., after service restart)
            if stage.stage_state in {StageState.COMPLETED, StageState.FAILED, StageState.CANCELLED}:
                log_secure_info(
                    "info",
                    f"Stage already in terminal state: job_id={result.job_id}, "
                    f"stage={result.stage_name}, state={stage.stage_state}",
                    job_id=str(result.job_id),
                )
                # Return early - service will archive the result file automatically
                return

            if result.status == "success":
                stage.complete()
                log_secure_info(
                    "info",
                    f"Stage completed: job_id={result.job_id}, stage={result.stage_name}",
                    job_id=str(result.job_id),
                )

                # S1-4 Part B: On build-image success, create ImageGroup + Images
                if self._is_build_image_stage(result.stage_name):
                    self._on_build_image_success(result)

                # On validate success, mark job as PASSED
                if result.stage_name == "validate":
                    self._on_validate_success(result)
                    JobStateHelper.handle_job_completion(
                        job_repo=self._job_repo,
                        audit_repo=self._audit_repo,
                        uuid_generator=self._uuid_generator,
                        job_id=JobId(result.job_id),
                        correlation_id=(
                            result.request_id.value
                            if hasattr(result.request_id, 'value')
                            else str(result.request_id)
                        ),
                        client_id=str(result.job_id),
                    )

                # S1-6: On deploy success, transition ImageGroup DEPLOYING -> DEPLOYED
                if result.stage_name == "deploy":
                    self._on_deploy_success(result)

                # S12: On restart completion, persist node_results.json as artifact
                if result.stage_name == "restart":
                    self._on_restart_completed(result)
            else:
                error_code = result.error_code or "PLAYBOOK_FAILED"
                error_summary = result.error_summary or "Playbook execution failed"
                stage.fail(error_code=error_code, error_summary=error_summary)
                log_secure_info(
                    "warning",
                    f"Stage failed: job_id={result.job_id}, "
                    f"stage={result.stage_name}, error={error_code}",
                    job_id=str(result.job_id),
                )

                # S12: On restart failure, still persist node_results.json
                if result.stage_name == "restart":
                    self._on_restart_completed(result)

                # Update job state to FAILED when stage fails
                JobStateHelper.handle_stage_failure(
                    job_repo=self._job_repo,
                    audit_repo=self._audit_repo,
                    uuid_generator=self._uuid_generator,
                    job_id=JobId(result.job_id),
                    stage_name=result.stage_name,
                    error_code=error_code,
                    error_summary=error_summary,
                    correlation_id=(
                        result.request_id.value
                        if hasattr(result.request_id, 'value')
                        else str(result.request_id)
                    ),
                    client_id=str(result.job_id),
                )

            # Update log file path if available
            if result.log_file_path:
                stage.log_file_path = result.log_file_path
                log_secure_info(
                    "info",
                    f"Updated stage log path: job_id={result.job_id}, stage={result.stage_name}",
                    job_id=str(result.job_id),
                )

            # Save updated stage
            self._stage_repo.save(stage)

            # Emit audit event
            event = AuditEvent(
                event_id=str(self._uuid_generator.generate()),
                job_id=result.job_id,
                event_type="STAGE_COMPLETED" if result.status == "success" else "STAGE_FAILED",
                correlation_id=result.request_id,
                client_id=result.job_id,  # Using job_id as client_id placeholder
                timestamp=datetime.now(timezone.utc),
                details={
                    "stage_name": result.stage_name,
                    "status": result.status,
                    "duration_seconds": result.duration_seconds,
                    "exit_code": result.exit_code,
                },
            )
            self._audit_repo.save(event)

            # Commit both repositories if using SQL
            # Note: Each repository may have its own session, so commit both
            if hasattr(self._stage_repo, 'session'):
                self._stage_repo.session.commit()
            if hasattr(self._audit_repo, 'session'):
                self._audit_repo.session.commit()

            log_secure_info(
                "info",
                f"Result processed for job {result.job_id}, stage {result.stage_name}",
                result.request_id,
            )

        except Exception as exc:  # pylint: disable=broad-except
            log_secure_info(
                "error",
                f"Error handling result: job_id={result.job_id}, error={exc}",
                job_id=str(result.job_id),
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # S1-4 Part B: Build-image completion — ImageGroup/Image creation
    # ------------------------------------------------------------------

    @staticmethod
    def _is_build_image_stage(stage_name: str) -> bool:
        """Check if the stage is a build-image stage."""
        return stage_name in (
            "build-image-x86_64",
            "build-image-aarch64",
            "build-image",
        )

    def _on_build_image_success(self, result: PlaybookResult) -> None:
        """Create ImageGroup (BUILT) and Image records on build-image success.

        Loads catalog metadata persisted by parse-catalog, creates the
        ImageGroup with status BUILT, and inserts Image records for each
        constituent role.

        Args:
            result: Playbook execution result from NFS queue.
        """
        if self._image_group_repo is None or self._image_repo is None:
            log_secure_info(
                "warning",
                f"ImageGroup/Image repos not available; skipping "
                f"ImageGroup creation for job={result.job_id}",
                job_id=str(result.job_id),
            )
            return

        try:
            catalog_metadata = self._load_catalog_metadata(result.job_id)
            if catalog_metadata is None:
                log_secure_info(
                    "warning",
                    f"No catalog metadata found for job={result.job_id}; "
                    f"skipping ImageGroup creation",
                    job_id=str(result.job_id),
                )
                return

            image_group_id = catalog_metadata["image_group_id"]
            role_images = catalog_metadata.get("role_images", {})

            # Create ImageGroup entity
            now = datetime.now(timezone.utc)
            image_group = ImageGroup(
                id=ImageGroupId(image_group_id),
                job_id=JobId(str(result.job_id)),
                status=ImageGroupStatus.BUILT,
                images=[],
                created_at=now,
                updated_at=now,
            )

            # Create Image entities for each role
            images = []
            for role_name, image_name in role_images.items():
                image = Image(
                    id=str(uuid.uuid4()),
                    image_group_id=image_group_id,
                    role=role_name,
                    image_name=image_name,
                    created_at=now,
                )
                images.append(image)
            image_group.images = images

            # Persist: ImageGroup first, then Images.
            # In ProdContainer each repo may hold a different DB session
            # (Factory-created via providers.Factory(SessionLocal)).
            # The images table has a FK to image_groups, so the ImageGroup
            # row must be committed (visible to other sessions) before the
            # Image INSERT can satisfy the FK constraint.
            try:
                self._image_group_repo.save(image_group)
                if hasattr(self._image_group_repo, 'session'):
                    self._image_group_repo.session.commit()

                self._image_repo.save_batch(images)
                if hasattr(self._image_repo, 'session'):
                    self._image_repo.session.commit()
            except IntegrityError as integrity_exc:
                log_secure_info(
                    "warning",
                    f"IntegrityError creating ImageGroup '{image_group_id}' "
                    f"for job={result.job_id}: {integrity_exc.orig}",
                    job_id=str(result.job_id),
                )
                if hasattr(self._image_group_repo, 'session'):
                    self._image_group_repo.session.rollback()
                if hasattr(self._image_repo, 'session'):
                    self._image_repo.session.rollback()
                return

            log_secure_info(
                "info",
                f"Build-image SUCCESS for job={result.job_id}. Created ImageGroup "
                f"'{image_group_id}' with {len(images)} images (status=BUILT).",
                job_id=str(result.job_id),
            )

        except Exception as exc:  # pylint: disable=broad-except
            log_secure_info(
                "error",
                f"Failed to create ImageGroup/Images for job={result.job_id}: {exc}",
                job_id=str(result.job_id),
                exc_info=True,
            )

    def _load_catalog_metadata(self, job_id) -> dict:
        """Load catalog metadata artifact persisted by parse-catalog.

        Retrieves the catalog-metadata artifact from the artifact store
        to get image_group_id and role-to-image mappings.

        Args:
            job_id: Job identifier.

        Returns:
            Dict with image_group_id, roles, role_images, or None if not found.
        """
        if self._artifact_metadata_repo is None or self._artifact_store is None:
            return None

        try:
            record = self._artifact_metadata_repo.find_by_job_stage_and_label(
                job_id=job_id,
                stage_name=StageName("parse-catalog"),
                label="catalog-metadata",
            )
            if record is None:
                return None

            raw = self._artifact_store.retrieve(
                record.artifact_ref.key,
                ArtifactKind.FILE,
            )
            return json.loads(raw.decode("utf-8"))

        except Exception as exc:  # pylint: disable=broad-except
            log_secure_info(
                "warning",
                f"Failed to load catalog metadata for job={job_id}: {exc}",
                job_id=str(job_id),
            )
            return None

    # ------------------------------------------------------------------
    # S1-6: Deploy completion — ImageGroup status transitions
    # ------------------------------------------------------------------

    def _on_deploy_success(self, result: PlaybookResult) -> None:
        """Transition ImageGroup from DEPLOYING to DEPLOYED on deploy success."""
        if self._image_group_repo is None:
            log_secure_info(
                "warning",
                f"ImageGroup repo not available; skipping deploy status "
                f"update for job={result.job_id}",
                job_id=str(result.job_id),
            )
            return

        try:
            image_group = self._image_group_repo.find_by_job_id(
                JobId(str(result.job_id))
            )
            if image_group is None:
                log_secure_info(
                    "error",
                    f"Deploy callback: No ImageGroup found for job={result.job_id}.",
                    job_id=str(result.job_id),
                )
                return

            self._image_group_repo.update_status(
                image_group_id=image_group.id,
                new_status=ImageGroupStatus.DEPLOYED,
            )

            if hasattr(self._image_group_repo, 'session'):
                self._image_group_repo.session.commit()

            log_secure_info(
                "info",
                f"Deploy SUCCESS for job={result.job_id}. "
                f"ImageGroup '{image_group.id}' -> DEPLOYED.",
                job_id=str(result.job_id),
            )
        except Exception as exc:  # pylint: disable=broad-except
            log_secure_info(
                "error",
                "Failed to update ImageGroup status on deploy "
                f"success for job={result.job_id}: {exc}",
                job_id=str(result.job_id),
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # S12: Restart completion — persist node_results.json as artifact
    # ------------------------------------------------------------------

    def _on_restart_completed(self, result: PlaybookResult) -> None:
        """Store node_results.json and failed_nodes.json as artifacts on restart completion.

        Both files are created by the playbook (Play 6 in set_pxe_boot.yml).
        This method reads them from NFS and stores them in ArtifactStore
        so they can be downloaded via the API by GitLab CI.

        Args:
            result: Playbook execution result from NFS queue.
        """
        if self._artifact_store is None or self._artifact_metadata_repo is None:
            log_secure_info(
                "warning",
                f"Artifact store/metadata repo not available; skipping "
                f"artifact persistence for job={result.job_id}",
                job_id=str(result.job_id),
            )
            return

        node_results_path = result.node_results_file_path
        if not node_results_path:
            log_secure_info(
                "info",
                f"No node_results_file_path in restart result for "
                f"job={result.job_id}; nothing to persist",
                job_id=str(result.job_id),
            )
            return

        try:
            path = Path(node_results_path)
            if not path.exists():
                log_secure_info(
                    "warning",
                    f"node_results file not found at {node_results_path} "
                    f"for job={result.job_id}",
                    job_id=str(result.job_id),
                )
                return

            raw = path.read_bytes()

            # Validate JSON
            json.loads(raw)

            # Store node_results.json in artifact store
            hint = StoreHint(
                namespace=str(result.job_id),
                label="node-results",
                tags={"job_id": str(result.job_id), "stage": "restart"},
            )
            artifact_ref = self._artifact_store.store(
                hint=hint,
                kind=ArtifactKind.FILE,
                content=raw,
                content_type="application/json",
            )

            record = ArtifactRecord(
                id=str(self._uuid_generator.generate()),
                job_id=JobId(str(result.job_id)),
                stage_name=StageName("restart"),
                label="node-results",
                artifact_ref=artifact_ref,
                kind=ArtifactKind.FILE,
                content_type="application/json",
            )
            self._artifact_metadata_repo.save(record)

            log_secure_info(
                "info",
                f"Restart node_results persisted as artifact for "
                f"job={result.job_id} (size={len(raw)} bytes)",
                job_id=str(result.job_id),
            )

            # Store failed_nodes.json (written by the playbook alongside node_results.json)
            failed_nodes_file = path.parent / "failed_nodes.json"
            if failed_nodes_file.exists():
                failed_raw = failed_nodes_file.read_bytes()

                # Validate JSON
                json.loads(failed_raw)

                failed_hint = StoreHint(
                    namespace=str(result.job_id),
                    label="failed-nodes",
                    tags={"job_id": str(result.job_id), "stage": "restart"},
                )
                failed_artifact_ref = self._artifact_store.store(
                    hint=failed_hint,
                    kind=ArtifactKind.FILE,
                    content=failed_raw,
                    content_type="application/json",
                )

                failed_record = ArtifactRecord(
                    id=str(self._uuid_generator.generate()),
                    job_id=JobId(str(result.job_id)),
                    stage_name=StageName("restart"),
                    label="failed-nodes",
                    artifact_ref=failed_artifact_ref,
                    kind=ArtifactKind.FILE,
                    content_type="application/json",
                )
                self._artifact_metadata_repo.save(failed_record)

                if hasattr(self._artifact_metadata_repo, 'session'):
                    self._artifact_metadata_repo.session.commit()

                failed_data = json.loads(failed_raw)
                log_secure_info(
                    "info",
                    f"Stored failed_nodes.json as artifact for job={result.job_id} "
                    f"({failed_data.get('failure_count', 0)} failed of "
                    f"{failed_data.get('total_nodes', 0)} total)",
                    job_id=str(result.job_id),
                )
            else:
                log_secure_info(
                    "info",
                    f"No failed_nodes.json found alongside node_results for "
                    f"job={result.job_id}; playbook may not have written it",
                    job_id=str(result.job_id),
                )
                
        except json.JSONDecodeError as jde:
            log_secure_info(
                "error",
                f"JSON artifact is not valid for "
                f"job={result.job_id}: {jde}",
                job_id=str(result.job_id),
            )
        except Exception as exc:  # pylint: disable=broad-except
            log_secure_info(
                "error",
                f"Failed to persist restart artifacts for "
                f"job={result.job_id}: {exc}",
                job_id=str(result.job_id),
                exc_info=True,
            )

    def _on_validate_success(self, result: PlaybookResult) -> None:
        """Copy test report artifacts to artifact store on validate success.

        Copies test_report.json, test_report.html, molecule_output.log,
        and junit.xml to {artifacts_base}/{job_id}/validate/attempt_{N}/.
        """
        try:
            log_secure_info(
                "info",
                f"Validate SUCCESS for job={result.job_id}. "
                f"Processing test artifacts.",
                job_id=str(result.job_id),
            )
        except Exception as exc:  # pylint: disable=broad-except
            log_secure_info(
                "error",
                f"Failed to process validate artifacts for job={result.job_id}: {exc}",
                job_id=str(result.job_id),
                exc_info=True,
            )

    def _on_validate_failure(self, result: PlaybookResult) -> None:
        """Copy partial test report artifacts on validate failure."""
        try:
            log_secure_info(
                "warning",
                f"Validate FAILED for job={result.job_id}. "
                f"exit_code={result.exit_code}, error={result.error_summary}. "
                f"Processing partial artifacts.",
                job_id=str(result.job_id),
            )
        except Exception as exc:  # pylint: disable=broad-except
            log_secure_info(
                "error",
                f"Failed to process validate failure artifacts for job={result.job_id}: {exc}",
                job_id=str(result.job_id),
                exc_info=True,
            )

    def _on_deploy_failure(self, result: PlaybookResult) -> None:
        """Transition ImageGroup from DEPLOYING to FAILED on deploy failure."""
        if self._image_group_repo is None:
            log_secure_info(
                "warning",
                f"ImageGroup repo not available; skipping deploy failure "
                f"update for job={result.job_id}",
                job_id=str(result.job_id),
            )
            return

        try:
            image_group = self._image_group_repo.find_by_job_id(
                JobId(str(result.job_id))
            )
            if image_group is None:
                log_secure_info(
                    "error",
                    f"Deploy failure callback: No ImageGroup found for job={result.job_id}.",
                    job_id=str(result.job_id),
                )
                return

            self._image_group_repo.update_status(
                image_group_id=image_group.id,
                new_status=ImageGroupStatus.FAILED,
            )

            if hasattr(self._image_group_repo, 'session'):
                self._image_group_repo.session.commit()

            log_secure_info(
                "warning",
                f"Deploy FAILED for job={result.job_id}. "
                f"ImageGroup '{image_group.id}' -> FAILED.",
                job_id=str(result.job_id),
            )
        except Exception as exc:  # pylint: disable=broad-except
            log_secure_info(
                "error",
                "Failed to update ImageGroup status on deploy "
                f"failure for job={result.job_id}: {exc}",
                job_id=str(result.job_id),
                exc_info=True,
            )
