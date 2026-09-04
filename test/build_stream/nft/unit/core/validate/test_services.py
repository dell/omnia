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

"""Unit tests for Validate domain services."""

import uuid

import pytest

from core.validate.entities import ValidateRequest
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
    """Create a ValidateRequest with sensible defaults."""
    return ValidateRequest(
        request_id=f"validate_{uuid.uuid4()}_20260217_103000",
        job_id=str(uuid.uuid4()),
        stage_type="validate",
        command_type="test_automation",
        scenario_names=["all"],
        test_suite="",
        timeout_minutes=120,
        artifact_dir="/opt/omnia/build_stream_root/artifacts/test/validate/attempt_1",
        config_path="/opt/omnia/automation/omnia_test_config.yml",
        correlation_id=str(uuid.uuid4()),
        submitted_at="2026-02-17T10:30:00Z",
        attempt=1,
    )


class TestValidateQueueService:
    """Tests for ValidateQueueService."""

    def test_submit_request_success(self):
        """Successful submission should write request to repo."""
        repo = MockQueueRepo()
        service = ValidateQueueService(queue_repo=repo)
        request = _make_request()
        corr_id = str(uuid.uuid4())

        service.submit_request(request=request, correlation_id=corr_id)

        assert len(repo.written_requests) == 1
        assert repo.written_requests[0] is request

    def test_submit_request_failure_propagates(self):
        """Queue failure should propagate the exception."""
        repo = MockQueueRepo(should_fail=True)
        service = ValidateQueueService(queue_repo=repo)
        request = _make_request()
        corr_id = str(uuid.uuid4())

        with pytest.raises(IOError, match="Queue unavailable"):
            service.submit_request(request=request, correlation_id=corr_id)

    def test_submit_request_with_scenarios(self):
        """Submission with specific scenarios should succeed."""
        repo = MockQueueRepo()
        service = ValidateQueueService(queue_repo=repo)
        request = ValidateRequest(
            request_id="test-req",
            job_id="test-job",
            stage_type="validate",
            command_type="test_automation",
            scenario_names=["discovery", "slurm"],
            test_suite="smoke",
            timeout_minutes=60,
            correlation_id="corr-123",
        )

        service.submit_request(request=request, correlation_id="corr-123")

        assert len(repo.written_requests) == 1
        written = repo.written_requests[0]
        assert written.scenario_names == ["discovery", "slurm"]
        assert written.test_suite == "smoke"
        assert written.command_type == "test_automation"
