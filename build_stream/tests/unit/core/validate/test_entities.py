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

"""Unit tests for Validate domain entities."""

import uuid
from unittest.mock import patch

from core.validate.entities import ValidateRequest


def _make_request(**overrides):
    """Create a ValidateRequest with sensible defaults."""
    defaults = {
        "request_id": f"validate_{uuid.uuid4()}_20260217_103000",
        "job_id": str(uuid.uuid4()),
        "stage_type": "validate",
        "command_type": "test_automation",
        "scenario_names": ["all"],
        "test_suite": "",
        "timeout_minutes": 120,
        "artifact_dir": "/opt/omnia/build_stream_root/artifacts/test-job/validate/attempt_1",
        "config_path": "/opt/omnia/automation/omnia_test_config.yml",
        "correlation_id": str(uuid.uuid4()),
        "submitted_at": "2026-02-17T10:30:00Z",
        "attempt": 1,
    }
    defaults.update(overrides)
    return ValidateRequest(**defaults)


class TestValidateRequest:
    """Tests for ValidateRequest entity."""

    def test_create_valid_request(self):
        """Valid request should be created successfully."""
        request = _make_request()
        assert request.stage_type == "validate"
        assert request.command_type == "test_automation"
        assert request.scenario_names == ["all"]
        assert request.timeout_minutes == 120

    def test_create_with_custom_scenarios(self):
        """Request with specific scenarios should be created."""
        request = _make_request(scenario_names=["discovery", "slurm"])
        assert request.scenario_names == ["discovery", "slurm"]

    def test_create_with_test_suite(self):
        """Request with test_suite filter should be created."""
        request = _make_request(test_suite="smoke")
        assert request.test_suite == "smoke"

    def test_immutability(self):
        """Request should be immutable (frozen dataclass)."""
        request = _make_request()
        try:
            request.job_id = "new-id"
            assert False, "Should have raised AttributeError"
        except AttributeError:
            pass

    def test_to_dict(self):
        """to_dict should serialize all fields correctly per spec §7.4."""
        job_id = str(uuid.uuid4())
        corr_id = str(uuid.uuid4())
        req_id = f"validate_{job_id}_20260217_103000"
        request = _make_request(
            request_id=req_id,
            job_id=job_id,
            correlation_id=corr_id,
            scenario_names=["discovery"],
            test_suite="smoke",
            timeout_minutes=60,
            attempt=2,
        )
        result = request.to_dict()

        assert result["request_id"] == req_id
        assert result["job_id"] == job_id
        assert result["stage_type"] == "validate"
        assert result["command_type"] == "test_automation"
        assert result["scenario_names"] == ["discovery"]
        assert result["test_suite"] == "smoke"
        assert result["timeout_minutes"] == 60
        assert result["correlation_id"] == corr_id
        assert result["submitted_at"] == "2026-02-17T10:30:00Z"
        assert result["attempt"] == 2
        assert result["artifact_dir"].endswith("attempt_1")
        assert result["config_path"] == "/opt/omnia/automation/omnia_test_config.yml"

    def test_to_dict_has_all_required_nfs_fields(self):
        """to_dict must include all NFS queue request fields per spec §7.4."""
        request = _make_request()
        result = request.to_dict()
        required_keys = [
            "request_id", "job_id", "stage_type", "command_type",
            "scenario_names", "test_suite", "timeout_minutes",
            "artifact_dir", "config_path", "correlation_id",
        ]
        for key in required_keys:
            assert key in result, f"Missing required NFS field: {key}"

    def test_generate_filename(self):
        """generate_filename should follow {job_id}_{stage_type}_{timestamp}.json convention."""
        job_id = "test-job-id"
        request = _make_request(job_id=job_id)

        with patch("core.validate.entities.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "20260217_103000"
            from datetime import timezone
            mock_dt.timezone = timezone
            filename = request.generate_filename()

        assert filename.startswith("test-job-id_validate_")
        assert filename.endswith(".json")

    def test_default_scenario_names(self):
        """Default scenario_names should be ['all']."""
        request = ValidateRequest(
            request_id="test",
            job_id="test-job",
            stage_type="validate",
            command_type="test_automation",
        )
        assert request.scenario_names == ["all"]

    def test_default_timeout(self):
        """Default timeout should be 120 minutes."""
        request = ValidateRequest(
            request_id="test",
            job_id="test-job",
            stage_type="validate",
            command_type="test_automation",
        )
        assert request.timeout_minutes == 120
