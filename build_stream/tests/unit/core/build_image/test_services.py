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

"""Unit tests for Build Image services."""

import pytest

from core.build_image.exceptions import InventoryHostMissingError
from core.build_image.repositories import BuildStreamConfigRepository
from core.build_image.services import (
    BuildImageConfigService,
    BuildImageQueueService,
)
from core.build_image.value_objects import Architecture, InventoryHost
from core.build_image.entities import BuildImageRequest
from core.localrepo.value_objects import (
    ExecutionTimeout,
    ExtraVars,
    PlaybookPath,
)


class MockBuildImageConfigRepository(BuildStreamConfigRepository):
    """Mock implementation of BuildStreamConfigRepository."""

    def __init__(self, inventory_host=None, should_fail=False):
        """Initialize mock with optional inventory host."""
        self.inventory_host = inventory_host
        self.should_fail = should_fail

    def get_aarch64_inv_host(self, job_id):
        """Return configured inventory host or None."""
        if self.should_fail:
            raise Exception("Config file error")
        return self.inventory_host


class MockBuildImageQueueRepository:
    """Mock implementation of PlaybookQueueRequestRepository."""

    def __init__(self, should_fail=False):
        """Initialize mock with optional failure mode."""
        self.submitted_requests = []
        self.should_fail = should_fail

    def write_request(self, request):
        """Store submitted request."""
        if self.should_fail:
            raise Exception("Queue error")
        self.submitted_requests.append(request)


class TestBuildImageConfigService:
    """Test cases for BuildImageConfigService."""

    def test_get_inventory_host_for_x86_64(self):
        """Test that x86_64 doesn't require inventory host."""
        config_repo = MockBuildImageConfigRepository()
        service = BuildImageConfigService(config_repo)
        
        result = service.get_inventory_host("job-123", Architecture("x86_64"), "corr-456")
        
        assert result is None

    def test_get_inventory_host_for_aarch64_success(self):
        """Test successful inventory host retrieval for aarch64."""
        config_repo = MockBuildImageConfigRepository(inventory_host="192.168.1.100")
        service = BuildImageConfigService(config_repo)
        
        result = service.get_inventory_host("job-123", Architecture("aarch64"), "corr-456")
        
        assert result is not None
        assert str(result) == "192.168.1.100"

    def test_get_inventory_host_for_aarch64_missing(self):
        """Test missing inventory host for aarch64."""
        config_repo = MockBuildImageConfigRepository()
        service = BuildImageConfigService(config_repo)
        
        with pytest.raises(InventoryHostMissingError) as exc_info:
            service.get_inventory_host("job-123", Architecture("aarch64"), "corr-456")
        
        assert "Inventory host is required for aarch64 builds" in str(exc_info.value)
        assert exc_info.value.correlation_id == "corr-456"

    def test_get_inventory_host_for_aarch64_config_error(self):
        """Test config error when retrieving inventory host."""
        config_repo = MockBuildImageConfigRepository(should_fail=True)
        service = BuildImageConfigService(config_repo)
        
        with pytest.raises(InventoryHostMissingError) as exc_info:
            service.get_inventory_host("job-123", Architecture("aarch64"), "corr-456")
        
        assert "Inventory host is required for aarch64 builds" in str(exc_info.value)


class TestBuildImageQueueService:
    """Test cases for BuildImageQueueService."""

    def test_submit_request_success(self):
        """Test successful request submission."""
        queue_repo = MockBuildImageQueueRepository()
        service = BuildImageQueueService(queue_repo)
        
        request = BuildImageRequest(
            job_id="job-123",
            stage_name="build-image",
            # architecture=Architecture("x86_64"),
            # image_key="test-image",
            # functional_groups=["group1"],
            playbook_path=PlaybookPath("/path/to/playbook.yml"),
            correlation_id="corr-456",
            timeout=ExecutionTimeout(60),
            submitted_at="2026-02-12T18:30:00.000Z",
            request_id="req-789",
        )
        
        service.submit_request(request, "corr-456")
        
        assert len(queue_repo.submitted_requests) == 1
        submitted_request = queue_repo.submitted_requests[0]
        assert submitted_request == request

    def test_submit_request_failure(self):
        """Test request submission failure."""
        queue_repo = MockBuildImageQueueRepository(should_fail=True)
        service = BuildImageQueueService(queue_repo)
        
        request = BuildImageRequest(
            job_id="job-123",
            stage_name="build-image",
            # architecture=Architecture("x86_64"),
            # image_key="test-image",
            # functional_groups=["group1"],
            playbook_path=PlaybookPath("/path/to/playbook.yml"),
            correlation_id="corr-456",
            timeout=ExecutionTimeout(60),
            submitted_at="2026-02-12T18:30:00.000Z",
            request_id="req-789",
        )
        
        # The service should let the exception bubble up
        with pytest.raises(Exception, match="Queue error"):
            service.submit_request(request, "corr-456")
