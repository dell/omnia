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

"""Upload files use case implementation."""

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from common.config import BuildStreamConfig
from core.artifacts.entities import ArtifactRecord
from core.artifacts.interfaces import ArtifactMetadataRepository, ArtifactStore
from core.artifacts.value_objects import ArtifactKind, StoreHint
from core.jobs.repositories import JobRepository, StageRepository, AuditEventRepository
from core.jobs.exceptions import JobNotFoundError, TerminalStateViolationError, StageNotFoundError
from core.jobs.value_objects import StageName, StageType, StageState
from core.jobs.entities import AuditEvent
from infra.id_generator import UUIDGenerator

from orchestrator.upload.commands.upload_files import UploadFilesCommand
from orchestrator.upload.results.upload_files import (
    UploadFilesResult,
    UploadedFileInfo,
    FileChangeStatus,
    UploadSummary,
)
from orchestrator.upload.exceptions import InvalidFilenameError, FileSizeExceededError


logger = logging.getLogger(__name__)


# Shared input directory path for playbook consumption
# This matches the path used by NfsInputRepository and expected by Omnia playbooks
DEFAULT_PLAYBOOK_INPUT_DIR = "/opt/omnia/input/project_default/"

# Whitelist of allowed configuration files
ALLOWED_CONFIG_FILES = {
    "local_repo_config.yml",
    "network_spec.yml",
    "provision_config.yml",
    "pxe_mapping_file.csv",
    "storage_config.yml",
    "telemetry_config.yml",
    "storage_config.yml",
    "security_config.yml",
    "high_availability_config.yml",
    "omnia_config.yml",
    "build_stream_config.yml",
}


class UploadFilesUseCase:
    """Use case for uploading configuration files to a job.

    This use case implements the multi-destination storage strategy:
    1. Immutable storage in ArtifactStore (for audit trail)
    2. Job-scoped NFS directory (for job-specific context)
    3. Shared input directory (for playbook consumption)

    Change detection is performed via SHA-256 hash comparison to optimize
    storage operations and provide accurate change status to clients.
    """

    def __init__(
        self,
        job_repository: JobRepository,
        stage_repository: StageRepository,
        audit_repository: AuditEventRepository,
        artifact_store: ArtifactStore,
        artifact_metadata_repo: ArtifactMetadataRepository,
        uuid_generator: UUIDGenerator,
        config: BuildStreamConfig,
    ):
        """Initialize use case with dependencies.

        Args:
            job_repository: Repository for job entities.
            stage_repository: Repository for stage entities.
            audit_repository: Repository for audit events.
            artifact_store: Store for immutable artifacts.
            artifact_metadata_repo: Repository for artifact metadata.
            uuid_generator: UUID generator for events.
            config: BuildStream configuration.
        """
        self._job_repo = job_repository
        self._stage_repo = stage_repository
        self._audit_repo = audit_repository
        self._artifact_store = artifact_store
        self._artifact_metadata_repo = artifact_metadata_repo
        self._uuid_generator = uuid_generator
        self._config = config

    def execute(self, command: UploadFilesCommand) -> UploadFilesResult:
        """Execute upload files operation.

        Args:
            command: Upload files command.

        Returns:
            Upload result with summary and file details.

        Raises:
            JobNotFoundError: If job does not exist.
            TerminalStateViolationError: If job is in terminal state.
            InvalidFilenameError: If any filename is not in whitelist.
            FileSizeExceededError: If any file exceeds size limit.
        """
        logger.info("Executing upload files for job_id=%s", command.job_id)

        # Validate job exists and is in valid state
        self._current_job = self._validate_job(command.job_id)

        # Retrieve and validate upload stage
        stage = self._get_upload_stage(command.job_id)

        # Validate all files before processing (fail-fast)
        self._validate_all_files(command.files)

        # Mark stage as started (first upload transitions to IN_PROGRESS)
        # Allow uploads even if stage is already COMPLETED
        if stage.stage_state == StageState.PENDING:
            # Collect filenames for audit event
            filenames = [filename for filename, _ in command.files]
            self._mark_stage_started(stage, command, filenames)

        # Process each file
        uploaded_files: List[UploadedFileInfo] = []
        changed_count = 0
        unchanged_count = 0

        for filename, content in command.files:
            file_info = self._process_file(command.job_id, filename, content)
            uploaded_files.append(file_info)

            if file_info.status == FileChangeStatus.CHANGED:
                changed_count += 1
            else:
                unchanged_count += 1

        # Emit audit event for file upload
        if stage.stage_state != StageState.COMPLETED:
            # First upload: mark stage as completed
            self._mark_stage_completed(stage)
        
        # Always emit audit event with file details (for all uploads)
        self._emit_upload_files_audit_event(command, uploaded_files)

        # Build result
        summary = UploadSummary(
            total_files=len(uploaded_files),
            changed_files=changed_count,
            unchanged_files=unchanged_count,
        )

        result = UploadFilesResult(
            job_id=str(command.job_id),
            upload_summary=summary,
            files=uploaded_files,
        )

        logger.info(
            "Upload completed: job_id=%s, total=%d, changed=%d, unchanged=%d",
            command.job_id,
            summary.total_files,
            summary.changed_files,
            summary.unchanged_files,
        )

        return result

    def _validate_job(self, job_id):
        """Validate job exists and is not in terminal state.

        Args:
            job_id: Job identifier.

        Returns:
            Job entity.

        Raises:
            JobNotFoundError: If job does not exist.
            TerminalStateViolationError: If job is in terminal state.
        """
        job = self._job_repo.find_by_id(job_id)
        if job is None:
            raise JobNotFoundError(f"Job not found: {job_id}")

        if job.is_completed() or job.is_failed() or job.is_cancelled():
            raise TerminalStateViolationError(
                entity_type="Job",
                entity_id=str(job_id),
                state=job.job_state.value
            )

        return job

    def _validate_all_files(self, files: List[tuple]):
        """Validate all files before processing (fail-fast).

        Args:
            files: List of (filename, content) tuples.

        Raises:
            InvalidFilenameError: If any filename is invalid.
            FileSizeExceededError: If any file exceeds size limit.
        """
        for filename, content in files:
            self._validate_filename(filename)
            self._validate_file_size(content, filename)

    def _validate_filename(self, filename: str):
        """Validate filename is in allowed whitelist.

        Args:
            filename: Filename to validate.

        Raises:
            InvalidFilenameError: If filename is not in whitelist.
        """
        if filename not in ALLOWED_CONFIG_FILES:
            raise InvalidFilenameError(
                f"Filename '{filename}' is not in allowed whitelist. "
                f"Allowed files: {sorted(ALLOWED_CONFIG_FILES)}"
            )

    def _validate_file_size(self, content: bytes, filename: str):
        """Validate file size is within limits.

        Args:
            content: File content.
            filename: Filename for error message.

        Raises:
            FileSizeExceededError: If file exceeds maximum size.
        """
        max_size = self._config.artifact_store.max_file_size_bytes
        file_size = len(content)

        if file_size > max_size:
            raise FileSizeExceededError(
                f"File '{filename}' size ({file_size} bytes) exceeds "
                f"maximum size ({max_size} bytes)"
            )

    def _process_file(
        self,
        job_id,
        filename: str,
        content: bytes,
    ) -> UploadedFileInfo:
        """Process a single file upload.

        Args:
            job_id: Job identifier.
            filename: Filename.
            content: File content.

        Returns:
            Uploaded file information.
        """
        # Compute SHA-256 digest for change detection
        current_digest = hashlib.sha256(content).hexdigest()

        # Check for previous upload
        previous_record = self._artifact_metadata_repo.find_by_job_stage_and_label(
            job_id=job_id,
            stage_name=StageName(StageType.UPLOAD.value),
            label=filename,
        )

        # Determine change status
        if previous_record and previous_record.artifact_ref.digest.value == current_digest:
            status = FileChangeStatus.UNCHANGED
            logger.debug("File unchanged: %s (digest: %s)", filename, current_digest[:12])
        else:
            status = FileChangeStatus.CHANGED
            logger.debug("File changed: %s (digest: %s)", filename, current_digest[:12])

            # Store in ArtifactStore only for changed files
            self._store_in_artifact_store(job_id, filename, content)

        # Always write to both NFS locations (job-scoped and shared)
        self._write_to_nfs_job_directory(job_id, filename, content)
        self._write_to_shared_input_directory(filename, content)

        return UploadedFileInfo(
            filename=filename,
            status=status,
            size_bytes=len(content),
        )

    def _store_in_artifact_store(self, job_id, filename: str, content: bytes):
        """Store file in immutable ArtifactStore and save metadata.

        Args:
            job_id: Job identifier.
            filename: Filename.
            content: File content.
        """
        hint = StoreHint(
            namespace="config-files",
            label=filename,
            tags={"job_id": str(job_id)},
        )

        artifact_ref = self._artifact_store.store(
            hint=hint,
            kind=ArtifactKind.FILE,
            content=content,
            content_type="application/octet-stream",
        )

        # Save metadata
        record = ArtifactRecord(
            id=self._generate_id(),
            job_id=job_id,
            stage_name=StageName(StageType.UPLOAD.value),
            label=filename,
            artifact_ref=artifact_ref,
            kind=ArtifactKind.FILE,
            content_type="application/octet-stream",
            tags={"filename": filename},
            created_at=None,  # Will be set by repository
        )

        self._artifact_metadata_repo.save(record)

        logger.debug(
            "Stored in ArtifactStore: %s (key: %s)",
            filename,
            artifact_ref.key,
        )

    def _write_to_nfs_job_directory(self, job_id, filename: str, content: bytes):
        """Write file to job-scoped NFS directory.

        Args:
            job_id: Job identifier.
            filename: Filename.
            content: File content.
        """
        base_path = Path(self._config.file_store.base_path)
        target_dir = base_path / str(job_id) / "artifacts"
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / filename
        target_file.write_bytes(content)

        logger.debug("Wrote to NFS job directory: %s", target_file)

    def _write_to_shared_input_directory(self, filename: str, content: bytes):
        """Write file to shared input directory.

        Args:
            filename: Filename.
            content: File content.
        """
        # Use the standard Omnia playbook input directory
        # This path matches NfsInputRepository.get_destination_input_repository_path()
        playbook_input_dir = Path(DEFAULT_PLAYBOOK_INPUT_DIR)
        playbook_input_dir.mkdir(parents=True, exist_ok=True)

        target_file = playbook_input_dir / filename
        target_file.write_bytes(content)

        logger.debug("Wrote to shared input directory: %s", target_file)

    def _generate_id(self) -> str:
        """Generate unique identifier for artifact record.

        Returns:
            UUID string.
        """
        import uuid
        return str(uuid.uuid4())

    def _get_upload_stage(self, job_id):
        """Retrieve upload stage for the job.

        Args:
            job_id: Job identifier.

        Returns:
            Upload stage entity.

        Raises:
            StageNotFoundError: If upload stage does not exist.
        """
        stage = self._stage_repo.find_by_job_and_name(
            job_id=job_id,
            stage_name=StageName(StageType.UPLOAD.value),
        )

        if stage is None:
            raise StageNotFoundError(
                job_id=str(job_id),
                stage_name=StageType.UPLOAD.value,
            )

        return stage

    def _mark_stage_started(self, stage, command: UploadFilesCommand, filenames: List[str]):
        """Transition stage to IN_PROGRESS.

        Args:
            stage: Stage entity.
            command: Upload files command.
            filenames: List of filenames being uploaded.
        """
        stage.start()
        self._stage_repo.save(stage)
        self._emit_audit_event(
            command,
            "STAGE_STARTED",
            {
                "stage_name": "upload",
                "files": filenames,
                "file_count": len(filenames),
            }
        )
        logger.info("Upload stage started: job_id=%s, files=%s", stage.job_id, filenames)

    def _mark_stage_completed(self, stage):
        """Transition stage to COMPLETED.

        Args:
            stage: Stage entity.
        """
        stage.complete()
        self._stage_repo.save(stage)
        logger.info("Upload stage marked as completed: job_id=%s", stage.job_id)

    def _emit_upload_files_audit_event(
        self,
        command: UploadFilesCommand,
        uploaded_files: List[UploadedFileInfo]
    ):
        """Emit audit event for file upload.

        Args:
            command: Upload files command.
            uploaded_files: List of uploaded file information.
        """
        # Build file details for audit event
        file_details = [
            {
                "filename": file_info.filename,
                "status": file_info.status.value,
                "size_bytes": file_info.size_bytes,
            }
            for file_info in uploaded_files
        ]

        # Count changed vs unchanged
        changed_count = sum(1 for f in uploaded_files if f.status == FileChangeStatus.CHANGED)
        unchanged_count = sum(1 for f in uploaded_files if f.status == FileChangeStatus.UNCHANGED)

        self._emit_audit_event(
            command,
            "STAGE_COMPLETED",
            {
                "stage_name": "upload",
                "files": file_details,
                "total_files": len(uploaded_files),
                "changed_files": changed_count,
                "unchanged_files": unchanged_count,
            }
        )
        
        logger.info(
            "Files uploaded: job_id=%s, total=%d, changed=%d, unchanged=%d",
            command.job_id, len(uploaded_files), changed_count, unchanged_count
        )

    def _emit_audit_event(
        self,
        command: UploadFilesCommand,
        event_type: str,
        details: dict,
    ) -> None:
        """Emit an audit event.

        Args:
            command: Upload files command.
            event_type: Type of audit event.
            details: Additional event details.
        """
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
