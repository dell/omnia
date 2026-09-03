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

"""ParseCatalog use case implementation.

Reintroduced (Omnia 2.3+) in minimal, deliberate form.

With domain segregation, create-local-repository/build-image consume the
catalog directly and no longer go through a dedicated parse step. However,
that also removed the only place that used to catch a real violation: two
different jobs uploading a catalog with the same ``image_group_id``.
``image_groups.id`` has a DB-level UNIQUE constraint, but without this
stage the collision was only discovered *after* create-local-repository and
build-image had already run to completion for the second job (the INSERT
would fail deep inside ``ResultPoller._on_build_image_success`` and was
silently swallowed as a warning).

This stage now fails fast, before any playbook runs, by:
1. Loading the catalog already uploaded for this job during the "upload"
   stage (no separate file upload here -- avoids duplicating the upload
   path).
2. Extracting ``image_group_id`` from the catalog.
3. Checking it isn't already owned by another job's ImageGroup.
4. Persisting catalog metadata (image_group_id, roles, role_images) as an
   artifact for consumption by the build-image stage completion callback.
"""

import json
import uuid as uuid_module
from datetime import datetime, timezone
from typing import Optional, Tuple

from api.logging_utils import log_secure_info

from core.artifacts.entities import ArtifactRecord
from core.artifacts.interfaces import ArtifactMetadataRepository, ArtifactStore
from core.artifacts.value_objects import ArtifactKind, StoreHint
from core.catalog.exceptions import CatalogNotUploadedError, InvalidCatalogFormatError
from core.image_group.exceptions import DuplicateImageGroupError
from core.image_group.repositories import ImageGroupRepository
from core.image_group.value_objects import ImageGroupId
from core.jobs.entities import AuditEvent, Job, Stage
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    StageAlreadyCompletedError,
    TerminalStateViolationError,
)
from core.jobs.repositories import (
    AuditEventRepository,
    JobRepository,
    StageRepository,
    UUIDGenerator,
)
from core.jobs.services import JobStateHelper
from core.jobs.value_objects import JobState, StageName, StageState, StageType

from orchestrator.catalog.commands.parse_catalog import ParseCatalogCommand
from orchestrator.catalog.dtos import ParseCatalogResult


class ParseCatalogUseCase:
    """Use case for executing the (reintroduced, minimal) parse-catalog stage.

    Orchestrates:
    1. Stage guard validation (job exists, stage PENDING/retryable)
    2. Loading the catalog uploaded during the "upload" stage
    3. ImageGroup ID extraction and cross-job uniqueness check
    4. Stage state transitions and audit events
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        job_repo: JobRepository,
        stage_repo: StageRepository,
        audit_repo: AuditEventRepository,
        artifact_store: ArtifactStore,
        artifact_metadata_repo: ArtifactMetadataRepository,
        uuid_generator: UUIDGenerator,
        image_group_repo: Optional[ImageGroupRepository] = None,
    ) -> None:
        self._job_repo = job_repo
        self._stage_repo = stage_repo
        self._audit_repo = audit_repo
        self._artifact_store = artifact_store
        self._artifact_metadata_repo = artifact_metadata_repo
        self._uuid_generator = uuid_generator
        self._image_group_repo = image_group_repo

    def execute(self, command: ParseCatalogCommand) -> ParseCatalogResult:
        """Execute the parse-catalog stage.

        Args:
            command: ParseCatalogCommand with job_id, client_id, correlation_id.

        Returns:
            ParseCatalogResult with stage outcome and the extracted image_group_id.

        Raises:
            JobNotFoundError: If job does not exist.
            TerminalStateViolationError: If job is in a terminal state.
            StageAlreadyCompletedError: If stage already completed.
            InvalidStateTransitionError: If stage is not in a runnable state.
            CatalogNotUploadedError: If no catalog was uploaded for this job.
            InvalidCatalogFormatError: If the catalog is missing image_group_id.
            DuplicateImageGroupError: If ImageGroup already exists (409).
        """
        job, stage = self._load_and_guard_stage(command)

        try:
            self._mark_stage_started(job, stage, command)

            catalog_data = self._load_uploaded_catalog(command.job_id)
            image_group_id = self._extract_image_group_id(catalog_data)
            self._check_image_group_uniqueness(image_group_id)
            
            # Persist catalog metadata for build-image stage
            catalog_metadata = self._extract_catalog_metadata(catalog_data)
            self._persist_catalog_metadata(command.job_id, catalog_metadata)

            self._mark_stage_completed(stage, command)
            return self._build_success_result(command, image_group_id)
        except Exception as exc:
            self._mark_stage_failed(stage, command, exc)
            raise

    # ------------------------------------------------------------------
    # Stage guards
    # ------------------------------------------------------------------

    def _load_and_guard_stage(
        self, command: ParseCatalogCommand
    ) -> Tuple[Job, Stage]:
        """Load job and parse-catalog stage, enforce preconditions."""
        job = self._job_repo.find_by_id(command.job_id)
        if job is None or job.client_id != command.client_id:
            raise JobNotFoundError(
                job_id=str(command.job_id),
                correlation_id=str(command.correlation_id),
            )

        if job.job_state.is_terminal():
            raise TerminalStateViolationError(
                entity_type="Job",
                entity_id=str(command.job_id),
                state=job.job_state.value,
                correlation_id=str(command.correlation_id),
            )

        stage_name = StageName(StageType.PARSE_CATALOG.value)
        stage = self._stage_repo.find_by_job_and_name(command.job_id, stage_name)
        if stage is None:
            raise JobNotFoundError(
                job_id=str(command.job_id),
                correlation_id=str(command.correlation_id),
            )

        # Reset FAILED stages for retry.
        if stage.stage_state == StageState.FAILED:
            prev_state = stage.stage_state.value
            stage.reset()
            self._stage_repo.save(stage)
            log_secure_info(
                "info",
                f"Resetting parse-catalog stage from {prev_state} to PENDING "
                f"for retry (attempt {stage.attempt}): job_id={command.job_id}",
                job_id=str(command.job_id),
            )
            JobStateHelper.handle_job_resume(
                job_repo=self._job_repo,
                audit_repo=self._audit_repo,
                uuid_generator=self._uuid_generator,
                job_id=command.job_id,
                stage_name=StageType.PARSE_CATALOG.value,
                correlation_id=str(command.correlation_id),
                client_id=str(command.client_id),
            )

        if stage.stage_state == StageState.COMPLETED:
            raise StageAlreadyCompletedError(
                job_id=str(command.job_id),
                stage_name=StageType.PARSE_CATALOG.value,
                correlation_id=str(command.correlation_id),
            )

        if stage.stage_state != StageState.PENDING:
            raise InvalidStateTransitionError(
                entity_type="Stage",
                entity_id=f"{command.job_id}/{StageType.PARSE_CATALOG.value}",
                from_state=stage.stage_state.value,
                to_state="IN_PROGRESS",
                correlation_id=str(command.correlation_id),
            )

        return job, stage

    # ------------------------------------------------------------------
    # Catalog loading and violation check
    # ------------------------------------------------------------------

    def _load_uploaded_catalog(self, job_id) -> dict:
        """Load the catalog JSON uploaded during the "upload" stage.

        Args:
            job_id: Job identifier.

        Returns:
            Parsed catalog dict.

        Raises:
            CatalogNotUploadedError: If no catalog artifact is found for
                this job, or it cannot be parsed as JSON.
        """
        catalog_record = None
        try:
            all_records = self._artifact_metadata_repo.list_by_job_id(job_id)
        except Exception as exc:  # pylint: disable=broad-except
            raise CatalogNotUploadedError(
                f"Failed to look up uploaded catalog for job {job_id}: {exc}"
            ) from exc

        for record in all_records or []:
            label_lower = record.label.lower()
            if (
                record.stage_name == StageName("upload")
                and "catalog" in label_lower
                and label_lower.endswith(".json")
            ):
                catalog_record = record
                break

        if catalog_record is None:
            raise CatalogNotUploadedError(
                f"No catalog uploaded for job {job_id}. Upload "
                "catalog_rhel.json via PUT /jobs/{job_id}/upload before "
                "triggering parse-catalog."
            )

        try:
            raw = self._artifact_store.retrieve(
                catalog_record.artifact_ref.key, ArtifactKind.FILE
            )
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise CatalogNotUploadedError(
                f"Uploaded catalog for job {job_id} is not valid JSON: {exc}"
            ) from exc

    def _extract_image_group_id(self, catalog_data: dict) -> ImageGroupId:
        """Extract ImageGroupID from the Catalog.Identifier field.

        Supports both PascalCase (``Catalog``/``Identifier``) and lowercase
        (``catalog``/``identifier``) keys for consistency with how
        ``ResultPoller`` reads the same catalog elsewhere in the pipeline.

        Raises:
            InvalidCatalogFormatError: If the ``Catalog`` key is missing or
                ``Identifier`` is absent/invalid.
        """
        catalog_obj = catalog_data.get("Catalog", catalog_data.get("catalog"))
        if not catalog_obj or not isinstance(catalog_obj, dict):
            raise InvalidCatalogFormatError(
                "Catalog JSON missing required 'Catalog' top-level key"
            )

        raw_id = catalog_obj.get("Identifier", catalog_obj.get("identifier", ""))
        try:
            return ImageGroupId(raw_id)
        except ValueError as exc:
            raise InvalidCatalogFormatError(
                f"Catalog 'Identifier' is invalid: {exc}"
            ) from exc

    def _check_image_group_uniqueness(self, image_group_id: ImageGroupId) -> None:
        """Check that no ImageGroup with this ID already exists.

        This is the core violation check this stage exists for: without
        it, two jobs uploading catalogs with the same image_group_id would
        both proceed through create-local-repository and build-image
        before the collision was ever detected (see module docstring).

        Raises:
            DuplicateImageGroupError: If an ImageGroup with this ID
                already exists in the database. Maps to HTTP 409 Conflict.
        """
        if self._image_group_repo is None:
            log_secure_info(
                "debug",
                "ImageGroup repo not available; skipping uniqueness check",
            )
            return

        if self._image_group_repo.exists(image_group_id):
            raise DuplicateImageGroupError(str(image_group_id))

    def _extract_catalog_metadata(self, catalog_data: dict) -> dict:
        """Extract image_group_id, roles, and role_images from catalog.

        This metadata is persisted as an artifact and consumed by the
        build-image stage completion callback to create ImageGroup/Image records.

        Args:
            catalog_data: Parsed catalog JSON.

        Returns:
            Dict with image_group_id, roles, role_images, name, version, parsed_at.
        """
        cat = catalog_data.get("Catalog", catalog_data.get("catalog"))
        if not cat or not isinstance(cat, dict):
            raise InvalidCatalogFormatError(
                "Catalog JSON missing required 'Catalog' top-level key"
            )

        raw_id = cat.get("Identifier", cat.get("identifier", ""))
        if not raw_id:
            raise InvalidCatalogFormatError(
                "Catalog 'Identifier' is missing or empty"
            )

        layers = cat.get("FunctionalLayer", cat.get("functionallayer", []))

        roles = []
        role_images = {}
        for layer in layers:
            if not isinstance(layer, dict):
                continue
            name = layer.get("Name", layer.get("name", ""))
            if name:
                roles.append(name)
                role_images[name] = f"{name}.img"
        roles.sort()

        # Add synthetic _first variant if base kube control plane exists
        base_kube = "service_kube_control_plane_x86_64"
        first_kube = "service_kube_control_plane_first_x86_64"
        if base_kube in roles and first_kube not in roles:
            roles.append(first_kube)
            role_images[first_kube] = f"{first_kube}.img"
            roles.sort()

        return {
            "image_group_id": raw_id,
            "roles": roles,
            "role_images": role_images,
            "name": cat.get("Name", cat.get("name", "")),
            "version": cat.get("Version", cat.get("version", "")),
            "parsed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _persist_catalog_metadata(
        self, job_id, catalog_metadata: dict
    ) -> None:
        """Store catalog metadata as an artifact for build-image.

        Creates a ``catalog-metadata`` artifact under the ``parse-catalog``
        stage so that the build-image completion callback can find it later.

        Args:
            job_id: Job identifier.
            catalog_metadata: Dict with image_group_id, roles, role_images, etc.
        """
        content = json.dumps(catalog_metadata, indent=2).encode("utf-8")

        hint = StoreHint(
            namespace="catalog",
            label="catalog-metadata",
            tags={"job_id": str(job_id)},
        )

        metadata_ref = self._artifact_store.store(
            hint=hint,
            kind=ArtifactKind.FILE,
            content=content,
            content_type="application/json",
        )

        record = ArtifactRecord(
            id=str(uuid_module.uuid4()),
            job_id=job_id,
            stage_name=StageName("parse-catalog"),
            label="catalog-metadata",
            artifact_ref=metadata_ref,
            kind=ArtifactKind.FILE,
            content_type="application/json",
            tags={"job_id": str(job_id)},
        )
        self._artifact_metadata_repo.save(record)

        log_secure_info(
            "info",
            f"Persisted catalog metadata for job={job_id}: "
            f"image_group_id={catalog_metadata.get('image_group_id')}, "
            f"roles={catalog_metadata.get('roles')}",
            job_id=str(job_id),
        )

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _mark_stage_started(
        self, job: Job, stage: Stage, command: ParseCatalogCommand
    ) -> None:
        """Transition stage to IN_PROGRESS and job to IN_PROGRESS if needed."""
        stage.start()
        self._stage_repo.save(stage)

        if job.job_state == JobState.CREATED:
            job.start()
            self._job_repo.save(job)

        self._emit_audit_event(command, "STAGE_STARTED", {"stage_name": "parse-catalog"})

    def _mark_stage_completed(self, stage: Stage, command: ParseCatalogCommand) -> None:
        """Transition stage to COMPLETED."""
        stage.complete()
        self._stage_repo.save(stage)
        self._emit_audit_event(command, "STAGE_COMPLETED", {"stage_name": "parse-catalog"})

    def _mark_stage_failed(
        self, stage: Stage, command: ParseCatalogCommand, error: Exception
    ) -> None:
        """Transition stage to FAILED with error details."""
        error_code = type(error).__name__
        error_summary = str(error) or "Parse-catalog failed"
        stage.fail(error_code=error_code, error_summary=error_summary)
        self._stage_repo.save(stage)
        self._emit_audit_event(
            command,
            "STAGE_FAILED",
            {
                "stage_name": "parse-catalog",
                "error_code": error_code,
                "error_summary": error_summary,
            },
        )

        JobStateHelper.handle_stage_failure(
            job_repo=self._job_repo,
            audit_repo=self._audit_repo,
            uuid_generator=self._uuid_generator,
            job_id=command.job_id,
            stage_name=StageType.PARSE_CATALOG.value,
            error_code=error_code,
            error_summary=error_summary,
            correlation_id=str(command.correlation_id),
            client_id=str(command.client_id),
        )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def _emit_audit_event(
        self, command: ParseCatalogCommand, event_type: str, details: dict
    ) -> None:
        """Emit an audit event."""
        event = AuditEvent(
            event_id=str(self._uuid_generator.generate()),
            job_id=command.job_id,
            event_type=event_type,
            correlation_id=command.correlation_id,
            client_id=command.client_id,
            timestamp=datetime.now(timezone.utc),
            details=details,
        )
        self._audit_repo.save(event)

    # ------------------------------------------------------------------
    # Result building
    # ------------------------------------------------------------------

    def _build_success_result(
        self, command: ParseCatalogCommand, image_group_id: ImageGroupId
    ) -> ParseCatalogResult:
        """Build the success result DTO."""
        return ParseCatalogResult(
            job_id=str(command.job_id),
            stage_state="COMPLETED",
            message="Catalog parsed successfully; image_group_id is unique",
            image_group_id=str(image_group_id),
            completed_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )
