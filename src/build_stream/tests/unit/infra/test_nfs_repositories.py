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

"""Unit tests for NFS repository implementations."""

import json
from pathlib import Path

import pytest

from core.localrepo.entities import PlaybookRequest, PlaybookResult
from core.localrepo.exceptions import QueueUnavailableError
from core.localrepo.value_objects import (
    ExecutionTimeout,
    ExtraVars,
    PlaybookPath,
)
from infra.repositories.nfs_input_repository import (
    NfsInputRepository,
)
from infra.repositories.nfs_playbook_queue_request_repository import (
    NfsPlaybookQueueRequestRepository,
)
from infra.repositories.nfs_playbook_queue_result_repository import (
    NfsPlaybookQueueResultRepository,
)


class TestNfsPlaybookQueueRequestRepository:
    """Tests for NfsPlaybookQueueRequestRepository."""

    def _make_request(self):
        """Helper to create a PlaybookRequest."""
        return PlaybookRequest(
            job_id="018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11",
            stage_name="create-local-repository",
            playbook_path=PlaybookPath("local_repo.yml"),
            extra_vars=ExtraVars(values={}),
            correlation_id="019bf590-1234-7890-abcd-ef1234567890",
            timeout=ExecutionTimeout.default(),
            submitted_at="2026-02-05T14:30:00Z",
            request_id="req-001",
        )

    def test_write_request_creates_file(self, tmp_path):
        """write_request should create a JSON file in requests dir."""
        repo = NfsPlaybookQueueRequestRepository(
            queue_base_path=str(tmp_path)
        )
        repo.ensure_directories()

        request = self._make_request()
        file_path = repo.write_request(request)

        assert file_path.exists()
        with open(file_path, "r", encoding="utf-8") as fobj:
            data = json.load(fobj)
        assert data["job_id"] == "018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"
        assert data["stage_name"] == "create-local-repository"

    def test_is_available_true(self, tmp_path):
        """is_available should return True when directory exists."""
        repo = NfsPlaybookQueueRequestRepository(
            queue_base_path=str(tmp_path)
        )
        repo.ensure_directories()
        assert repo.is_available() is True

    def test_is_available_false(self):
        """is_available should return False when directory missing."""
        repo = NfsPlaybookQueueRequestRepository(
            queue_base_path="/nonexistent/path"
        )
        assert repo.is_available() is False

    def test_write_request_unavailable_raises(self):
        """write_request on unavailable queue should raise."""
        repo = NfsPlaybookQueueRequestRepository(
            queue_base_path="/nonexistent/path"
        )
        with pytest.raises(QueueUnavailableError):
            repo.write_request(self._make_request())

    def test_file_permissions(self, tmp_path):
        """Written file should have restricted permissions."""
        import os
        import stat

        repo = NfsPlaybookQueueRequestRepository(
            queue_base_path=str(tmp_path)
        )
        repo.ensure_directories()

        file_path = repo.write_request(self._make_request())
        mode = os.stat(file_path).st_mode
        assert mode & stat.S_IRUSR  # owner read
        assert mode & stat.S_IWUSR  # owner write
        assert not (mode & stat.S_IROTH)  # no other read


class TestNfsPlaybookQueueResultRepository:
    """Tests for NfsPlaybookQueueResultRepository."""

    def _write_result_file(self, results_dir, filename, data):
        """Helper to write a result JSON file."""
        file_path = results_dir / filename
        with open(file_path, "w", encoding="utf-8") as fobj:
            json.dump(data, fobj)
        return file_path

    def test_get_unprocessed_results(self, tmp_path):
        """Should return list of unprocessed result files."""
        repo = NfsPlaybookQueueResultRepository(
            queue_base_path=str(tmp_path)
        )
        repo.ensure_directories()

        results_dir = tmp_path / "results"
        self._write_result_file(
            results_dir,
            "job1_create-local-repository_20260205.json",
            {"job_id": "job-1", "stage_name": "create-local-repository", "status": "success"},
        )

        files = repo.get_unprocessed_results()
        assert len(files) == 1

    def test_read_result_valid(self, tmp_path):
        """Should parse valid result file."""
        repo = NfsPlaybookQueueResultRepository(
            queue_base_path=str(tmp_path)
        )
        repo.ensure_directories()

        results_dir = tmp_path / "results"
        file_path = self._write_result_file(
            results_dir,
            "result.json",
            {
                "job_id": "job-1",
                "stage_name": "create-local-repository",
                "status": "success",
                "exit_code": 0,
            },
        )

        result = repo.read_result(file_path)
        assert result.job_id == "job-1"
        assert result.is_success is True

    def test_read_result_invalid_json(self, tmp_path):
        """Should raise ValueError for invalid JSON."""
        repo = NfsPlaybookQueueResultRepository(
            queue_base_path=str(tmp_path)
        )
        repo.ensure_directories()

        results_dir = tmp_path / "results"
        bad_file = results_dir / "bad.json"
        bad_file.write_text("not json")

        with pytest.raises(ValueError, match="Invalid JSON"):
            repo.read_result(bad_file)

    def test_read_result_missing_fields(self, tmp_path):
        """Should raise ValueError for missing required fields."""
        repo = NfsPlaybookQueueResultRepository(
            queue_base_path=str(tmp_path)
        )
        repo.ensure_directories()

        results_dir = tmp_path / "results"
        file_path = self._write_result_file(
            results_dir,
            "incomplete.json",
            {"stage_name": "create-local-repository"},
        )

        with pytest.raises(ValueError, match="missing required fields"):
            repo.read_result(file_path)

    def test_archive_result(self, tmp_path):
        """Should move result file to archive directory."""
        repo = NfsPlaybookQueueResultRepository(
            queue_base_path=str(tmp_path)
        )
        repo.ensure_directories()

        results_dir = tmp_path / "results"
        file_path = self._write_result_file(
            results_dir,
            "result.json",
            {"job_id": "job-1", "stage_name": "test", "status": "success"},
        )

        repo.archive_result(file_path)

        assert not file_path.exists()
        archive_path = tmp_path / "archive" / "results" / "result.json"
        assert archive_path.exists()

    def test_is_available_true(self, tmp_path):
        """is_available should return True when directory exists."""
        repo = NfsPlaybookQueueResultRepository(
            queue_base_path=str(tmp_path)
        )
        repo.ensure_directories()
        assert repo.is_available() is True

    def test_is_available_false(self):
        """is_available should return False when directory missing."""
        repo = NfsPlaybookQueueResultRepository(
            queue_base_path="/nonexistent/path"
        )
        assert repo.is_available() is False

    def test_clear_processed_cache(self, tmp_path):
        """clear_processed_cache should reset the in-memory set."""
        repo = NfsPlaybookQueueResultRepository(
            queue_base_path=str(tmp_path)
        )
        repo.ensure_directories()

        results_dir = tmp_path / "results"
        file_path = self._write_result_file(
            results_dir,
            "result.json",
            {"job_id": "job-1", "stage_name": "test", "status": "success"},
        )
        repo.archive_result(file_path)
        assert "result.json" in repo._processed_files

        repo.clear_processed_cache()
        assert len(repo._processed_files) == 0


class TestNfsInputRepository:
    """Tests for NfsInputRepository."""

    def test_get_source_path(self):
        """Should return correct source path for job."""
        repo = NfsInputRepository(
            build_stream_base="/opt/omnia/build_stream"
        )
        path = repo.get_source_input_repository_path("job-123")
        assert path == Path("/opt/omnia/build_stream/job-123/input")

    def test_get_destination_path(self):
        """Should return correct destination path."""
        repo = NfsInputRepository(
            playbook_input_dir="/opt/omnia/input/project_build_stream"
        )
        path = repo.get_destination_input_repository_path()
        assert path == Path("/opt/omnia/input/project_build_stream")

    def test_validate_existing_directory(self, tmp_path):
        """Should return True for directory with files."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "config.json").write_text("{}")

        repo = NfsInputRepository(
            build_stream_base=str(tmp_path)
        )
        assert repo.validate_input_directory(input_dir) is True

    def test_validate_nonexistent_directory(self):
        """Should return False for nonexistent directory."""
        repo = NfsInputRepository()
        assert repo.validate_input_directory(Path("/nonexistent")) is False

    def test_validate_empty_directory(self, tmp_path):
        """Should return False for empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        repo = NfsInputRepository()
        assert repo.validate_input_directory(empty_dir) is False
