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

"""Unit tests for ValidateImageOnTest domain entities."""

import uuid
from unittest.mock import patch

from core.localrepo.value_objects import ExecutionTimeout, ExtraVars, PlaybookPath
from core.validate.entities import ValidateImageOnTestRequest


def _make_request(**overrides):
    """Create a ValidateImageOnTestRequest with sensible defaults."""
    defaults = {
        "job_id": str(uuid.uuid4()),
        "stage_name": "validate-image-on-test",
        "playbook_path": PlaybookPath("discovery.yml"),
        "extra_vars": ExtraVars({"job_id": str(uuid.uuid4())}),
        "correlation_id": str(uuid.uuid4()),
        "timeout": ExecutionTimeout(60),
        "submitted_at": "2026-02-17T10:30:00Z",
        "request_id": str(uuid.uuid4()),
    }
    defaults.update(overrides)
    return ValidateImageOnTestRequest(**defaults)


class TestValidateImageOnTestRequest:
    """Tests for ValidateImageOnTestRequest entity."""

    def test_create_valid_request(self):
        """Valid request should be created successfully."""
        request = _make_request()
        assert request.stage_name == "validate-image-on-test"
        assert str(request.playbook_path) == "discovery.yml"

    def test_immutability(self):
        """Request should be immutable (frozen dataclass)."""
        request = _make_request()
        try:
            request.job_id = "new-id"
            assert False, "Should have raised AttributeError"
        except AttributeError:
            pass

    def test_to_dict(self):
        """to_dict should serialize all fields correctly."""
        job_id = str(uuid.uuid4())
        corr_id = str(uuid.uuid4())
        req_id = str(uuid.uuid4())
        request = _make_request(
            job_id=job_id,
            correlation_id=corr_id,
            request_id=req_id,
        )
        result = request.to_dict()

        assert result["job_id"] == job_id
        assert result["stage_name"] == "validate-image-on-test"
        assert result["playbook_path"] == "discovery.yml"
        assert result["correlation_id"] == corr_id
        assert result["timeout_minutes"] == 60
        assert result["submitted_at"] == "2026-02-17T10:30:00Z"
        assert result["request_id"] == req_id
        assert isinstance(result["extra_vars"], dict)

    def test_generate_filename(self):
        """generate_filename should follow naming convention."""
        job_id = "test-job-id"
        request = _make_request(job_id=job_id)

        with patch("core.validate.entities.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "20260217_103000"
            mock_dt.now.return_value.isoformat.return_value = "2026-02-17T10:30:00+00:00"
            from datetime import timezone
            mock_dt.timezone = timezone
            filename = request.generate_filename()

        assert filename.startswith("test-job-id_validate-image-on-test_")
        assert filename.endswith(".json")
