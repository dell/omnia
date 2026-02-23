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

# pylint: disable=too-many-arguments,too-many-positional-arguments

"""ParseCatalog use case implementation."""

import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

import hashlib

from jsonschema import ValidationError

from core.artifacts.entities import ArtifactRecord
from core.artifacts.exceptions import ArtifactAlreadyExistsError
from core.artifacts.interfaces import ArtifactMetadataRepository, ArtifactStore
from core.artifacts.value_objects import ArtifactDigest, ArtifactKind, ArtifactRef, StoreHint
from core.catalog.exceptions import (
    CatalogSchemaValidationError,
    InvalidFileFormatError,
    InvalidJSONError,
)
from core.catalog.generator import generate_root_json_from_catalog
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
from core.jobs.value_objects import (
    ClientId,
    StageName,
    StageState,
    StageType,
    JobState,
)

from orchestrator.catalog.commands.parse_catalog import ParseCatalogCommand
from orchestrator.catalog.dtos import ParseCatalogResult

logger = logging.getLogger(__name__)


class ParseCatalogUseCase:  # pylint: disable=too-few-public-methods
    """Use case for executing the parse-catalog stage.

    Orchestrates:
    1. Stage guard validation (job exists, stage PENDING)
    2. Catalog validation (format, JSON, schema)
    3. Root JSON generation via existing generator
    4. Artifact storage (catalog file + root JSONs archive)
    5. Artifact metadata persistence
    6. Stage state transitions and audit events
    """

    def __init__(
        self,
        job_repo: JobRepository,
        stage_repo: StageRepository,
        audit_repo: AuditEventRepository,
        artifact_store: ArtifactStore,
        artifact_metadata_repo: ArtifactMetadataRepository,
        uuid_generator: UUIDGenerator,
    ) -> None:
        self._job_repo = job_repo
        self._stage_repo = stage_repo
        self._audit_repo = audit_repo
        self._artifact_store = artifact_store
        self._artifact_metadata_repo = artifact_metadata_repo
        self._uuid_generator = uuid_generator
        self._current_job: Job | None = None

    def execute(self, command: ParseCatalogCommand) -> ParseCatalogResult:
        """Execute the parse-catalog stage.

        Args:
            command: ParseCatalogCommand with job_id, filename, content.

        Returns:
            ParseCatalogResult with stage outcome and artifact references.

        Raises:
            JobNotFoundError: If job does not exist.
            InvalidStateTransitionError: If job/stage not in valid state.
            StageAlreadyCompletedError: If stage already completed.
            InvalidFileFormatError: If file is not JSON.
            InvalidJSONError: If content is not valid JSON dict.
            CatalogSchemaValidationError: If catalog fails schema validation.
            ArtifactStoreError: If artifact storage fails.
        """
        job, stage = self._load_and_guard_stage(command)
        self._current_job = job

        # Idempotency: if stage already completed, return existing result
        existing = self._check_idempotent_completion(command, stage)
        if existing is not None:
            return existing

        try:
            self._mark_stage_started(job, stage, command)
            self._validate_file_format(command.filename)
            catalog_data = self._parse_and_validate_json(command.content)
            catalog_ref = self._store_catalog_artifact(command)
            root_jsons_ref = self._generate_and_store_root_jsons(
                command, catalog_data
            )
            self._mark_stage_completed(stage, command)
            return self._build_success_result(
                command, catalog_ref, root_jsons_ref
            )
        except Exception as e:
            self._mark_stage_failed(stage, command, e)
            raise

    # ------------------------------------------------------------------
    # Stage guards
    # ------------------------------------------------------------------

    def _load_and_guard_stage(
        self, command: ParseCatalogCommand
    ) -> Tuple[Job, Stage]:
        """Load job and parse-catalog stage, enforce preconditions."""
        job = self._job_repo.find_by_id(command.job_id)
        if job is None:
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

        stage = self._stage_repo.find_by_job_and_name(
            command.job_id, StageName(StageType.PARSE_CATALOG.value)
        )
        if stage is None:
            raise JobNotFoundError(
                job_id=str(command.job_id),
                correlation_id=str(command.correlation_id),
            )

        if stage.stage_state == StageState.COMPLETED:
            raise StageAlreadyCompletedError(
                job_id=str(command.job_id),
                stage_name="parse-catalog",
                correlation_id=str(command.correlation_id),
            )

        if stage.stage_state != StageState.PENDING:
            raise InvalidStateTransitionError(
                entity_type="Stage",
                entity_id=f"{command.job_id}/parse-catalog",
                from_state=stage.stage_state.value,
                to_state="IN_PROGRESS",
                correlation_id=str(command.correlation_id),
            )

        return job, stage

    def _check_idempotent_completion(
        self, command: ParseCatalogCommand, stage: Stage
    ) -> ParseCatalogResult | None:
        """If stage already completed with artifacts, return existing result."""
        # Stage guard already rejects COMPLETED, so this is only for
        # future use if we relax the guard for idempotent retries.
        return None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_file_format(self, filename: str) -> None:
        """Validate that the file has a .json extension."""
        if not filename.lower().endswith(".json"):
            raise InvalidFileFormatError(
                "Invalid file format. Only JSON files are accepted."
            )

    def _parse_and_validate_json(self, content: bytes) -> dict:
        """Parse JSON content from bytes and validate structure."""
        try:
            data = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise InvalidJSONError(f"Invalid JSON data: {e.msg}") from e
        except UnicodeDecodeError as e:
            raise InvalidJSONError("File content is not valid UTF-8 text") from e

        if not isinstance(data, dict):
            raise InvalidJSONError(
                "Invalid JSON data. The data must be a dictionary."
            )
        return data

    # ------------------------------------------------------------------
    # Artifact storage
    # ------------------------------------------------------------------

    def _store_catalog_artifact(
        self, command: ParseCatalogCommand
    ) -> ArtifactRef:
        """Store the uploaded catalog file as a FILE artifact."""
        hint = StoreHint(
            namespace="catalog",
            label="catalog-file",
            tags={"job_id": str(command.job_id)},
        )

        try:
            catalog_ref = self._artifact_store.store(
                hint=hint,
                kind=ArtifactKind.FILE,
                content=command.content,
                content_type="application/json",
            )
        except ArtifactAlreadyExistsError:
            # Idempotent: artifact already stored from a previous attempt
            key = self._artifact_store.generate_key(hint, ArtifactKind.FILE)
            raw = self._artifact_store.retrieve(key, ArtifactKind.FILE)
            digest = ArtifactDigest(hashlib.sha256(raw).hexdigest())
            catalog_ref = ArtifactRef(
                key=key, digest=digest, size_bytes=len(raw),
                uri=f"memory://{key.value}",
            )

        record = ArtifactRecord(
            id=str(self._uuid_generator.generate()),
            job_id=command.job_id,
            stage_name=StageName(StageType.PARSE_CATALOG.value),
            label="catalog-file",
            artifact_ref=catalog_ref,
            kind=ArtifactKind.FILE,
            content_type="application/json",
            tags={"job_id": str(command.job_id)},
        )
        self._artifact_metadata_repo.save(record)

        return catalog_ref

    def _generate_and_store_root_jsons(
        self,
        command: ParseCatalogCommand,
        catalog_data: dict,
    ) -> Tuple[ArtifactRef, Dict[str, bytes]]:
        """Generate root JSONs and store as ARCHIVE artifact."""
        with tempfile.TemporaryDirectory(
            prefix=f"parse-catalog-{command.job_id}-"
        ) as tmp_dir:
            tmp_path = Path(tmp_dir)
            catalog_file = tmp_path / "catalog.json"
            catalog_file.write_text(
                json.dumps(catalog_data), encoding="utf-8"
            )

            output_dir = tmp_path / "root_jsons"
            output_dir.mkdir()

            try:
                generate_root_json_from_catalog(
                    catalog_path=str(catalog_file),
                    output_root=str(output_dir),
                )
            except ValidationError as e:
                # Preserve the original validation error message
                error_msg = f"Catalog schema validation failed: {e.message}"
                if e.absolute_path:
                    error_msg += f" at {'/'.join(str(p) for p in e.absolute_path)}"
                raise CatalogSchemaValidationError(error_msg) from e
            except Exception as e:
                raise CatalogSchemaValidationError(
                    f"Catalog processing failed: {e}"
                ) from e

            hint = StoreHint(
                namespace="catalog",
                label="root-jsons",
                tags={"job_id": str(command.job_id)},
            )

            try:
                root_jsons_ref = self._artifact_store.store(
                    hint=hint,
                    kind=ArtifactKind.ARCHIVE,
                    source_directory=output_dir,
                    content_type="application/zip",
                )
            except ArtifactAlreadyExistsError:
                key = self._artifact_store.generate_key(hint, ArtifactKind.ARCHIVE)
                raw = self._artifact_store.retrieve(key, ArtifactKind.FILE)
                digest = ArtifactDigest(hashlib.sha256(raw).hexdigest())
                root_jsons_ref = ArtifactRef(
                    key=key, digest=digest, size_bytes=len(raw),
                    uri=f"memory://{key.value}",
                )

            record = ArtifactRecord(
                id=str(self._uuid_generator.generate()),
                job_id=command.job_id,
                stage_name=StageName(StageType.PARSE_CATALOG.value),
                label="root-jsons",
                artifact_ref=root_jsons_ref,
                kind=ArtifactKind.ARCHIVE,
                content_type="application/zip",
                tags={
                    "job_id": str(command.job_id),
                },
            )
            self._artifact_metadata_repo.save(record)

            return root_jsons_ref

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

        self._emit_audit_event(
            command, "STAGE_STARTED", {"stage_name": "parse-catalog"}
        )

    def _mark_stage_completed(
        self, stage: Stage, command: ParseCatalogCommand
    ) -> None:
        """Transition stage to COMPLETED."""
        stage.complete()
        self._stage_repo.save(stage)
        self._emit_audit_event(
            command, "STAGE_COMPLETED", {"stage_name": "parse-catalog"}
        )

    def _mark_stage_failed(
        self, stage: Stage, command: ParseCatalogCommand, error: Exception
    ) -> None:
        """Transition stage to FAILED with error details."""
        error_code = type(error).__name__
        error_summary = str(error)[:256]
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

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def _emit_audit_event(
        self,
        command: ParseCatalogCommand,
        event_type: str,
        details: dict,
    ) -> None:
        """Emit an audit event."""
        client_id = (
            self._current_job.client_id
            if self._current_job is not None
            else ClientId("unknown")
        )
        event = AuditEvent(
            event_id=str(self._uuid_generator.generate()),
            job_id=command.job_id,
            event_type=event_type,
            correlation_id=command.correlation_id,
            client_id=client_id,
            timestamp=datetime.now(timezone.utc),
            details=details,
        )
        self._audit_repo.save(event)

    # ------------------------------------------------------------------
    # Result building
    # ------------------------------------------------------------------

    def _build_success_result(
        self,
        command: ParseCatalogCommand,
        catalog_ref: ArtifactRef,
        root_jsons_ref: ArtifactRef,
    ) -> ParseCatalogResult:
        """Build the success result DTO."""
        return ParseCatalogResult(
            job_id=str(command.job_id),
            stage_state="COMPLETED",
            message="Catalog parsed successfully",
            catalog_ref=catalog_ref,
            root_jsons_ref=root_jsons_ref,
            root_json_count=0,  # No longer tracking file count
            arch_os_combinations=[],  # No longer tracking combinations
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
