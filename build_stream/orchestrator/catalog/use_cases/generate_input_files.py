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

"""GenerateInputFiles use case implementation."""

import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from core.artifacts.entities import ArtifactRecord
from core.artifacts.exceptions import ArtifactNotFoundError
from core.artifacts.ports import ArtifactMetadataRepository, ArtifactStore
from core.artifacts.value_objects import (
    ArtifactKind,
    ArtifactRef,
    SafePath,
    StoreHint,
)
from core.catalog.adapter_policy import generate_configs_from_policy
from core.catalog.exceptions import (
    AdapterPolicyValidationError,
    ConfigGenerationError,
)
from common.config import load_config
from core.jobs.entities import AuditEvent, Job, Stage
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    StageAlreadyCompletedError,
    TerminalStateViolationError,
    UpstreamStageNotCompletedError,
)
from core.jobs.repositories import (
    AuditEventRepository,
    JobRepository,
    StageRepository,
    UUIDGenerator,
)
from core.jobs.value_objects import JobId, StageName, StageType, StageState, JobState

from orchestrator.catalog.commands.generate_input_files import GenerateInputFilesCommand
from orchestrator.catalog.dtos import GenerateInputFilesResult

logger = logging.getLogger(__name__)


class GenerateInputFilesUseCase:
    """Use case for executing the generate-input-files stage.

    Orchestrates:
    1. Stage guard validation (parse-catalog COMPLETED, this stage PENDING)
    2. Upstream artifact retrieval (root JSONs from parse-catalog)
    3. Adapter policy loading and validation
    4. Omnia config generation via adapter policy engine
    5. Output artifact storage (configs archive)
    6. Artifact metadata persistence
    7. Stage state transitions and audit events
    """

    def __init__(
        self,
        job_repo: JobRepository,
        stage_repo: StageRepository,
        audit_repo: AuditEventRepository,
        artifact_store: ArtifactStore,
        artifact_metadata_repo: ArtifactMetadataRepository,
        uuid_generator: UUIDGenerator,
        default_policy_path: SafePath,
        policy_schema_path: SafePath,
    ) -> None:
        self._job_repo = job_repo
        self._stage_repo = stage_repo
        self._audit_repo = audit_repo
        self._artifact_store = artifact_store
        self._artifact_metadata_repo = artifact_metadata_repo
        self._uuid_generator = uuid_generator
        self._default_policy_path = default_policy_path
        self._policy_schema_path = policy_schema_path
        self._current_job: Job | None = None

    def execute(
        self, command: GenerateInputFilesCommand
    ) -> GenerateInputFilesResult:
        """Execute the generate-input-files stage."""
        job, stage = self._load_and_guard_stage(command)
        self._current_job = job
        self._verify_upstream_stage_completed(command)

        try:
            self._mark_stage_started(job, stage, command)
            with tempfile.TemporaryDirectory(
                prefix=f"gif-{command.job_id}-"
            ) as tmp_dir:
                root_jsons_dir = self._retrieve_upstream_artifacts(
                    command, Path(tmp_dir)
                )
                policy_path = self._resolve_policy_path(command)
                config_output_dir = self._generate_omnia_configs(
                    root_jsons_dir, policy_path, Path(tmp_dir)
                )
                configs_ref, configs_record = self._store_output_artifacts(
                    command, config_output_dir
                )
                self._copy_configs_to_artifacts_input_dir(command, config_output_dir)

                self._mark_stage_completed(stage, command)
                return self._build_success_result(
                    command, configs_ref, configs_record, config_output_dir
                )
        except Exception as e:
            self._mark_stage_failed(stage, command, e)
            raise

    # ------------------------------------------------------------------
    # Stage guards
    # ------------------------------------------------------------------

    def _load_and_guard_stage(
        self, command: GenerateInputFilesCommand
    ) -> Tuple[Job, Stage]:
        """Load job and generate-input-files stage, enforce preconditions."""
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
            command.job_id, StageName(StageType.GENERATE_INPUT_FILES.value)
        )
        if stage is None:
            raise JobNotFoundError(
                job_id=str(command.job_id),
                correlation_id=str(command.correlation_id),
            )

        if stage.stage_state == StageState.COMPLETED:
            raise StageAlreadyCompletedError(
                job_id=str(command.job_id),
                stage_name="generate-input-files",
                correlation_id=str(command.correlation_id),
            )

        if stage.stage_state != StageState.PENDING:
            raise InvalidStateTransitionError(
                entity_type="Stage",
                entity_id=f"{command.job_id}/generate-input-files",
                from_state=stage.stage_state.value,
                to_state="IN_PROGRESS",
                correlation_id=str(command.correlation_id),
            )

        return job, stage

    def _verify_upstream_stage_completed(
        self, command: GenerateInputFilesCommand
    ) -> None:
        """Verify that parse-catalog stage is COMPLETED."""
        parse_stage = self._stage_repo.find_by_job_and_name(
            command.job_id, StageName(StageType.PARSE_CATALOG.value)
        )
        if (
            parse_stage is None
            or parse_stage.stage_state != StageState.COMPLETED
        ):
            raise UpstreamStageNotCompletedError(
                job_id=str(command.job_id),
                required_stage="parse-catalog",
                actual_state=(
                    parse_stage.stage_state.value
                    if parse_stage
                    else "NOT_FOUND"
                ),
                correlation_id=str(command.correlation_id),
            )

    # ------------------------------------------------------------------
    # Artifact retrieval
    # ------------------------------------------------------------------

    def _retrieve_upstream_artifacts(
        self, command: GenerateInputFilesCommand, tmp_base: Path
    ) -> Path:
        """Retrieve root JSONs archive from ArtifactStore and unpack."""
        record = self._artifact_metadata_repo.find_by_job_stage_and_label(
            job_id=command.job_id,
            stage_name=StageName(StageType.PARSE_CATALOG.value),
            label="root-jsons",
        )
        if record is None:
            raise ArtifactNotFoundError(
                key=f"root-jsons for job {command.job_id}",
                correlation_id=str(command.correlation_id),
            )

        destination = tmp_base / "root-jsons"
        return self._artifact_store.retrieve(
            key=record.artifact_ref.key,
            kind=ArtifactKind.ARCHIVE,
            destination=destination,
        )

    # ------------------------------------------------------------------
    # Config generation
    # ------------------------------------------------------------------

    def _resolve_policy_path(
        self, command: GenerateInputFilesCommand
    ) -> str:
        """Resolve the adapter policy path."""
        if command.adapter_policy_path is not None:
            policy_path = str(command.adapter_policy_path.value)
        else:
            policy_path = str(self._default_policy_path.value)

        if not os.path.isfile(policy_path):
            raise FileNotFoundError(f"Adapter policy not found: {policy_path}")
        return policy_path

    def _generate_omnia_configs(
        self,
        root_jsons_dir: Path,
        policy_path: str,
        tmp_base: Path,
    ) -> Path:
        """Generate Omnia config files using the adapter policy engine."""
        output_dir = tmp_base / "omnia-configs"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            generate_configs_from_policy(
                input_dir=str(root_jsons_dir),
                output_dir=str(output_dir),
                policy_path=policy_path,
                schema_path=str(self._policy_schema_path.value),
            )
        except ValueError as e:
            raise AdapterPolicyValidationError(str(e)) from e
        except FileNotFoundError:
            raise
        except Exception as e:
            raise ConfigGenerationError(
                f"Config generation failed: {e}"
            ) from e

        # Check if any files were generated
        has_files = any(
            filename.endswith(".json")
            for root, _dirs, files in os.walk(str(output_dir))
            for filename in files
        )

        if not has_files:
            raise ConfigGenerationError(
                "No config files generated. Check adapter policy and root JSONs."
            )

        return output_dir

    # ------------------------------------------------------------------
    # Artifact storage
    # ------------------------------------------------------------------

    def _store_output_artifacts(
        self,
        command: GenerateInputFilesCommand,
        config_output_dir: Path,
    ) -> Tuple[ArtifactRef, ArtifactRecord]:
        """Store generated configs as archive artifact and persist metadata."""
        hint = StoreHint(
            namespace="input-files",
            label="omnia-configs",
            tags={"job_id": str(command.job_id)},
        )

        configs_ref = self._artifact_store.store(
            hint=hint,
            kind=ArtifactKind.ARCHIVE,
            source_directory=config_output_dir,
            content_type="application/zip",
        )

        record = ArtifactRecord(
            id=str(self._uuid_generator.generate()),
            job_id=command.job_id,
            stage_name=StageName(StageType.GENERATE_INPUT_FILES.value),
            label="omnia-configs",
            artifact_ref=configs_ref,
            kind=ArtifactKind.ARCHIVE,
            content_type="application/zip",
            tags={
                "job_id": str(command.job_id),
            },
        )
        self._artifact_metadata_repo.save(record)

        return configs_ref, record

    def _copy_configs_to_artifacts_input_dir(
        self,
        command: GenerateInputFilesCommand,
        config_output_dir: Path,
    ) -> None:
        """Copy generated config files to artifacts/{job_id}/ directory.
        
        This creates a copy of the generated input files in the expected location
        for the NfsInputDirectoryRepository to consume.
        
        Args:
            command: Generate input files command.
            config_output_dir: Directory containing generated config files.
        """
        import shutil
        
        # Load config and get artifacts base path from configuration
        config = load_config()
        artifacts_base = Path(config.file_store.base_path)
        target_dir = artifacts_base / str(command.job_id)
        
        # Create target directory if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all contents from config_output_dir to target_dir
        for item in config_output_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, target_dir / item.name)
            elif item.is_dir():
                shutil.copytree(item, target_dir / item.name, dirs_exist_ok=True)
        
        logger.info(
            "Copied generated configs to artifacts input directory: %s",
            target_dir
        )

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _mark_stage_started(
        self, job: Job, stage: Stage, command: GenerateInputFilesCommand
    ) -> None:
        """Transition stage to IN_PROGRESS."""
        stage.start()
        self._stage_repo.save(stage)
        self._emit_audit_event(
            command, "STAGE_STARTED",
            {"stage_name": "generate-input-files"},
        )

    def _mark_stage_completed(
        self, stage: Stage, command: GenerateInputFilesCommand
    ) -> None:
        """Transition stage to COMPLETED."""
        stage.complete()
        self._stage_repo.save(stage)
        self._emit_audit_event(
            command, "STAGE_COMPLETED",
            {"stage_name": "generate-input-files"},
        )

    def _mark_stage_failed(
        self, stage: Stage, command: GenerateInputFilesCommand, error: Exception
    ) -> None:
        """Transition stage to FAILED with error details."""
        error_code = type(error).__name__
        error_summary = str(error)[:256]
        stage.fail(error_code=error_code, error_summary=error_summary)
        self._stage_repo.save(stage)
        self._emit_audit_event(
            command, "STAGE_FAILED",
            {
                "stage_name": "generate-input-files",
                "error_code": error_code,
                "error_summary": error_summary,
            },
        )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def _emit_audit_event(
        self,
        command: GenerateInputFilesCommand,
        event_type: str,
        details: dict,
    ) -> None:
        """Emit an audit event."""
        from core.jobs.value_objects import ClientId
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
        command: GenerateInputFilesCommand,
        configs_ref: ArtifactRef,
        configs_record: ArtifactRecord,
        config_output_dir: Path,
    ) -> GenerateInputFilesResult:
        """Build minimal success result with only essential fields."""
        return GenerateInputFilesResult(
            job_id=str(command.job_id),
            stage_state="COMPLETED",
            message="Input files generated successfully",
            configs_ref=configs_ref,
            config_file_count=0,  # Not included in minimal response
            config_files=[],      # Not included in minimal response
            arch_os_combinations=[],  # Not included in minimal response
            completed_at="",     # Not included in minimal response
        )
