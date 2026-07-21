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

"""Unit tests for Deploy domain services."""

import uuid

import pytest

from core.deploy.entities import DeployPlaybookRequest
from core.deploy.services import DeployQueueService
from core.jobs.value_objects import CorrelationId
from core.localrepo.value_objects import ExecutionTimeout, ExtraVars, PlaybookPath


class MockQueueRepo:
    """Mock playbook queue request repository."""

    def __init__(self, should_fail: bool = False):
        self.written_requests = []
        self.should_fail = should_fail

    def write_request(self, request):
        if self.should_fail:
            raise IOError("Queue unavailable")
        self.written_requests.append(request)


def _make_request():
    """Create a DeployPlaybookRequest with sensible defaults."""
    return DeployPlaybookRequest(
        job_id=str(uuid.uuid4()),
        stage_name="deploy",
        playbook_path=PlaybookPath("provision.yml"),
        extra_vars=ExtraVars({"job_id": "test-job", "image_group_id": "test-cluster"}),
        correlation_id=str(uuid.uuid4()),
        timeout=ExecutionTimeout(60),
        submitted_at="2026-06-15T10:30:00Z",
        request_id=f"deploy_{uuid.uuid4()}_20260615_103000",
    )


class TestDeployQueueService:
    """Tests for DeployQueueService."""

    def test_submit_request_success(self):
        """Successful submission should write request to repo."""
        repo = MockQueueRepo()
        service = DeployQueueService(queue_repo=repo)
        request = _make_request()
        corr_id = str(uuid.uuid4())

        service.submit_request(request=request, correlation_id=CorrelationId(corr_id))

        assert len(repo.written_requests) == 1
        assert repo.written_requests[0] is request

    def test_submit_request_failure_propagates(self):
        """Queue failure should propagate the exception."""
        repo = MockQueueRepo(should_fail=True)
        service = DeployQueueService(queue_repo=repo)
        request = _make_request()
        corr_id = str(uuid.uuid4())

        with pytest.raises(IOError, match="Queue unavailable"):
            service.submit_request(request=request, correlation_id=CorrelationId(corr_id))

    def test_submit_multiple_requests(self):
        """Multiple submissions should all be written."""
        repo = MockQueueRepo()
        service = DeployQueueService(queue_repo=repo)

        for _ in range(3):
            request = _make_request()
            service.submit_request(request=request, correlation_id=CorrelationId(str(uuid.uuid4())))

        assert len(repo.written_requests) == 3
