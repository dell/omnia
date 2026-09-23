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

import shutil
from pathlib import Path

import pytest

from common.queue_auth import read_signed_payload, write_signed_payload
from common.queue_state import PendingRequestStore
from core.localrepo.entities import PlaybookRequest
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

KEY = b"q" * 32


@pytest.fixture(autouse=True)
def queue_auth_key(monkeypatch, tmp_path):
    """Provide the same protected key used by both queue adapters."""
    key_path = tmp_path / "queue-auth.key"
    key_path.write_bytes(KEY)
    key_path.chmod(0o600)
    monkeypatch.setenv("PLAYBOOK_QUEUE_AUTH_KEY_FILE", str(key_path))
    monkeypatch.setenv(
        "PLAYBOOK_QUEUE_API_STATE_DIR", str(tmp_path / "queue-state")
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
        data = read_signed_payload(file_path, KEY, purpose="request")
        assert data["job_id"] == "018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"
        assert data["stage_name"] == "create-local-repository"
        assert data["command_type"] == "ansible-playbook"
        assert len(list((tmp_path / "queue-state" / "pending").iterdir())) == 1

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
        data = dict(data)
        data.setdefault("request_id", f"request-{filename}")
        if data.get("job_id") and data.get("stage_name"):
            PendingRequestStore(KEY).register_request(data)
        file_path = results_dir / filename
        write_signed_payload(file_path, data, KEY, purpose="result")
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

        with pytest.raises(ValueError, match="Untrusted result"):
            repo.read_result(bad_file)

        repo.quarantine_result(bad_file)
        assert not bad_file.exists()
        assert len(list((tmp_path / "archive" / "rejected-results").iterdir())) == 1

    def test_read_result_rejects_tampered_signed_data(self, tmp_path):
        """A queue writer cannot alter a watcher-authenticated result."""
        repo = NfsPlaybookQueueResultRepository(
            queue_base_path=str(tmp_path)
        )
        repo.ensure_directories()

        result_path = self._write_result_file(
            tmp_path / "results",
            "tampered.json",
            {
                "job_id": "job-1",
                "stage_name": "deploy",
                "status": "failed",
            },
        )
        contents = result_path.read_text(encoding="utf-8")
        result_path.write_text(
            contents.replace('"failed"', '"success"'),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="Untrusted result"):
            repo.read_result(result_path)

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

        repo.read_result(file_path)
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
        repo.read_result(file_path)
        repo.archive_result(file_path)
        assert "result.json" in repo._processed_files

        repo.clear_processed_cache()
        assert len(repo._processed_files) == 0

    def test_archived_result_cannot_be_replayed_for_a_new_retry(self, tmp_path):
        """A stale signed result must not affect a later request attempt."""
        repo = NfsPlaybookQueueResultRepository(
            queue_base_path=str(tmp_path)
        )
        repo.ensure_directories()
        old_result_path = self._write_result_file(
            tmp_path / "results",
            "old.json",
            {
                "job_id": "job-1",
                "stage_name": "deploy",
                "request_id": "request-old",
                "status": "success",
            },
        )
        repo.read_result(old_result_path)
        repo.archive_result(old_result_path)

        PendingRequestStore(KEY).register_request(
            {
                "job_id": "job-1",
                "stage_name": "deploy",
                "request_id": "request-new",
            }
        )
        replay_path = tmp_path / "results" / "replayed.json"
        shutil.copy2(
            tmp_path / "archive" / "results" / "old.json",
            replay_path,
        )
        restarted_repo = NfsPlaybookQueueResultRepository(
            queue_base_path=str(tmp_path)
        )

        with pytest.raises(ValueError, match="already consumed"):
            restarted_repo.read_result(replay_path)


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
