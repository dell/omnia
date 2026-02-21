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

"""Unit tests for PlaybookQueueResultService."""

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.localrepo.entities import PlaybookResult
from core.localrepo.repositories import PlaybookQueueResultRepository
from core.localrepo.services import PlaybookQueueResultService


class TestPlaybookQueueResultService:
    """Tests for PlaybookQueueResultService."""

    @pytest.fixture
    def mock_result_repo(self):
        """Mock result repository."""
        return MagicMock(spec=PlaybookQueueResultRepository)

    @pytest.fixture
    def result_service(self, mock_result_repo):
        """Create result service with mocked repository."""
        return PlaybookQueueResultService(mock_result_repo)

    @pytest.fixture
    def result_file_content(self):
        """Sample result file content."""
        return {
            "job_id": str(uuid.uuid4()),
            "stage_name": "create-local-repository",
            "request_id": str(uuid.uuid4()),
            "status": "success",
            "exit_code": 0,
            "duration_seconds": 30,
        }

    def test_poll_results_no_files(self, result_service, mock_result_repo):
        """Test polling when no result files exist."""
        callback = MagicMock()
        mock_result_repo.is_available.return_value = True
        mock_result_repo.get_unprocessed_results.return_value = []

        count = result_service.poll_results(callback=callback)

        assert count == 0
        callback.assert_not_called()
        mock_result_repo.get_unprocessed_results.assert_called_once()

    def test_poll_results_with_files(self, result_service, mock_result_repo, result_file_content):
        """Test polling with result files."""
        # Setup mock
        result_path1 = Path("/queue/result1.json")
        result_path2 = Path("/queue/result2.json")

        mock_result_repo.is_available.return_value = True
        mock_result_repo.get_unprocessed_results.return_value = [result_path1, result_path2]

        # Create mock results
        result1 = PlaybookResult(**result_file_content)
        result2 = PlaybookResult(**result_file_content)

        mock_result_repo.read_result.side_effect = [result1, result2]

        callback = MagicMock()

        count = result_service.poll_results(callback=callback)

        assert count == 2
        assert callback.call_count == 2
        callback.assert_any_call(result1)
        callback.assert_any_call(result2)
        mock_result_repo.archive_result.assert_any_call(result_path1)
        mock_result_repo.archive_result.assert_any_call(result_path2)

    def test_poll_results_repo_unavailable(self, result_service, mock_result_repo):
        """Test polling when repository is unavailable."""
        callback = MagicMock()
        mock_result_repo.is_available.return_value = False

        count = result_service.poll_results(callback=callback)

        assert count == 0
        callback.assert_not_called()
        mock_result_repo.get_unprocessed_results.assert_not_called()

    def test_poll_results_callback_exception(self, result_service, mock_result_repo, result_file_content):
        """Test polling when callback raises exception."""
        result_path = Path("/queue/result1.json")

        mock_result_repo.is_available.return_value = True
        mock_result_repo.get_unprocessed_results.return_value = [result_path]

        result = PlaybookResult(**result_file_content)
        mock_result_repo.read_result.return_value = result

        callback = MagicMock(side_effect=Exception("Callback error"))

        # Should not raise exception
        count = result_service.poll_results(callback=callback)

        assert count == 0  # No files processed due to error
        mock_result_repo.archive_result.assert_not_called()

    def test_poll_results_read_exception(self, result_service, mock_result_repo):
        """Test polling when reading result fails."""
        result_path = Path("/queue/result1.json")

        mock_result_repo.is_available.return_value = True
        mock_result_repo.get_unprocessed_results.return_value = [result_path]
        mock_result_repo.read_result.side_effect = Exception("Read error")

        callback = MagicMock()

        # Should not raise exception
        count = result_service.poll_results(callback=callback)

        assert count == 0  # No files processed due to error
        callback.assert_not_called()
        mock_result_repo.archive_result.assert_not_called()
