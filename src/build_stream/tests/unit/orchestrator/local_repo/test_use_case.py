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

"""Unit tests for CreateLocalRepoUseCase."""

import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.jobs.entities import Job, Stage
from core.jobs.exceptions import JobNotFoundError, UpstreamStageNotCompletedError
from core.jobs.value_objects import (
    ClientId,
    CorrelationId,
    JobId,
    StageName,
    StageState,
    StageType,
)
from core.localrepo.exceptions import InputFilesMissingError
from orchestrator.local_repo.commands import CreateLocalRepoCommand
from orchestrator.local_repo.use_cases import CreateLocalRepoUseCase


@pytest.fixture(name="job_id")
def job_id_fixture():
    """Provide a valid JobId."""
    return JobId(str(uuid.uuid4()))


@pytest.fixture(name="client_id")
def client_id_fixture():
    """Provide a valid ClientId."""
    return ClientId("test-client-123")


@pytest.fixture(name="correlation_id")
def correlation_id_fixture():
    """Provide a valid CorrelationId."""
    return CorrelationId(str(uuid.uuid4()))


@pytest.fixture(name="job")
def job_fixture(job_id, client_id):
    """Provide a Job entity."""
    return Job(
        job_id=job_id,
        client_id=client_id,
        request_client_id="client-123",
    )


@pytest.fixture(name="stage")
def stage_fixture(job_id):
    """Provide a Stage entity in PENDING state."""
    return Stage(
        job_id=job_id,
        stage_name=StageName(StageType.CREATE_LOCAL_REPOSITORY.value),
    )


@pytest.fixture(name="parse_catalog_stage")
def parse_catalog_stage_fixture(job_id):
    """Provide a COMPLETED parse-catalog stage (upstream dependency).

    Reintroduced (Omnia 2.3+): create-local-repository now requires
    parse-catalog to have completed the image_group_id uniqueness check.
    """
    return Stage(
        job_id=job_id,
        stage_name=StageName(StageType.PARSE_CATALOG.value),
        stage_state=StageState.COMPLETED,
        attempt=1,
    )


@pytest.fixture(name="command")
def command_fixture(job_id, client_id, correlation_id):
    """Provide a CreateLocalRepoCommand."""
    return CreateLocalRepoCommand(
        job_id=job_id,
        client_id=client_id,
        correlation_id=correlation_id,
    )


@pytest.fixture(name="use_case")
def use_case_fixture(job, stage, parse_catalog_stage):
    """Provide a CreateLocalRepoUseCase with mocked dependencies.

    Omnia 2.3+: parse-catalog (reintroduced, minimal) is now the upstream
    dependency for create-local-repository, which must find it COMPLETED.
    """
    job_repo = MagicMock()
    job_repo.find_by_id.return_value = job

    stage_repo = MagicMock()

    def _find_by_job_and_name(_job_id_arg, stage_name_arg):
        if stage_name_arg.value == StageType.CREATE_LOCAL_REPOSITORY.value:
            return stage
        if stage_name_arg.value == StageType.PARSE_CATALOG.value:
            return parse_catalog_stage
        return None

    stage_repo.find_by_job_and_name.side_effect = _find_by_job_and_name

    audit_repo = MagicMock()

    input_file_service = MagicMock()
    input_file_service.prepare_playbook_input.return_value = True

    playbook_queue_service = MagicMock()
    playbook_queue_service.submit_request.return_value = Path("/queue/requests/test.json")

    uuid_generator = MagicMock()
    uuid_generator.generate.return_value = uuid.uuid4()

    use_case = CreateLocalRepoUseCase(
        job_repo=job_repo,
        stage_repo=stage_repo,
        audit_repo=audit_repo,
        input_file_service=input_file_service,
        playbook_queue_service=playbook_queue_service,
        uuid_generator=uuid_generator,
    )
    use_case._job_repo = job_repo
    use_case._stage_repo = stage_repo
    use_case._audit_repo = audit_repo
    use_case._input_file_service = input_file_service
    use_case._playbook_queue_service = playbook_queue_service
    return use_case


class TestCreateLocalRepoUseCase:
    """Tests for CreateLocalRepoUseCase."""

    def test_execute_success(self, use_case, command):
        """Successful execution should return accepted response."""
        result = use_case.execute(command)

        assert result.status == "accepted"
        assert result.stage_name == "create-local-repository"
        assert result.job_id == str(command.job_id)
        assert result.correlation_id == str(command.correlation_id)

    def test_execute_updates_stage_to_running(self, use_case, command):
        """Stage should transition to IN_PROGRESS on success."""
        use_case.execute(command)
        use_case._stage_repo.save.assert_called()

    def test_execute_submits_request(self, use_case, command):
        """Request should be submitted to the queue."""
        use_case.execute(command)
        use_case._playbook_queue_service.submit_request.assert_called_once()

    def test_execute_emits_audit_event(self, use_case, command):
        """Audit event should be emitted."""
        use_case.execute(command)
        use_case._audit_repo.save.assert_called_once()

    def test_execute_job_not_found(self, use_case, command):
        """Missing job should raise JobNotFoundError."""
        use_case._job_repo.find_by_id.return_value = None

        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_execute_tombstoned_job(self, use_case, command, job):
        """Tombstoned job should raise JobNotFoundError."""
        job.tombstone()
        use_case._job_repo.find_by_id.return_value = job

        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_execute_wrong_client(self, use_case, command, job):
        """Job owned by different client should raise JobNotFoundError."""
        job.client_id = ClientId("other-client")
        use_case._job_repo.find_by_id.return_value = job

        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_execute_stage_not_found(self, use_case, command, parse_catalog_stage):
        """Missing create-local-repository stage should raise error.

        The upstream parse-catalog stage is still COMPLETED here -- only
        the create-local-repository stage itself is missing.
        """
        def _only_parse_catalog_found(_job_id_arg, stage_name_arg):
            if stage_name_arg.value == StageType.PARSE_CATALOG.value:
                return parse_catalog_stage
            return None

        use_case._stage_repo.find_by_job_and_name.side_effect = _only_parse_catalog_found

        with pytest.raises(JobNotFoundError):
            use_case.execute(command)

    def test_execute_upstream_parse_catalog_not_completed(self, use_case, command, job_id):
        """parse-catalog not COMPLETED should block create-local-repository."""
        pending_parse_catalog = Stage(
            job_id=job_id,
            stage_name=StageName(StageType.PARSE_CATALOG.value),
        )

        def _pending_parse_catalog(_job_id_arg, stage_name_arg):
            if stage_name_arg.value == StageType.PARSE_CATALOG.value:
                return pending_parse_catalog
            return None

        use_case._stage_repo.find_by_job_and_name.side_effect = _pending_parse_catalog

        with pytest.raises(UpstreamStageNotCompletedError):
            use_case.execute(command)

    def test_execute_input_files_missing(self, use_case, command):
        """Missing input files should raise and fail the stage."""
        use_case._input_file_service.prepare_playbook_input.side_effect = (
            InputFilesMissingError(
                job_id=str(command.job_id),
                input_path="/opt/omnia/build_stream/job-1/input",
            )
        )

        with pytest.raises(InputFilesMissingError):
            use_case.execute(command)

        use_case._stage_repo.save.assert_called()
        use_case._playbook_queue_service.submit_request.assert_not_called()
