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

"""Unit tests for Deploy API routes."""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from api.deploy.routes import create_deploy, _build_error_response
from api.deploy.schemas import DeployRequest, DeployResponse
from core.jobs.value_objects import CorrelationId
from core.image_group.exceptions import (
    ImageGroupMismatchError,
    ImageGroupNotFoundError,
    InvalidStateTransitionError as IGInvalidStateTransitionError,
)
from core.jobs.exceptions import (
    JobNotFoundError,
    UpstreamStageNotCompletedError,
)
from core.jobs.value_objects import CorrelationId
from orchestrator.deploy.dtos.deploy_response import DeployResponseDTO


def _uuid():
    return str(uuid.uuid4())


class MockDeployUseCase:
    """Mock deploy use case for testing."""

    def __init__(self, result=None, error_to_raise=None):
        self._result = result
        self._error = error_to_raise
        self.executed_commands = []

    def execute(self, command):
        self.executed_commands.append(command)
        if self._error:
            raise self._error
        return self._result or DeployResponseDTO(
            job_id=str(command.job_id),
            stage_name="deploy",
            status="accepted",
            submitted_at=datetime.now(timezone.utc).isoformat() + "Z",
            image_group_id=str(command.image_group_id),
            correlation_id=str(command.correlation_id),
        )


class TestBuildErrorResponse:
    """Tests for _build_error_response helper."""

    def test_builds_correct_response(self):
        """Error response has all required fields."""
        resp = _build_error_response("TEST_ERROR", "test message", "corr-123")
        assert resp.error == "TEST_ERROR"
        assert resp.message == "test message"
        assert resp.correlation_id == "corr-123"
        assert resp.timestamp.endswith("Z")


class TestCreateDeploy:
    """Tests for POST /{job_id}/stages/deploy route handler."""

    def test_success(self):
        """Returns 202 Accepted on successful deploy."""
        job_id = _uuid()
        use_case = MockDeployUseCase()
        request_body = DeployRequest(image_group_id="test-cluster-v1")

        response = create_deploy(
            job_id=job_id,
            request_body=request_body,
            token_data={"client_id": "test-client", "scopes": ["job:write"]},
            use_case=use_case,
            correlation_id=CorrelationId(_uuid()),
            _=None,
        )

        assert isinstance(response, DeployResponse)
        assert response.job_id == job_id
        assert response.stage == "deploy"
        assert response.status == "accepted"
        assert response.image_group_id == "test-cluster-v1"
        assert len(use_case.executed_commands) == 1

    def test_invalid_job_id(self):
        """Returns 400 for invalid job_id format."""
        use_case = MockDeployUseCase()
        request_body = DeployRequest(image_group_id="test-cluster-v1")

        with pytest.raises(HTTPException) as exc_info:
            create_deploy(
                job_id="not-a-valid-uuid",
                request_body=request_body,
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(_uuid()),
                _=None,
            )
        assert exc_info.value.status_code == 400

    def test_job_not_found(self):
        """Returns 404 when job doesn't exist."""
        job_id = _uuid()
        use_case = MockDeployUseCase(
            error_to_raise=JobNotFoundError(
                job_id=job_id, correlation_id=_uuid()
            )
        )
        request_body = DeployRequest(image_group_id="test-cluster-v1")

        with pytest.raises(HTTPException) as exc_info:
            create_deploy(
                job_id=job_id,
                request_body=request_body,
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(_uuid()),
                _=None,
            )
        assert exc_info.value.status_code == 404

    def test_image_group_not_found(self):
        """Returns 404 when no ImageGroup exists for job."""
        job_id = _uuid()
        use_case = MockDeployUseCase(
            error_to_raise=ImageGroupNotFoundError(job_id=job_id)
        )
        request_body = DeployRequest(image_group_id="test-cluster-v1")

        with pytest.raises(HTTPException) as exc_info:
            create_deploy(
                job_id=job_id,
                request_body=request_body,
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(_uuid()),
                _=None,
            )
        assert exc_info.value.status_code == 404

    def test_image_group_mismatch(self):
        """Returns 409 when image_group_id doesn't match."""
        job_id = _uuid()
        use_case = MockDeployUseCase(
            error_to_raise=ImageGroupMismatchError(
                supplied="wrong-cluster", expected="actual-cluster"
            )
        )
        request_body = DeployRequest(image_group_id="wrong-cluster")

        with pytest.raises(HTTPException) as exc_info:
            create_deploy(
                job_id=job_id,
                request_body=request_body,
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(_uuid()),
                _=None,
            )
        assert exc_info.value.status_code == 409

    def test_precondition_failed(self):
        """Returns 412 when ImageGroup status is wrong."""
        job_id = _uuid()
        use_case = MockDeployUseCase(
            error_to_raise=IGInvalidStateTransitionError(
                current="DEPLOYING", required={"BUILT"}
            )
        )
        request_body = DeployRequest(image_group_id="test-cluster-v1")

        with pytest.raises(HTTPException) as exc_info:
            create_deploy(
                job_id=job_id,
                request_body=request_body,
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(_uuid()),
                _=None,
            )
        assert exc_info.value.status_code == 412

    def test_upstream_not_completed(self):
        """Returns 412 when upstream build stage not completed."""
        job_id = _uuid()
        use_case = MockDeployUseCase(
            error_to_raise=UpstreamStageNotCompletedError(
                job_id=job_id,
                required_stage="build-image-x86_64",
                actual_state="PENDING",
                correlation_id=_uuid(),
            )
        )
        request_body = DeployRequest(image_group_id="test-cluster-v1")

        with pytest.raises(HTTPException) as exc_info:
            create_deploy(
                job_id=job_id,
                request_body=request_body,
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(_uuid()),
                _=None,
            )
        assert exc_info.value.status_code == 412

    def test_unexpected_error(self):
        """Returns 500 on unexpected exception."""
        job_id = _uuid()
        use_case = MockDeployUseCase(
            error_to_raise=RuntimeError("unexpected")
        )
        request_body = DeployRequest(image_group_id="test-cluster-v1")

        with pytest.raises(HTTPException) as exc_info:
            create_deploy(
                job_id=job_id,
                request_body=request_body,
                token_data={"client_id": "test-client", "scopes": ["job:write"]},
                use_case=use_case,
                correlation_id=CorrelationId(_uuid()),
                _=None,
            )
        assert exc_info.value.status_code == 500
