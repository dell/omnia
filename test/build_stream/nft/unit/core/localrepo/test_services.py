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

"""Unit tests for Local Repository services."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.localrepo.entities import PlaybookRequest, PlaybookResult
from core.localrepo.exceptions import (
    InputFilesMissingError,
    QueueUnavailableError,
)
from core.localrepo.services import (
    InputFileService,
    PlaybookQueueRequestService,
    PlaybookQueueResultService,
)
from core.localrepo.value_objects import (
    ExecutionTimeout,
    ExtraVars,
    PlaybookPath,
)


class TestInputFileService:
    """Tests for InputFileService."""

    def _make_service(self, input_repo=None):
        """Create InputFileService with mock or provided repo."""
        if input_repo is None:
            input_repo = MagicMock()
        return InputFileService(input_repo=input_repo)

    def test_prepare_success(self, tmp_path):
        """Successful validation of domain input directory returns True.

        Omnia 2.3+: prepare_playbook_input only validates that the
        destination input directory exists — no file copying.
        """
        dest = tmp_path / "dest"
        dest.mkdir()
        (dest / "repo_manager_config.yml").write_text("repo_config: partial")

        repo = MagicMock()
        repo.get_destination_input_repository_path.return_value = dest
        repo.validate_input_directory.return_value = True

        service = self._make_service(input_repo=repo)
        result = service.prepare_playbook_input(job_id="job-1")

        assert result is True

    def test_prepare_missing_input_raises(self):
        """Missing domain input directory should raise InputFilesMissingError."""
        repo = MagicMock()
        repo.get_destination_input_repository_path.return_value = Path("/nonexistent")
        repo.validate_input_directory.return_value = False

        service = self._make_service(input_repo=repo)

        with pytest.raises(InputFilesMissingError):
            service.prepare_playbook_input(job_id="job-1")

    def test_prepare_validates_destination_only(self, tmp_path):
        """Omnia 2.3+: only validates destination, does not copy files."""
        dest = tmp_path / "dest"
        dest.mkdir()
        (dest / "repo_manager_config.yml").write_text("repo_config: partial")

        repo = MagicMock()
        repo.get_destination_input_repository_path.return_value = dest
        repo.validate_input_directory.return_value = True

        service = self._make_service(input_repo=repo)
        result = service.prepare_playbook_input(job_id="job-1")

        assert result is True
        # get_source_input_repository_path should NOT be called
        repo.get_source_input_repository_path.assert_not_called()


class TestPlaybookQueueRequestService:
    """Tests for PlaybookQueueRequestService."""

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

    def test_submit_request_success(self):
        """Successful submission should return file path."""
        repo = MagicMock()
        repo.is_available.return_value = True
        repo.write_request.return_value = Path("/queue/requests/test.json")

        service = PlaybookQueueRequestService(request_repo=repo)
        result = service.submit_request(self._make_request())

        assert result == Path("/queue/requests/test.json")
        repo.write_request.assert_called_once()

    def test_submit_request_queue_unavailable(self):
        """Unavailable queue should raise QueueUnavailableError."""
        repo = MagicMock()
        repo.is_available.return_value = False

        service = PlaybookQueueRequestService(request_repo=repo)

        with pytest.raises(QueueUnavailableError):
            service.submit_request(self._make_request())


class TestPlaybookQueueResultService:
    """Tests for PlaybookQueueResultService."""

    def test_poll_results_processes_files(self):
        """Should process available result files and invoke callback."""
        result = PlaybookResult(
            job_id="job-1",
            stage_name="create-local-repository",
            request_id="req-1",
            status="success",
            exit_code=0,
        )

        repo = MagicMock()
        repo.is_available.return_value = True
        repo.get_unprocessed_results.return_value = [Path("/results/r1.json")]
        repo.read_result.return_value = result

        callback = MagicMock()
        service = PlaybookQueueResultService(result_repo=repo)
        count = service.poll_results(callback=callback)

        assert count == 1
        callback.assert_called_once_with(result)
        repo.archive_result.assert_called_once()

    def test_poll_results_queue_unavailable(self):
        """Unavailable queue should return 0 processed."""
        repo = MagicMock()
        repo.is_available.return_value = False

        service = PlaybookQueueResultService(result_repo=repo)
        count = service.poll_results(callback=MagicMock())

        assert count == 0

    def test_poll_results_handles_parse_error(self):
        """Parse errors should be logged and skipped."""
        repo = MagicMock()
        repo.is_available.return_value = True
        repo.get_unprocessed_results.return_value = [Path("/results/bad.json")]
        repo.read_result.side_effect = ValueError("bad json")

        callback = MagicMock()
        service = PlaybookQueueResultService(result_repo=repo)
        count = service.poll_results(callback=callback)

        assert count == 0
        callback.assert_not_called()
        repo.archive_result.assert_not_called()

    def test_poll_results_empty_queue(self):
        """Empty queue should return 0 processed."""
        repo = MagicMock()
        repo.is_available.return_value = True
        repo.get_unprocessed_results.return_value = []

        service = PlaybookQueueResultService(result_repo=repo)
        count = service.poll_results(callback=MagicMock())

        assert count == 0
