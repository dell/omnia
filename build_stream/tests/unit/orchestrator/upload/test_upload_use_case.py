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

"""Unit tests for Upload Files Use Case - TDD Approach."""

import hashlib
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import pytest

from core.artifacts.entities import ArtifactRecord
from core.artifacts.value_objects import (
    ArtifactRef, ArtifactKind, StoreHint, ArtifactDigest
)
from core.jobs.entities import Job, Stage
from core.jobs.value_objects import (
    JobId, JobState, StageName, StageType, StageState, ClientId, CorrelationId
)
from core.jobs.exceptions import JobNotFoundError, TerminalStateViolationError

from orchestrator.upload.use_cases.upload_files import (
    UploadFilesUseCase,
    UploadFilesCommand,
    UploadFilesResult,
    FileChangeStatus,
)
from orchestrator.upload.exceptions import (
    InvalidFilenameError,
    FileSizeExceededError,
)


def _create_mock_upload_stage(job_id, state=StageState.PENDING):
    """Helper to create a mock upload stage."""
    stage = Mock(spec=Stage)
    stage.job_id = job_id
    stage.stage_name = StageName(StageType.UPLOAD.value)
    stage.stage_state = state
    
    # Mock start() to transition to IN_PROGRESS
    def mock_start():
        stage.stage_state = StageState.IN_PROGRESS
    stage.start = Mock(side_effect=mock_start)
    
    # Mock complete() to transition to COMPLETED
    def mock_complete():
        stage.stage_state = StageState.COMPLETED
    stage.complete = Mock(side_effect=mock_complete)

    # Mock reset() to transition back to PENDING (for retry after FAILED/COMPLETED)
    def mock_reset():
        stage.stage_state = StageState.PENDING
    stage.reset = Mock(side_effect=mock_reset)

    return stage


def _create_upload_command(job_id, files, client_id=None, correlation_id=None):
    """Helper to create UploadFilesCommand with default values."""
    if client_id is None:
        client_id = ClientId("test-client")
    if correlation_id is None:
        correlation_id = CorrelationId("018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10")  # Valid UUID

    return UploadFilesCommand(
        job_id=job_id,
        files=files,
        client_id=client_id,
        correlation_id=correlation_id,
    )


class TestUploadFilesValidation:
    """Test filename and file size validation."""

    def test_valid_yaml_filename_passes(self):
        """Valid YAML filename should pass validation."""
        use_case = self._create_use_case()

        # Should not raise
        use_case._validate_filename("network_spec.yml")

    def test_valid_csv_filename_passes(self):
        """Valid CSV filename should pass validation."""
        use_case = self._create_use_case()

        # Should not raise
        use_case._validate_filename("pxe_mapping_file.csv")

    def test_invalid_filename_raises_error(self):
        """Filename not in whitelist should raise InvalidFilenameError."""
        use_case = self._create_use_case()

        with pytest.raises(InvalidFilenameError) as exc_info:
            use_case._validate_filename("malicious.sh")

        assert "not in allowed whitelist" in str(exc_info.value)

    def test_path_traversal_filename_raises_error(self):
        """Path traversal attempt should raise InvalidFilenameError."""
        use_case = self._create_use_case()

        with pytest.raises(InvalidFilenameError) as exc_info:
            use_case._validate_filename("../etc/passwd")

        assert "not in allowed whitelist" in str(exc_info.value)

    def test_empty_filename_raises_error(self):
        """Empty filename should raise InvalidFilenameError."""
        use_case = self._create_use_case()

        with pytest.raises(InvalidFilenameError) as exc_info:
            use_case._validate_filename("")

        assert "not in allowed whitelist" in str(exc_info.value)

    def test_file_within_size_limit_passes(self):
        """File within size limit should pass validation."""
        use_case = self._create_use_case()
        content = b"x" * (1024 * 1024)  # 1 MB

        # Should not raise
        use_case._validate_file_size(content, "test.yml")

    def test_file_at_size_limit_passes(self):
        """File at exact size limit should pass validation."""
        use_case = self._create_use_case()
        content = b"x" * (5 * 1024 * 1024)  # 5 MB

        # Should not raise
        use_case._validate_file_size(content, "test.yml")

    def test_file_exceeds_size_limit_raises_error(self):
        """File exceeding size limit should raise FileSizeExceededError."""
        use_case = self._create_use_case()
        content = b"x" * (6 * 1024 * 1024)  # 6 MB

        with pytest.raises(FileSizeExceededError) as exc_info:
            use_case._validate_file_size(content, "test.yml")

        assert "exceeds maximum size" in str(exc_info.value)

    def test_zero_size_file_passes(self):
        """Zero-size file should pass validation (edge case)."""
        use_case = self._create_use_case()
        content = b""

        # Should not raise
        use_case._validate_file_size(content, "test.yml")

    def _create_use_case(self):
        """Create use case with mocked dependencies."""
        job_id = JobId("018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10")
        stage = _create_mock_upload_stage(job_id)

        stage_repo = Mock()
        stage_repo.find_by_job_and_name.return_value = stage

        return UploadFilesUseCase(
            job_repository=Mock(),
            stage_repository=stage_repo,
            audit_repository=Mock(),
            artifact_store=Mock(),
            artifact_metadata_repo=Mock(),
            uuid_generator=Mock(),
            config=Mock(artifact_store=Mock(max_file_size_bytes=5242880)),
        )


class TestUploadFilesJobValidation:
    """Test job state validation."""

    def test_job_not_found_raises_error(self):
        """Non-existent job should raise JobNotFoundError."""
        job_repo = Mock()
        job_repo.find_by_id.return_value = None

        use_case = UploadFilesUseCase(
            job_repository=job_repo,
            stage_repository=Mock(),
            audit_repository=Mock(),
            artifact_store=Mock(),
            artifact_metadata_repo=Mock(),
            uuid_generator=Mock(),
            config=Mock(),
        )

        command = _create_upload_command(
            job_id=JobId("018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"),
            files=[("test.yml", b"content")],
        )

        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_job_in_created_state_allows_upload(self):
        """Job in CREATED state should allow upload."""
        job = self._create_job(JobState.CREATED)
        use_case = self._create_use_case_with_job(job)

        command = _create_upload_command(
            job_id=job.id,
            files=[("network_spec.yml", b"content")],
        )

        # Should not raise
        result = use_case.execute(command)
        assert result is not None

    def test_job_in_completed_state_raises_error(self):
        """Job in COMPLETED state should raise TerminalStateViolationError."""
        job = self._create_job(JobState.COMPLETED)
        use_case = self._create_use_case_with_job(job)

        command = _create_upload_command(
            job_id=job.id,
            files=[("network_spec.yml", b"content")],
        )

        with pytest.raises(TerminalStateViolationError):
            use_case.execute(command)

    def test_job_in_cancelled_state_raises_error(self):
        """Job in CANCELLED state should raise TerminalStateViolationError."""
        job = self._create_job(JobState.CANCELLED)
        use_case = self._create_use_case_with_job(job)

        command = _create_upload_command(
            job_id=job.id,
            files=[("network_spec.yml", b"content")],
        )

        with pytest.raises(TerminalStateViolationError):
            use_case.execute(command)

    def test_job_in_failed_state_allows_upload(self):
        """Job in FAILED state should allow upload to support resume/retry."""
        job = self._create_job(JobState.FAILED)
        use_case = self._create_use_case_with_job(job)

        command = _create_upload_command(
            job_id=job.id,
            files=[("network_spec.yml", b"content")],
        )

        result = use_case.execute(command)
        assert result is not None

    def _create_job(self, status: JobState):
        """Create mock job with given status."""
        job = Mock(spec=Job)
        job.id = JobId("018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10")
        job.job_state = status

        # Setup the mock methods to return the correct boolean based on status
        is_terminal = status in [JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED]

        job.is_completed = Mock(return_value=status == JobState.COMPLETED)
        job.is_failed = Mock(return_value=status == JobState.FAILED)
        job.is_cancelled = Mock(return_value=status == JobState.CANCELLED)
        job.is_in_progress = Mock(return_value=status == JobState.IN_PROGRESS)

        # The use case uses JobHelper or checks these directly, let's update use case too
        # But for now, let's add a custom method to our mock that the use case can use
        job.is_in_terminal_state = Mock(return_value=is_terminal)

        return job

    def _create_use_case_with_job(self, job):
        """Create use case with mocked job repository."""
        job_repo = Mock()
        job_repo.find_by_id.return_value = job

        stage = _create_mock_upload_stage(job.id)
        stage_repo = Mock()
        stage_repo.find_by_job_and_name.return_value = stage

        artifact_store = Mock()
        metadata_repo = Mock()
        metadata_repo.find_by_job_stage_and_label.return_value = None

        return UploadFilesUseCase(
            job_repository=job_repo,
            stage_repository=stage_repo,
            audit_repository=Mock(),
            artifact_store=artifact_store,
            artifact_metadata_repo=metadata_repo,
            uuid_generator=Mock(),
            config=Mock(
                artifact_store=Mock(max_file_size_bytes=5242880),
                file_store=Mock(base_path="/tmp/artifacts"),
                paths=Mock(build_stream_base_path="/tmp/buildstream"),
            ),
        )


class TestUploadFilesChangeDetection:
    """Test change detection logic."""

    def test_first_upload_marked_as_changed(self):
        """First upload with no previous record should be marked CHANGED."""
        job = self._create_job()
        metadata_repo = Mock()
        metadata_repo.find_by_job_stage_and_label.return_value = None

        use_case = self._create_use_case(job, metadata_repo)

        command = _create_upload_command(
            job_id=job.id,
            files=[("network_spec.yml", b"content")],
        )

        result = use_case.execute(command)

        assert result.upload_summary.changed_files == 1
        assert result.upload_summary.unchanged_files == 0
        assert result.files[0].status == FileChangeStatus.CHANGED

    def test_same_content_reupload_marked_unchanged(self):
        """Re-uploading same content should be marked UNCHANGED."""
        job = self._create_job()
        content = b"test content"
        digest = hashlib.sha256(content).hexdigest()

        # Previous record with same digest
        previous_record = Mock(spec=ArtifactRecord)
        previous_record.artifact_ref = ArtifactRef(
            key="config-files/abc123/network_spec.yml.bin",
            digest=ArtifactDigest(digest),
            size_bytes=len(content),
            uri="file:///tmp/artifacts/config-files/abc123/network_spec.yml.bin",
        )

        metadata_repo = Mock()
        metadata_repo.find_by_job_stage_and_label.return_value = previous_record

        use_case = self._create_use_case(job, metadata_repo)

        command = _create_upload_command(
            job_id=job.id,
            files=[("network_spec.yml", content)],
        )

        result = use_case.execute(command)

        assert result.upload_summary.changed_files == 0
        assert result.upload_summary.unchanged_files == 1
        assert result.files[0].status == FileChangeStatus.UNCHANGED

    def test_modified_content_marked_changed(self):
        """Modified content should be marked CHANGED."""
        job = self._create_job()
        old_content = b"old content"
        new_content = b"new content"
        old_digest = hashlib.sha256(old_content).hexdigest()

        # Previous record with different digest
        previous_record = Mock(spec=ArtifactRecord)
        previous_record.artifact_ref = ArtifactRef(
            key="config-files/abc123/network_spec.yml.bin",
            digest=ArtifactDigest(old_digest),
            size_bytes=len(old_content),
            uri="file:///tmp/artifacts/config-files/abc123/network_spec.yml.bin",
        )

        metadata_repo = Mock()
        metadata_repo.find_by_job_stage_and_label.return_value = previous_record

        use_case = self._create_use_case(job, metadata_repo)

        command = _create_upload_command(
            job_id=job.id,
            files=[("network_spec.yml", new_content)],
        )

        result = use_case.execute(command)

        assert result.upload_summary.changed_files == 1
        assert result.upload_summary.unchanged_files == 0
        assert result.files[0].status == FileChangeStatus.CHANGED

    def _create_job(self):
        """Create mock job."""
        job = Mock(spec=Job)
        job.id = JobId("018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10")
        job.job_state = JobState.CREATED
        job.is_in_terminal_state = Mock(return_value=False)

        job.is_completed = Mock(return_value=False)
        job.is_failed = Mock(return_value=False)
        job.is_cancelled = Mock(return_value=False)

        return job

    def _create_use_case(self, job, metadata_repo):
        """Create use case with mocked dependencies."""
        job_repo = Mock()
        job_repo.find_by_id.return_value = job

        stage = _create_mock_upload_stage(job.id)
        stage_repo = Mock()
        stage_repo.find_by_job_and_name.return_value = stage

        artifact_store = Mock()
        artifact_store.store.return_value = ArtifactRef(
            key="config-files/abc123/test.yml.bin",
            digest=ArtifactDigest("a" * 64),
            size_bytes=100,
            uri="file:///tmp/test.yml.bin",
        )

        return UploadFilesUseCase(
            job_repository=job_repo,
            stage_repository=stage_repo,
            audit_repository=Mock(),
            artifact_store=artifact_store,
            artifact_metadata_repo=metadata_repo,
            uuid_generator=Mock(),
            config=Mock(
                artifact_store=Mock(max_file_size_bytes=5242880),
                file_store=Mock(base_path="/tmp/artifacts"),
                paths=Mock(build_stream_base_path="/tmp/buildstream"),
            ),
        )


class TestUploadFilesStorageIntegration:
    """Test storage integration."""

    def test_changed_file_stored_in_artifact_store(self):
        """Changed file should be stored in ArtifactStore."""
        job = self._create_job()
        artifact_store = Mock()
        metadata_repo = Mock()
        metadata_repo.find_by_job_stage_and_label.return_value = None

        use_case = self._create_use_case(job, artifact_store, metadata_repo)

        command = _create_upload_command(
            job_id=job.id,
            files=[("network_spec.yml", b"content")],
        )

        use_case.execute(command)

        # Verify ArtifactStore.store was called
        artifact_store.store.assert_called_once()
        call_args = artifact_store.store.call_args
        assert call_args[1]["kind"] == ArtifactKind.FILE
        assert call_args[1]["content"] == b"content"

    def test_unchanged_file_skips_artifact_store(self):
        """Unchanged file should skip ArtifactStore."""
        job = self._create_job()
        content = b"content"
        digest = hashlib.sha256(content).hexdigest()

        # Previous record with same digest
        previous_record = Mock(spec=ArtifactRecord)
        previous_record.artifact_ref = ArtifactRef(
            key="config-files/abc123/network_spec.yml.bin",
            digest=ArtifactDigest(digest),
            size_bytes=len(content),
            uri="file:///tmp/test.yml.bin",
        )

        artifact_store = Mock()
        metadata_repo = Mock()
        metadata_repo.find_by_job_stage_and_label.return_value = previous_record

        use_case = self._create_use_case(job, artifact_store, metadata_repo)

        command = _create_upload_command(
            job_id=job.id,
            files=[("network_spec.yml", content)],
        )

        use_case.execute(command)

        # Verify ArtifactStore.store was NOT called
        artifact_store.store.assert_not_called()

    def test_metadata_saved_for_changed_file(self):
        """Metadata should be saved for changed files."""
        job = self._create_job()
        artifact_store = Mock()
        artifact_store.store.return_value = ArtifactRef(
            key="config-files/abc123/test.yml.bin",
            digest=ArtifactDigest("a" * 64),
            size_bytes=100,
            uri="file:///tmp/test.yml.bin",
        )

        metadata_repo = Mock()
        metadata_repo.find_by_job_stage_and_label.return_value = None

        use_case = self._create_use_case(job, artifact_store, metadata_repo)

        command = _create_upload_command(
            job_id=job.id,
            files=[("network_spec.yml", b"content")],
        )

        use_case.execute(command)

        # Verify metadata was saved
        metadata_repo.save.assert_called_once()
        saved_record = metadata_repo.save.call_args[0][0]
        assert saved_record.job_id == job.id
        assert saved_record.label == "network_spec.yml"

    def _create_job(self):
        """Create mock job."""
        job = Mock(spec=Job)
        job.id = JobId("018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10")
        job.job_state = JobState.CREATED
        job.is_in_terminal_state = Mock(return_value=False)

        job.is_completed = Mock(return_value=False)
        job.is_failed = Mock(return_value=False)
        job.is_cancelled = Mock(return_value=False)

        return job

    def _create_use_case(self, job, artifact_store, metadata_repo):
        """Create use case with mocked dependencies."""
        job_repo = Mock()
        job_repo.find_by_id.return_value = job

        stage = _create_mock_upload_stage(job.id)
        stage_repo = Mock()
        stage_repo.find_by_job_and_name.return_value = stage

        return UploadFilesUseCase(
            job_repository=job_repo,
            stage_repository=stage_repo,
            audit_repository=Mock(),
            artifact_store=artifact_store,
            artifact_metadata_repo=metadata_repo,
            uuid_generator=Mock(),
            config=Mock(
                artifact_store=Mock(max_file_size_bytes=5242880),
                file_store=Mock(base_path="/tmp/artifacts"),
                paths=Mock(build_stream_base_path="/tmp/buildstream"),
            ),
        )


class TestUploadFilesMultiFileUpload:
    """Test multi-file upload scenarios."""

    def test_single_file_upload(self):
        """Single file upload should succeed."""
        job = self._create_job()
        use_case = self._create_use_case(job)

        command = _create_upload_command(
            job_id=job.id,
            files=[("network_spec.yml", b"content")],
        )

        result = use_case.execute(command)

        assert result.upload_summary.total_files == 1
        assert len(result.files) == 1

    def test_multiple_valid_files_upload(self):
        """Multiple valid files should all be uploaded."""
        job = self._create_job()
        use_case = self._create_use_case(job)

        command = _create_upload_command(
            job_id=job.id,
            files=[
                ("network_spec.yml", b"content1"),
                ("provision_config.yml", b"content2"),
                ("pxe_mapping_file.csv", b"content3"),
            ],
        )

        result = use_case.execute(command)

        assert result.upload_summary.total_files == 3
        assert len(result.files) == 3

    def test_mixed_valid_invalid_fails_fast(self):
        """Upload with any invalid file should fail immediately."""
        job = self._create_job()
        use_case = self._create_use_case(job)

        command = _create_upload_command(
            job_id=job.id,
            files=[
                ("network_spec.yml", b"content1"),
                ("malicious.sh", b"content2"),  # Invalid
            ],
        )

        with pytest.raises(InvalidFilenameError):
            use_case.execute(command)

    def test_partial_change_detection(self):
        """Upload with some changed and some unchanged files."""
        job = self._create_job()

        # Setup: file1 unchanged, file2 changed
        content1 = b"unchanged content"
        content2_old = b"old content"
        content2_new = b"new content"

        digest1 = hashlib.sha256(content1).hexdigest()
        digest2_old = hashlib.sha256(content2_old).hexdigest()

        metadata_repo = Mock()
        def find_by_label(job_id, stage_name, label):
            if label == "network_spec.yml":
                record = Mock(spec=ArtifactRecord)
                record.artifact_ref = ArtifactRef(
                    key="config-files/abc/network_spec.yml.bin",
                    digest=ArtifactDigest(digest1),
                    size_bytes=len(content1),
                    uri="file:///tmp/test.bin",
                )
                return record
            elif label == "provision_config.yml":
                record = Mock(spec=ArtifactRecord)
                record.artifact_ref = ArtifactRef(
                    key="config-files/def/provision_config.yml.bin",
                    digest=ArtifactDigest(digest2_old),
                    size_bytes=len(content2_old),
                    uri="file:///tmp/test2.bin",
                )
                return record
            return None

        metadata_repo.find_by_job_stage_and_label.side_effect = find_by_label

        use_case = self._create_use_case(job, metadata_repo)

        command = _create_upload_command(
            job_id=job.id,
            files=[
                ("network_spec.yml", content1),
                ("provision_config.yml", content2_new),
            ],
        )

        result = use_case.execute(command)

        assert result.upload_summary.total_files == 2
        assert result.upload_summary.changed_files == 1
        assert result.upload_summary.unchanged_files == 1

    def _create_job(self):
        """Create mock job."""
        job = Mock(spec=Job)
        job.id = JobId("018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10")
        job.job_state = JobState.CREATED
        job.is_in_terminal_state = Mock(return_value=False)

        job.is_completed = Mock(return_value=False)
        job.is_failed = Mock(return_value=False)
        job.is_cancelled = Mock(return_value=False)

        return job

    def _create_use_case(self, job, metadata_repo=None):
        """Create use case with mocked dependencies."""
        job_repo = Mock()
        job_repo.find_by_id.return_value = job

        stage = _create_mock_upload_stage(job.id)
        stage_repo = Mock()
        stage_repo.find_by_job_and_name.return_value = stage

        artifact_store = Mock()
        artifact_store.store.return_value = ArtifactRef(
            key="config-files/abc123/test.yml.bin",
            digest=ArtifactDigest("a" * 64),
            size_bytes=100,
            uri="file:///tmp/test.yml.bin",
        )

        if metadata_repo is None:
            metadata_repo = Mock()
            metadata_repo.find_by_job_stage_and_label.return_value = None

        return UploadFilesUseCase(
            job_repository=job_repo,
            stage_repository=stage_repo,
            audit_repository=Mock(),
            artifact_store=artifact_store,
            artifact_metadata_repo=metadata_repo,
            uuid_generator=Mock(),
            config=Mock(
                artifact_store=Mock(max_file_size_bytes=5242880),
                file_store=Mock(base_path="/tmp/artifacts"),
                paths=Mock(build_stream_base_path="/tmp/buildstream"),
            ),
        )


class TestUploadFilesAuditEvents:
    """Test audit event emission with file details."""

    def test_stage_started_audit_event_includes_filenames(self):
        """STAGE_STARTED audit event should include list of filenames."""
        job = self._create_job()
        audit_repo = Mock()
        use_case = self._create_use_case(job, audit_repo=audit_repo)

        command = _create_upload_command(
            job.id,
            [("network_spec.yml", b"content1"), ("pxe_mapping_file.csv", b"content2")]
        )

        use_case.execute(command)

        # Find STAGE_STARTED audit event
        started_calls = [
            call for call in audit_repo.save.call_args_list
            if call[0][0].event_type == "STAGE_STARTED"
        ]
        assert len(started_calls) == 1

        started_event = started_calls[0][0][0]
        assert started_event.details["stage_name"] == "upload"
        assert started_event.details["files"] == ["network_spec.yml", "pxe_mapping_file.csv"]
        assert started_event.details["file_count"] == 2

    def test_stage_completed_audit_event_includes_file_details(self):
        """STAGE_COMPLETED audit event should include file details and counts."""
        job = self._create_job()
        audit_repo = Mock()

        # Setup metadata repo to simulate one file unchanged
        metadata_repo = Mock()
        metadata_repo.find_by_job_stage_and_label.side_effect = [
            None,  # First file not found (will be CHANGED)
            Mock(  # Second file found with same digest (will be UNCHANGED)
                artifact_ref=ArtifactRef(
                    key="test",
                    digest=ArtifactDigest(hashlib.sha256(b"content2").hexdigest()),
                    size_bytes=8,
                    uri="file:///tmp/test",
                )
            ),
        ]

        use_case = self._create_use_case(job, audit_repo=audit_repo, metadata_repo=metadata_repo)

        command = _create_upload_command(
            job.id,
            [("network_spec.yml", b"content1"), ("pxe_mapping_file.csv", b"content2")]
        )

        use_case.execute(command)

        # Find STAGE_COMPLETED audit event
        completed_calls = [
            call for call in audit_repo.save.call_args_list
            if call[0][0].event_type == "STAGE_COMPLETED"
        ]
        assert len(completed_calls) == 1

        completed_event = completed_calls[0][0][0]
        assert completed_event.details["stage_name"] == "upload"
        assert completed_event.details["total_files"] == 2
        assert completed_event.details["changed_files"] == 1
        assert completed_event.details["unchanged_files"] == 1

        # Check file details
        file_details = completed_event.details["files"]
        assert len(file_details) == 2

        # First file should be CHANGED
        assert file_details[0]["filename"] == "network_spec.yml"
        assert file_details[0]["status"] == "CHANGED"
        assert file_details[0]["size_bytes"] == 8

        # Second file should be UNCHANGED
        assert file_details[1]["filename"] == "pxe_mapping_file.csv"
        assert file_details[1]["status"] == "UNCHANGED"
        assert file_details[1]["size_bytes"] == 8

    def test_upload_allowed_when_stage_already_completed(self):
        """Upload should succeed even when stage is already COMPLETED (reset + redo)."""
        job = self._create_job()
        audit_repo = Mock()

        # Create stage in COMPLETED state — will be reset() then start()/complete()
        stage = _create_mock_upload_stage(job.id, state=StageState.COMPLETED)
        stage_repo = Mock()
        stage_repo.find_by_job_and_name.return_value = stage

        # Create use case with completed stage
        job_repo = Mock()
        job_repo.find_by_id.return_value = job

        artifact_store = Mock()
        artifact_store.store.return_value = ArtifactRef(
            key="config-files/abc123/test.yml.bin",
            digest=ArtifactDigest("a" * 64),
            size_bytes=100,
            uri="file:///tmp/test.yml.bin",
        )

        metadata_repo = Mock()
        metadata_repo.find_by_job_stage_and_label.return_value = None

        use_case = UploadFilesUseCase(
            job_repository=job_repo,
            stage_repository=stage_repo,
            audit_repository=audit_repo,
            artifact_store=artifact_store,
            artifact_metadata_repo=metadata_repo,
            uuid_generator=Mock(),
            config=Mock(
                artifact_store=Mock(max_file_size_bytes=5242880),
                file_store=Mock(base_path="/tmp/artifacts"),
                paths=Mock(build_stream_base_path="/tmp/buildstream"),
            ),
        )

        command = _create_upload_command(
            job.id,
            [("network_spec.yml", b"content1")]
        )

        # Should not raise TerminalStateViolationError
        result = use_case.execute(command)

        # Verify upload succeeded
        assert result.upload_summary.total_files == 1
        assert result.upload_summary.changed_files == 1

        # Verify stage.reset() was called (stage was COMPLETED, reset for retry)
        stage.reset.assert_called_once()

        # Verify stage.start() and complete() were called after reset
        stage.start.assert_called_once()
        stage.complete.assert_called_once()

        # Verify STAGE_COMPLETED audit event was emitted
        completed_calls = [
            call for call in audit_repo.save.call_args_list
            if call[0][0].event_type == "STAGE_COMPLETED"
        ]
        assert len(completed_calls) == 1

        completed_event = completed_calls[0][0][0]
        assert completed_event.details["stage_name"] == "upload"
        assert completed_event.details["total_files"] == 1
        assert completed_event.details["changed_files"] == 1
        assert completed_event.details["unchanged_files"] == 0
        assert len(completed_event.details["files"]) == 1
        assert completed_event.details["files"][0]["filename"] == "network_spec.yml"
        assert completed_event.details["files"][0]["status"] == "CHANGED"


    def _create_job(self):
        """Create mock job."""
        job = Mock(spec=Job)
        job.id = JobId("018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10")
        job.job_state = JobState.CREATED
        job.is_in_terminal_state = Mock(return_value=False)

        job.is_completed = Mock(return_value=False)
        job.is_failed = Mock(return_value=False)
        job.is_cancelled = Mock(return_value=False)

        return job

    def _create_use_case(self, job, audit_repo=None, metadata_repo=None):
        """Create use case with mocked dependencies."""
        job_repo = Mock()
        job_repo.find_by_id.return_value = job

        stage = _create_mock_upload_stage(job.id)
        stage_repo = Mock()
        stage_repo.find_by_job_and_name.return_value = stage

        artifact_store = Mock()
        artifact_store.store.return_value = ArtifactRef(
            key="config-files/abc123/test.yml.bin",
            digest=ArtifactDigest("a" * 64),
            size_bytes=100,
            uri="file:///tmp/test.yml.bin",
        )

        if audit_repo is None:
            audit_repo = Mock()

        if metadata_repo is None:
            metadata_repo = Mock()
            metadata_repo.find_by_job_stage_and_label.return_value = None

        return UploadFilesUseCase(
            job_repository=job_repo,
            stage_repository=stage_repo,
            audit_repository=audit_repo,
            artifact_store=artifact_store,
            artifact_metadata_repo=metadata_repo,
            uuid_generator=Mock(),
            config=Mock(
                artifact_store=Mock(max_file_size_bytes=5242880),
                file_store=Mock(base_path="/tmp/artifacts"),
                paths=Mock(build_stream_base_path="/tmp/buildstream"),
            ),
        )


