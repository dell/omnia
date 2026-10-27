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

"""Unit tests for Build Image entities."""

import json
from datetime import datetime, timezone

import pytest

from core.build_image.entities import BuildImageRequest
from core.build_image.value_objects import FunctionalGroups, ImageKey
from core.localrepo.value_objects import ExecutionTimeout, ExtraVars, PlaybookPath


class TestBuildImageRequest:
    """Test cases for BuildImageRequest entity."""

    @pytest.fixture
    def sample_request(self):
        """Create a sample BuildImageRequest for testing."""
        return BuildImageRequest(
            job_id="job-123",
            stage_name="build-image",
            playbook_path=PlaybookPath("build_image_x86_64.yml"),
            extra_vars=ExtraVars(
                {
                    "job_id": "job-123",
                    "image_key": ImageKey("test-image").value,
                    "functional_groups": FunctionalGroups(["service_kube_control_plane_x86_64_first", "service_kube_control_plane_x86_64", "service_kube_node_x86_64"]).to_list(),
                }
            ),
            correlation_id="corr-456",
            timeout=ExecutionTimeout(60),
            submitted_at="2026-02-12T18:30:00.000Z",
            request_id="req-789",
        )

    @pytest.mark.parametrize(
        "functional_groups",
        [
            (
                "service_kube_control_plane_x86_64_first",
                "service_kube_control_plane_x86_64",
                "service_kube_node_x86_64",
            )
        ],
    )
    def test_to_dict(self, functional_groups):
        """Test serialization to dictionary."""
        request = BuildImageRequest(
            job_id="job-123",
            stage_name="build-image",
            playbook_path=PlaybookPath("build_image_x86_64.yml"),
            extra_vars=ExtraVars(
                {
                    "job_id": "job-123",
                    "image_key": ImageKey("test-image").value,
                    "functional_groups": list(functional_groups),
                }
            ),
            correlation_id="corr-456",
            timeout=ExecutionTimeout(60),
            submitted_at="2026-02-12T18:30:00.000Z",
            request_id="req-789",
        )

        result = request.to_dict()

        assert result["job_id"] == "job-123"
        assert result["stage_name"] == "build-image"
        assert result["extra_vars"]["job_id"] == "job-123"
        assert result["extra_vars"]["image_key"] == "test-image"
        assert result["extra_vars"]["functional_groups"] == list(functional_groups)
        assert result["playbook_path"] == "build_image_x86_64.yml"
        assert result["correlation_id"] == "corr-456"
        assert result["timeout_minutes"] == 60
        assert result["submitted_at"] == "2026-02-12T18:30:00.000Z"
        assert result["request_id"] == "req-789"
        assert "inventory_host" not in result

    @pytest.mark.parametrize(
        ("image_key_value", "inventory_host_value"),
        [("test-image", "192.168.1.100")],
    )
    def test_to_dict_with_inventory_host(self, image_key_value, inventory_host_value):
        """Test serialization to dictionary with inventory host."""
        request = BuildImageRequest(
            job_id="job-123",
            stage_name="build-image",
            playbook_path=PlaybookPath("build_image_aarch64.yml"),
            extra_vars=ExtraVars(
                {
                    "job_id": "job-123",
                    "image_key": ImageKey(image_key_value).value,
                    "functional_groups": FunctionalGroups(["group1"]).to_list(),
                    "inventory_host": inventory_host_value,
                }
            ),
            correlation_id="corr-456",
            timeout=ExecutionTimeout(60),
            submitted_at="2026-02-12T18:30:00.000Z",
            request_id="req-789",
        )

        result = request.to_dict()
        assert result["extra_vars"]["inventory_host"] == inventory_host_value

    def test_generate_filename(self, sample_request):
        """Test filename generation."""
        filename = sample_request.generate_filename()
        assert filename.startswith("job-123_build-image_")
        assert filename.endswith(".json")
        # Should include timestamp
        assert len(filename) > len("job-123_build-image_.json")

    def test_no_shell_command_builder(self, sample_request):
        """The shell-string builder is gone; the watcher builds argv itself (F24)."""
        assert not hasattr(sample_request, "get_playbook_command")

    def test_queue_request_cannot_carry_inventory(self, sample_request):
        """No inventory path is serialised or accepted (F27)."""
        assert "inventory_file_path" not in sample_request.to_dict()
        with pytest.raises(TypeError):
            BuildImageRequest(
                job_id="job-123",
                stage_name="build-image",
                playbook_path=PlaybookPath("build_image_x86_64.yml"),
                extra_vars=sample_request.extra_vars,
                correlation_id="corr-456",
                timeout=ExecutionTimeout(60),
                submitted_at="2026-02-12T18:30:00.000Z",
                request_id="req-789",
                inventory_file_path="/etc/passwd",
            )

    def test_immutable(self, sample_request):
        """Test that BuildImageRequest is immutable."""
        with pytest.raises(AttributeError):
            sample_request.job_id = "new-job-id"

    def test_all_fields_required(self):
        """Test that all required fields must be provided."""
        with pytest.raises(TypeError):
            BuildImageRequest(
                job_id="job-123",
                # Missing other required fields
            )
