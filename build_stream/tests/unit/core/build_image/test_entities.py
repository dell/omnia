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

from datetime import datetime, timezone

import pytest

from core.build_image.entities import BuildImageRequest
from core.build_image.value_objects import (
    Architecture,
    ImageKey,
    FunctionalGroups,
    InventoryHost,
)


class TestBuildImageRequest:
    """Test cases for BuildImageRequest entity."""

    @pytest.fixture
    def sample_request(self):
        """Create a sample BuildImageRequest for testing."""
        return BuildImageRequest(
            job_id="job-123",
            stage_name="build-image",
            architecture=Architecture("x86_64"),
            image_key=ImageKey("test-image"),
            functional_groups=FunctionalGroups(["group1", "group2"]),
            playbook_path="/omnia/build_image_x86_64/build_image_x86_64.yml",
            correlation_id="corr-456",
            timeout_minutes=60,
            submitted_at="2026-02-12T18:30:00.000Z",
            request_id="req-789",
        )

    def test_to_dict(self, sample_request):
        """Test serialization to dictionary."""
        result = sample_request.to_dict()
        
        assert result["job_id"] == "job-123"
        assert result["stage_name"] == "build-image"
        assert result["architecture"] == "x86_64"
        assert result["image_key"] == "test-image"
        assert result["functional_groups"] == ["group1", "group2"]
        assert result["playbook_path"] == "/omnia/build_image_x86_64/build_image_x86_64.yml"
        assert result["correlation_id"] == "corr-456"
        assert result["timeout_minutes"] == 60
        assert result["submitted_at"] == "2026-02-12T18:30:00.000Z"
        assert result["request_id"] == "req-789"
        assert "inventory_host" not in result

    def test_to_dict_with_inventory_host(self):
        """Test serialization to dictionary with inventory host."""
        request = BuildImageRequest(
            job_id="job-123",
            stage_name="build-image",
            architecture=Architecture("aarch64"),
            image_key=ImageKey("test-image"),
            functional_groups=FunctionalGroups(["group1"]),
            playbook_path="/omnia/build_image_aarch64/build_image_aarch64.yml",
            correlation_id="corr-456",
            timeout_minutes=60,
            submitted_at="2026-02-12T18:30:00.000Z",
            request_id="req-789",
            inventory_host=InventoryHost("192.168.1.100"),
        )
        
        result = request.to_dict()
        assert result["inventory_host"] == "192.168.1.100"

    def test_generate_filename(self, sample_request):
        """Test filename generation."""
        filename = sample_request.generate_filename()
        assert filename.startswith("job-123_build-image_")
        assert filename.endswith(".json")
        # Should include timestamp
        assert len(filename) > len("job-123_build-image_.json")

    def test_get_playbook_command_x86_64(self, sample_request):
        """Test playbook command generation for x86_64."""
        command = sample_request.get_playbook_command()
        
        assert "ansible-playbook" in command
        assert "/omnia/build_image_x86_64/build_image_x86_64.yml" in command
        assert '-e job_id="job-123"' in command
        assert '-e image_key="test-image"' in command
        assert '-e functional_groups=\'["group1", "group2"]\'' in command
        assert "-i " not in command  # No inventory for x86_64

    def test_get_playbook_command_aarch64(self):
        """Test playbook command generation for aarch64."""
        request = BuildImageRequest(
            job_id="job-123",
            stage_name="build-image",
            playbook_path=PlaybookPath("/omnia/build_image_aarch64/build_image_aarch64.yml"),
            extra_vars=ExtraVars({
                "job_id": "job-123",
                "image_key": "test-image",
                "functional_groups": ["group1"],
                "inventory_host": "192.168.1.100",
            }),
            correlation_id="corr-456",
            timeout=ExecutionTimeout(60),
            submitted_at="2026-02-12T18:30:00.000Z",
            request_id="req-789",
        )
        
        command = request.get_playbook_command()
        
        assert "ansible-playbook" in command
        assert "/omnia/build_image_aarch64/build_image_aarch64.yml" in command
        assert "-i 192.168.1.100" in command
        assert '-e job_id="job-123"' in command
        assert '-e image_key="test-image"' in command
        assert '-e functional_groups=\'["group1"]\'' in command

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
