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

"""Unit tests for Deploy domain entities."""

import uuid
from unittest.mock import patch

from core.deploy.entities import DeployPlaybookRequest
from core.localrepo.value_objects import ExecutionTimeout, ExtraVars, PlaybookPath


def _make_request(**overrides):
    """Create a DeployPlaybookRequest with sensible defaults."""
    defaults = {
        "job_id": str(uuid.uuid4()),
        "stage_name": "deploy",
        "playbook_path": PlaybookPath("provision.yml"),
        "extra_vars": ExtraVars({"job_id": "test-job", "image_group_id": "test-cluster"}),
        "correlation_id": str(uuid.uuid4()),
        "timeout": ExecutionTimeout(60),
        "submitted_at": "2026-06-15T10:30:00Z",
        "request_id": f"deploy_{uuid.uuid4()}_20260615_103000",
    }
    defaults.update(overrides)
    return DeployPlaybookRequest(**defaults)


class TestDeployPlaybookRequest:
    """Tests for DeployPlaybookRequest entity."""

    def test_create_valid_request(self):
        """Valid request should be created successfully."""
        request = _make_request()
        assert request.stage_name == "deploy"
        assert str(request.playbook_path) == "provision.yml"
        assert request.timeout.minutes == 60

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
        req_id = f"deploy_{job_id}_20260615_103000"
        request = _make_request(
            job_id=job_id,
            correlation_id=corr_id,
            request_id=req_id,
        )
        result = request.to_dict()

        assert result["job_id"] == job_id
        assert result["stage_name"] == "deploy"
        assert result["playbook_path"] == "provision.yml"
        assert result["correlation_id"] == corr_id
        assert result["timeout_minutes"] == 60
        assert result["submitted_at"] == "2026-06-15T10:30:00Z"
        assert result["request_id"] == req_id
        assert "extra_vars" in result

    def test_to_dict_has_all_required_nfs_fields(self):
        """to_dict must include all NFS queue request fields."""
        request = _make_request()
        result = request.to_dict()
        required_keys = [
            "job_id", "stage_name", "playbook_path", "extra_vars",
            "correlation_id", "timeout_minutes", "submitted_at", "request_id",
        ]
        for key in required_keys:
            assert key in result, f"Missing required NFS field: {key}"

    def test_extra_vars_serialized(self):
        """Extra vars should serialize to dict format."""
        extra = ExtraVars({"job_id": "j1", "image_group_id": "ig1"})
        request = _make_request(extra_vars=extra)
        result = request.to_dict()
        assert result["extra_vars"]["job_id"] == "j1"
        assert result["extra_vars"]["image_group_id"] == "ig1"

    def test_generate_filename(self):
        """generate_filename should follow {job_id}_{stage_name}_{timestamp}.json convention."""
        job_id = "test-job-id"
        request = _make_request(job_id=job_id)

        with patch("core.deploy.entities.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "20260615_103000"
            from datetime import timezone
            mock_dt.timezone = timezone
            filename = request.generate_filename()

        assert filename.startswith("test-job-id_deploy_")
        assert filename.endswith(".json")

    def test_different_playbook_path(self):
        """Should support different playbook paths."""
        request = _make_request(
            playbook_path=PlaybookPath("custom_provision.yml")
        )
        assert str(request.playbook_path) == "custom_provision.yml"
        assert request.to_dict()["playbook_path"] == "custom_provision.yml"

    def test_timeout_value_preserved(self):
        """Timeout value should be preserved in serialization."""
        request = _make_request(timeout=ExecutionTimeout(120))
        assert request.to_dict()["timeout_minutes"] == 120
