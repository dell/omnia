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

"""Unit tests for GenerateInputFilesUseCase."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from core.artifacts.entities import ArtifactRecord
from core.artifacts.exceptions import ArtifactNotFoundError
from core.artifacts.value_objects import (
    ArtifactDigest,
    ArtifactKey,
    ArtifactKind,
    ArtifactRef,
    SafePath,
    StoreHint,
)
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    StageAlreadyCompletedError,
    TerminalStateViolationError,
    UpstreamStageNotCompletedError,
)
from core.jobs.value_objects import (
    CorrelationId,
    JobId,
    StageName,
    StageState,
    StageType,
)
from orchestrator.catalog.commands.generate_input_files import (
    GenerateInputFilesCommand,
)
from orchestrator.catalog.use_cases.generate_input_files import (
    GenerateInputFilesUseCase,
)


VALID_JOB_ID = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
VALID_CORRELATION_ID = "018f3c4b-2d9e-7d1a-8a2b-111111111111"


def _make_command() -> GenerateInputFilesCommand:
    return GenerateInputFilesCommand(
        job_id=JobId(VALID_JOB_ID),
        correlation_id=CorrelationId(VALID_CORRELATION_ID),
    )


def _build_use_case(
    job_repo, stage_repo, audit_repo,
    artifact_store, artifact_metadata_repo, uuid_generator,
    default_policy_path=None,
    policy_schema_path=None,
) -> GenerateInputFilesUseCase:
    if default_policy_path is None:
        # Use the real default adapter policy from the codebase
        base = Path(__file__).resolve().parent.parent.parent.parent.parent / "core" / "catalog" / "resources"
        policy = base / "adapter_policy_default.json"
        schema = base / "AdapterPolicySchema.json"
        # Fallback checks for different file naming conventions (historical/compatibility)
        if not policy.is_file():
            policy = base / "adapter_policy.json"
        if not schema.is_file():
            schema = base / "adapter_policy_schema.json"
        default_policy_path = SafePath(value=policy)
        policy_schema_path = SafePath(value=schema)

    return GenerateInputFilesUseCase(
        job_repo=job_repo,
        stage_repo=stage_repo,
        audit_repo=audit_repo,
        artifact_store=artifact_store,
        artifact_metadata_repo=artifact_metadata_repo,
        uuid_generator=uuid_generator,
        default_policy_path=default_policy_path,
        policy_schema_path=policy_schema_path,
    )


def _seed_upstream_artifacts(
    artifact_store, artifact_metadata_repo, uuid_generator,
    job_id_str=VALID_JOB_ID,
):
    """Pre-populate root-jsons artifact as if parse-catalog completed."""
    file_map = {
        "x86_64/rhel/9.5/functional_layer.json": json.dumps(
            {"FeatureList": []}
        ).encode(),
        "x86_64/rhel/9.5/base_os.json": json.dumps(
            {"FeatureList": []}
        ).encode(),
        "x86_64/rhel/9.5/infrastructure.json": json.dumps(
            {"FeatureList": []}
        ).encode(),
        "x86_64/rhel/9.5/drivers.json": json.dumps(
            {"FeatureList": []}
        ).encode(),
        "x86_64/rhel/9.5/miscellaneous.json": json.dumps(
            {"FeatureList": []}
        ).encode(),
    }
    hint = StoreHint(
        namespace="catalog",
        label="root-jsons",
        tags={"job_id": job_id_str},
    )
    ref = artifact_store.store(
        hint=hint,
        kind=ArtifactKind.ARCHIVE,
        file_map=file_map,
        content_type="application/zip",
    )
    record = ArtifactRecord(
        id=str(uuid_generator.generate()),
        job_id=JobId(job_id_str),
        stage_name=StageName(StageType.PARSE_CATALOG.value),
        label="root-jsons",
        artifact_ref=ref,
        kind=ArtifactKind.ARCHIVE,
        content_type="application/zip",
    )
    artifact_metadata_repo.save(record)
    return ref


class TestStageGuards:
    """Tests for stage guard validation."""

    def test_job_not_found(
        self, job_repo, stage_repo, audit_repo,
        artifact_store, artifact_metadata_repo, uuid_generator,
    ) -> None:
        uc = _build_use_case(
            job_repo, stage_repo, audit_repo,
            artifact_store, artifact_metadata_repo, uuid_generator,
        )
        with pytest.raises(JobNotFoundError):
            uc.execute(_make_command())

    def test_job_in_terminal_state(
        self, job_repo, stage_repo, audit_repo,
        artifact_store, artifact_metadata_repo, uuid_generator,
        in_progress_job, generate_input_files_stage,
    ) -> None:
        in_progress_job.fail()
        job_repo.save(in_progress_job)
        stage_repo.save(generate_input_files_stage)

        uc = _build_use_case(
            job_repo, stage_repo, audit_repo,
            artifact_store, artifact_metadata_repo, uuid_generator,
        )
        with pytest.raises(TerminalStateViolationError):
            uc.execute(_make_command())

    def test_stage_already_completed(
        self, job_repo, stage_repo, audit_repo,
        artifact_store, artifact_metadata_repo, uuid_generator,
        in_progress_job, generate_input_files_stage,
    ) -> None:
        generate_input_files_stage.start()
        generate_input_files_stage.complete()
        job_repo.save(in_progress_job)
        stage_repo.save(generate_input_files_stage)

        uc = _build_use_case(
            job_repo, stage_repo, audit_repo,
            artifact_store, artifact_metadata_repo, uuid_generator,
        )
        with pytest.raises(StageAlreadyCompletedError):
            uc.execute(_make_command())


class TestUpstreamValidation:
    """Tests for upstream stage validation."""

    def test_upstream_not_completed(
        self, job_repo, stage_repo, audit_repo,
        artifact_store, artifact_metadata_repo, uuid_generator,
        in_progress_job, parse_catalog_stage, generate_input_files_stage,
    ) -> None:
        """parse-catalog still PENDING → should raise."""
        job_repo.save(in_progress_job)
        stage_repo.save(parse_catalog_stage)
        stage_repo.save(generate_input_files_stage)

        uc = _build_use_case(
            job_repo, stage_repo, audit_repo,
            artifact_store, artifact_metadata_repo, uuid_generator,
        )
        with pytest.raises(UpstreamStageNotCompletedError):
            uc.execute(_make_command())

    def test_upstream_artifact_not_found(
        self, job_repo, stage_repo, audit_repo,
        artifact_store, artifact_metadata_repo, uuid_generator,
        in_progress_job, completed_parse_catalog_stage,
        generate_input_files_stage,
    ) -> None:
        """parse-catalog COMPLETED but no root-jsons artifact → should raise."""
        job_repo.save(in_progress_job)
        stage_repo.save(completed_parse_catalog_stage)
        stage_repo.save(generate_input_files_stage)

        uc = _build_use_case(
            job_repo, stage_repo, audit_repo,
            artifact_store, artifact_metadata_repo, uuid_generator,
        )
        with pytest.raises(ArtifactNotFoundError):
            uc.execute(_make_command())

        stage = stage_repo.find_by_job_and_name(
            JobId(VALID_JOB_ID), StageName(StageType.GENERATE_INPUT_FILES.value)
        )
        assert stage.stage_state == StageState.FAILED


class TestHappyPath:
    """Tests for successful generate-input-files execution."""

    def test_generates_and_stores_configs(
        self, job_repo, stage_repo, audit_repo,
        artifact_store, artifact_metadata_repo, uuid_generator,
        in_progress_job, completed_parse_catalog_stage,
        generate_input_files_stage, tmp_path,
    ) -> None:
        """Full happy path with mocked adapter policy engine."""
        job_repo.save(in_progress_job)
        stage_repo.save(completed_parse_catalog_stage)
        stage_repo.save(generate_input_files_stage)
        _seed_upstream_artifacts(
            artifact_store, artifact_metadata_repo, uuid_generator
        )

        # Mock the adapter policy engine to produce output files
        def mock_generate(input_dir, output_dir, policy_path, schema_path, **kwargs):
            # Create some output config files
            arch_dir = os.path.join(output_dir, "x86_64", "rhel", "9.5")
            os.makedirs(arch_dir, exist_ok=True)
            with open(os.path.join(arch_dir, "omnia_config.json"), "w") as f:
                json.dump({"config": "test"}, f)

        # Use a temp file as policy path
        policy_file = tmp_path / "policy.json"
        policy_file.write_text(json.dumps({"targets": {}}))
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(json.dumps({}))

        uc = _build_use_case(
            job_repo, stage_repo, audit_repo,
            artifact_store, artifact_metadata_repo, uuid_generator,
            default_policy_path=SafePath(policy_file),
            policy_schema_path=SafePath(schema_file),
        )

        with patch(
            "orchestrator.catalog.use_cases.generate_input_files"
            ".generate_configs_from_policy",
            side_effect=mock_generate,
        ):
            result = uc.execute(_make_command())

        assert result.stage_state == "COMPLETED"
        assert result.config_file_count == 0  # No longer tracking file count
        assert result.config_files == []  # No longer tracking file list

        # Stage should be COMPLETED
        stage = stage_repo.find_by_job_and_name(
            JobId(VALID_JOB_ID), StageName(StageType.GENERATE_INPUT_FILES.value)
        )
        assert stage.stage_state == StageState.COMPLETED

        # Artifact metadata should be saved
        record = artifact_metadata_repo.find_by_job_stage_and_label(
            job_id=JobId(VALID_JOB_ID),
            stage_name=StageName(StageType.GENERATE_INPUT_FILES.value),
            label="omnia-configs",
        )
        assert record is not None

    def test_stage_fails_on_config_generation_error(
        self, job_repo, stage_repo, audit_repo,
        artifact_store, artifact_metadata_repo, uuid_generator,
        in_progress_job, completed_parse_catalog_stage,
        generate_input_files_stage, tmp_path,
    ) -> None:
        """Config generation failure → stage FAILED."""
        job_repo.save(in_progress_job)
        stage_repo.save(completed_parse_catalog_stage)
        stage_repo.save(generate_input_files_stage)
        _seed_upstream_artifacts(
            artifact_store, artifact_metadata_repo, uuid_generator
        )

        policy_file = tmp_path / "policy.json"
        policy_file.write_text(json.dumps({"targets": {}}))
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(json.dumps({}))

        uc = _build_use_case(
            job_repo, stage_repo, audit_repo,
            artifact_store, artifact_metadata_repo, uuid_generator,
            default_policy_path=SafePath(policy_file),
            policy_schema_path=SafePath(schema_file),
        )

        # Mock generates no output files → ConfigGenerationError
        def mock_generate_empty(input_dir, output_dir, policy_path, schema_path, **kwargs):
            pass  # produces no files

        with patch(
            "orchestrator.catalog.use_cases.generate_input_files"
            ".generate_configs_from_policy",
            side_effect=mock_generate_empty,
        ):
            from core.catalog.exceptions import ConfigGenerationError
            with pytest.raises(ConfigGenerationError):
                uc.execute(_make_command())

        stage = stage_repo.find_by_job_and_name(
            JobId(VALID_JOB_ID), StageName(StageType.GENERATE_INPUT_FILES.value)
        )
        assert stage.stage_state == StageState.FAILED

    def test_audit_events_emitted(
        self, job_repo, stage_repo, audit_repo,
        artifact_store, artifact_metadata_repo, uuid_generator,
        in_progress_job, completed_parse_catalog_stage,
        generate_input_files_stage, tmp_path,
    ) -> None:
        """Audit events emitted on success."""
        job_repo.save(in_progress_job)
        stage_repo.save(completed_parse_catalog_stage)
        stage_repo.save(generate_input_files_stage)
        _seed_upstream_artifacts(
            artifact_store, artifact_metadata_repo, uuid_generator
        )

        def mock_generate(input_dir, output_dir, policy_path, schema_path, **kwargs):
            arch_dir = os.path.join(output_dir, "x86_64", "rhel", "9.5")
            os.makedirs(arch_dir, exist_ok=True)
            with open(os.path.join(arch_dir, "config.json"), "w") as f:
                json.dump({"config": "test"}, f)

        policy_file = tmp_path / "policy.json"
        policy_file.write_text(json.dumps({"targets": {}}))
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(json.dumps({}))

        uc = _build_use_case(
            job_repo, stage_repo, audit_repo,
            artifact_store, artifact_metadata_repo, uuid_generator,
            default_policy_path=SafePath(policy_file),
            policy_schema_path=SafePath(schema_file),
        )

        with patch(
            "orchestrator.catalog.use_cases.generate_input_files"
            ".generate_configs_from_policy",
            side_effect=mock_generate,
        ):
            uc.execute(_make_command())

        events = audit_repo.find_by_job(JobId(VALID_JOB_ID))
        event_types = [e.event_type for e in events]
        assert "STAGE_STARTED" in event_types
        assert "STAGE_COMPLETED" in event_types
