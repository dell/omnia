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

"""Unit tests for Local Repository entities."""

import pytest

from core.jobs.value_objects import CorrelationId, JobId
from core.localrepo.entities import (
    PlaybookRequest,
    PlaybookResult,
)
from core.localrepo.value_objects import (
    ExecutionTimeout,
    ExtraVars,
    PlaybookPath,
)


class TestPlaybookRequest:
    """Tests for PlaybookRequest entity."""

    def _make_request(self, **overrides):
        """Helper to create a PlaybookRequest with defaults."""
        defaults = {
            "job_id": "018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11",
            "stage_name": "create-local-repository",
            "playbook_path": PlaybookPath("local_repo.yml"),
            "extra_vars": ExtraVars(values={}),
            "correlation_id": "019bf590-1234-7890-abcd-ef1234567890",
            "timeout": ExecutionTimeout.default(),
            "submitted_at": "2026-02-05T14:30:00Z",
            "request_id": "req-001",
        }
        defaults.update(overrides)
        return PlaybookRequest(**defaults)

    def test_to_dict_contains_all_fields(self):
        """to_dict should contain all required fields."""
        request = self._make_request()
        data = request.to_dict()
        assert data["job_id"] == "018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"
        assert data["stage_name"] == "create-local-repository"
        assert data["playbook_path"] == "local_repo.yml"
        assert data["extra_vars"] == {}
        assert data["timeout_minutes"] == 30
        assert data["submitted_at"] == "2026-02-05T14:30:00Z"
        assert data["request_id"] == "req-001"

    def test_generate_filename_format(self):
        """Filename should follow naming convention."""
        request = self._make_request()
        filename = request.generate_filename()
        assert filename.startswith("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11")
        assert "create-local-repository" in filename
        assert filename.endswith(".json")

    def test_immutability(self):
        """PlaybookRequest should be immutable."""
        request = self._make_request()
        with pytest.raises(AttributeError):
            request.job_id = "other-id"


class TestPlaybookResult:
    """Tests for PlaybookResult entity."""

    def test_success_result(self):
        """Successful result should report is_success=True."""
        result = PlaybookResult(
            job_id="job-1",
            stage_name="create-local-repository",
            request_id="req-1",
            status="success",
            exit_code=0,
        )
        assert result.is_success is True
        assert result.is_failed is False

    def test_failed_result(self):
        """Failed result should report is_failed=True."""
        result = PlaybookResult(
            job_id="job-1",
            stage_name="create-local-repository",
            request_id="req-1",
            status="failed",
            exit_code=1,
            error_code="PLAYBOOK_FAILED",
            error_summary="Playbook failed",
        )
        assert result.is_success is False
        assert result.is_failed is True

    def test_from_dict_success(self):
        """from_dict should parse valid dictionary."""
        data = {
            "job_id": "job-1",
            "stage_name": "create-local-repository",
            "request_id": "req-1",
            "status": "success",
            "exit_code": 0,
            "stdout": "output",
            "stderr": "",
            "started_at": "2026-02-05T14:30:00Z",
            "completed_at": "2026-02-05T14:40:00Z",
            "duration_seconds": 600,
            "timestamp": "2026-02-05T14:40:00Z",
        }
        result = PlaybookResult.from_dict(data)
        assert result.job_id == "job-1"
        assert result.is_success is True
        assert result.duration_seconds == 600

    def test_from_dict_missing_required_field(self):
        """from_dict should raise KeyError for missing required fields."""
        data = {"stage_name": "create-local-repository", "status": "success"}
        with pytest.raises(KeyError):
            PlaybookResult.from_dict(data)

    def test_from_dict_with_optional_fields(self):
        """from_dict should handle missing optional fields gracefully."""
        data = {
            "job_id": "job-1",
            "stage_name": "create-local-repository",
            "status": "failed",
        }
        result = PlaybookResult.from_dict(data)
        assert result.exit_code == -1
        assert result.stdout == ""
        assert result.error_code is None

    def test_immutability(self):
        """PlaybookResult should be immutable."""
        result = PlaybookResult(
            job_id="job-1",
            stage_name="create-local-repository",
            request_id="req-1",
            status="success",
            exit_code=0,
        )
        with pytest.raises(AttributeError):
            result.status = "failed"
