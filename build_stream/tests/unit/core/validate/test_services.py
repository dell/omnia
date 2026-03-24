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

"""Unit tests for ValidateImageOnTest domain services."""

import uuid

import pytest

from core.jobs.value_objects import CorrelationId
from core.localrepo.value_objects import ExecutionTimeout, ExtraVars, PlaybookPath
from core.validate.entities import ValidateImageOnTestRequest
from core.validate.services import ValidateQueueService


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
    """Create a ValidateImageOnTestRequest with sensible defaults."""
    return ValidateImageOnTestRequest(
        job_id=str(uuid.uuid4()),
        stage_name="validate-image-on-test",
        playbook_path=PlaybookPath("discovery.yml"),
        extra_vars=ExtraVars({"job_id": str(uuid.uuid4())}),
        correlation_id=str(uuid.uuid4()),
        timeout=ExecutionTimeout(60),
        submitted_at="2026-02-17T10:30:00Z",
        request_id=str(uuid.uuid4()),
    )


class TestValidateQueueService:
    """Tests for ValidateQueueService."""

    def test_submit_request_success(self):
        """Successful submission should write request to repo."""
        repo = MockQueueRepo()
        service = ValidateQueueService(queue_repo=repo)
        request = _make_request()
        corr_id = CorrelationId(str(uuid.uuid4()))

        service.submit_request(request=request, correlation_id=corr_id)

        assert len(repo.written_requests) == 1
        assert repo.written_requests[0] is request

    def test_submit_request_failure_propagates(self):
        """Queue failure should propagate the exception."""
        repo = MockQueueRepo(should_fail=True)
        service = ValidateQueueService(queue_repo=repo)
        request = _make_request()
        corr_id = CorrelationId(str(uuid.uuid4()))

        with pytest.raises(IOError, match="Queue unavailable"):
            service.submit_request(request=request, correlation_id=corr_id)
