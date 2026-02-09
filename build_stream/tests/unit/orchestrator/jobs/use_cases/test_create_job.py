# pylint: disable=too-few-public-methods
# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
# pylint: disable=duplicate-code

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

"""Unit tests for CreateJobUseCase."""

import pytest

from core.jobs.exceptions import JobAlreadyExistsError, IdempotencyConflictError
from core.jobs.value_objects import (
    JobId,
    ClientId,
    CorrelationId,
    IdempotencyKey,
    JobState,
    StageState,
    StageType,
)
from orchestrator.jobs.commands import CreateJobCommand
from orchestrator.jobs.use_cases import CreateJobUseCase


class _DeterministicJobIdGenerator:
    """Job ID generator that returns a predetermined JobId."""
    def __init__(self, job_id: JobId):
        self._job_id = job_id

    def generate(self) -> JobId:
        """Return the predetermined JobId."""
        return self._job_id


class _SequenceJobIdGenerator:
    """Job ID generator that returns JobIds from a list in sequence."""
    def __init__(self, job_ids: list[JobId]):
        self._job_ids = job_ids

    def generate(self) -> JobId:
        """Return the next JobId from the sequence."""
        return self._job_ids.pop(0)


class TestCreateJobUseCase:
    """Tests for CreateJobUseCase."""

    def test_create_job_success(
        self,
        job_repo,
        stage_repo,
        idempotency_repo,
        audit_repo,
        _job_id_generator,
        uuid_generator,
    ):
        """Job should be created with all initial stages."""
        generated_job_id = JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11")
        use_case = CreateJobUseCase(
            job_repo,
            stage_repo,
            idempotency_repo,
            audit_repo,
            job_id_generator=_DeterministicJobIdGenerator(generated_job_id),
            uuid_generator=uuid_generator,
        )
        command = CreateJobCommand(
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            client_name="abc123def456",
            correlation_id=CorrelationId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a12"),
            idempotency_key=IdempotencyKey("idem-key-1"),
        )
        response = use_case.execute(command)
        assert response.job_id == "018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"
        assert response.client_id == "client-1"
        assert response.client_name == "abc123def456"
        assert response.job_state == JobState.CREATED.value
        assert response.version == 1
        assert response.tombstoned is False

    def test_create_job_persists_job(
        self,
        job_repo,
        stage_repo,
        idempotency_repo,
        audit_repo,
        _job_id_generator,
        uuid_generator,
    ):
        """Job should be persisted to repository."""
        generated_job_id = JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11")
        use_case = CreateJobUseCase(
            job_repo,
            stage_repo,
            idempotency_repo,
            audit_repo,
            job_id_generator=_DeterministicJobIdGenerator(generated_job_id),
            uuid_generator=uuid_generator,
        )
        command = CreateJobCommand(
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            client_name="abc123def456",
            correlation_id=CorrelationId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a12"),
            idempotency_key=IdempotencyKey("idem-key-1"),
        )
        response = use_case.execute(command)
        saved_job = job_repo.find_by_id(JobId(response.job_id))
        assert saved_job is not None
        assert saved_job.job_id == JobId(response.job_id)
        assert saved_job.client_id == command.client_id
        assert saved_job.job_state == JobState.CREATED

    def test_create_job_creates_all_stages(
        self,
        job_repo,
        stage_repo,
        idempotency_repo,
        audit_repo,
        _job_id_generator,
        uuid_generator,
    ):
        """All 9 initial stages should be created in PENDING state."""
        generated_job_id = JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11")
        use_case = CreateJobUseCase(
            job_repo,
            stage_repo,
            idempotency_repo,
            audit_repo,
            job_id_generator=_DeterministicJobIdGenerator(generated_job_id),
            uuid_generator=uuid_generator,
        )
        command = CreateJobCommand(
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            client_name="abc123def456",
            correlation_id=CorrelationId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a12"),
            idempotency_key=IdempotencyKey("idem-key-1"),
        )
        response = use_case.execute(command)
        job_id = JobId(response.job_id)
        stages = stage_repo.find_all_by_job(job_id)
        assert len(stages) == 9

        stage_names = {stage.stage_name.value for stage in stages}
        expected_names = {stage_type.value for stage_type in StageType}
        assert stage_names == expected_names
        for stage in stages:
            assert stage.stage_state == StageState.PENDING
            assert stage.attempt == 1
            assert stage.job_id == job_id

    def test_create_job_saves_idempotency_record(
        self,
        job_repo,
        stage_repo,
        idempotency_repo,
        audit_repo,
        _job_id_generator,
        uuid_generator,
    ):
        """Idempotency record should be saved."""
        generated_job_id = JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11")
        use_case = CreateJobUseCase(
            job_repo,
            stage_repo,
            idempotency_repo,
            audit_repo,
            job_id_generator=_DeterministicJobIdGenerator(generated_job_id),
            uuid_generator=uuid_generator,
        )
        command = CreateJobCommand(
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            client_name="abc123def456",
            correlation_id=CorrelationId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a12"),
            idempotency_key=IdempotencyKey("idem-key-1"),
        )
        response = use_case.execute(command)
        record = idempotency_repo.find_by_key(command.idempotency_key)
        assert record is not None
        assert record.idempotency_key == command.idempotency_key
        assert record.client_id == command.client_id
        assert record.job_id == JobId(response.job_id)

    def test_create_job_emits_audit_event(
        self,
        job_repo,
        stage_repo,
        idempotency_repo,
        audit_repo,
        _job_id_generator,
        uuid_generator,
    ):
        """JOB_CREATED audit event should be emitted."""
        generated_job_id = JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11")
        use_case = CreateJobUseCase(
            job_repo,
            stage_repo,
            idempotency_repo,
            audit_repo,
            job_id_generator=_DeterministicJobIdGenerator(generated_job_id),
            uuid_generator=uuid_generator,
        )
        command = CreateJobCommand(
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            client_name="abc123def456",
            correlation_id=CorrelationId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a12"),
            idempotency_key=IdempotencyKey("idem-key-1"),
        )
        response = use_case.execute(command)
        job_id = JobId(response.job_id)
        events = audit_repo.find_by_job(job_id)
        assert len(events) == 1
        assert events[0].event_type == "JOB_CREATED"
        assert events[0].job_id == job_id
        assert events[0].correlation_id == command.correlation_id
        assert events[0].client_id == command.client_id

    def test_idempotent_retry_returns_existing_job(
        self,
        job_repo,
        stage_repo,
        idempotency_repo,
        audit_repo,
        _job_id_generator,
        uuid_generator,
    ):
        """Duplicate idempotency key with same fingerprint returns existing job."""
        generated_job_id = JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11")
        use_case = CreateJobUseCase(
            job_repo,
            stage_repo,
            idempotency_repo,
            audit_repo,
            job_id_generator=_DeterministicJobIdGenerator(generated_job_id),
            uuid_generator=uuid_generator,
        )
        command = CreateJobCommand(
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            client_name="abc123def456",
            correlation_id=CorrelationId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a12"),
            idempotency_key=IdempotencyKey("idem-key-1"),
        )
        first_response = use_case.execute(command)
        second_response = use_case.execute(command)
        assert first_response.job_id == second_response.job_id
        assert first_response.version == second_response.version
        stages = stage_repo.find_all_by_job(JobId(first_response.job_id))
        assert len(stages) == 9

        events = audit_repo.find_by_job(JobId(first_response.job_id))
        assert len(events) == 1

    def test_idempotency_conflict_raises_error(
        self,
        job_repo,
        stage_repo,
        idempotency_repo,
        audit_repo,
        _job_id_generator,
        uuid_generator,
    ):
        """Same idempotency key with different fingerprint raises conflict."""
        first_job_id = JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11")
        second_job_id = JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a13")
        generator = _SequenceJobIdGenerator([first_job_id, second_job_id])

        use_case = CreateJobUseCase(
            job_repo,
            stage_repo,
            idempotency_repo,
            audit_repo,
            job_id_generator=generator,
            uuid_generator=uuid_generator,
        )
        first_command = CreateJobCommand(
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            client_name="abc123def456",
            correlation_id=CorrelationId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a12"),
            idempotency_key=IdempotencyKey("idem-key-1"),
        )
        second_command = CreateJobCommand(
            client_id=ClientId("client-2"),
            request_client_id="req-client-456",
            client_name="different-digest",
            correlation_id=CorrelationId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a14"),
            idempotency_key=IdempotencyKey("idem-key-1"),
        )
        use_case.execute(first_command)
        with pytest.raises(IdempotencyConflictError) as exc_info:
            use_case.execute(second_command)

        assert exc_info.value.idempotency_key == "idem-key-1"
        assert exc_info.value.existing_job_id == str(first_job_id)
        assert exc_info.value.correlation_id == str(second_command.correlation_id)

    def test_job_already_exists_raises_error(
        self,
        job_repo,
        stage_repo,
        idempotency_repo,
        audit_repo,
        _job_id_generator,
        uuid_generator,
    ):
        """Creating job with existing job_id raises error."""
        generated_job_id = JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11")
        use_case = CreateJobUseCase(
            job_repo,
            stage_repo,
            idempotency_repo,
            audit_repo,
            job_id_generator=_DeterministicJobIdGenerator(generated_job_id),
            uuid_generator=uuid_generator,
        )
        first_command = CreateJobCommand(
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            client_name="abc123def456",
            correlation_id=CorrelationId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a12"),
            idempotency_key=IdempotencyKey("idem-key-1"),
        )
        second_command = CreateJobCommand(
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            client_name="abc123def456",
            correlation_id=CorrelationId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a13"),
            idempotency_key=IdempotencyKey("idem-key-2"),
        )
        use_case.execute(first_command)
        with pytest.raises(JobAlreadyExistsError) as exc_info:
            use_case.execute(second_command)

        assert exc_info.value.job_id == "018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"
        assert exc_info.value.correlation_id == str(second_command.correlation_id)
