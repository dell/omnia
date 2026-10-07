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

# pylint: disable=protected-access,too-few-public-methods,unused-argument

"""Unit tests: stage log paths and attempt numbers are recorded uniformly."""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from api.jobs.schemas import GetStageResponse
from core.image_group.entities import ImageGroup
from core.image_group.value_objects import ImageGroupId, ImageGroupStatus
from core.jobs.entities import AuditEvent, Job, Stage
from core.jobs.value_objects import ClientId, JobId, StageName, StageState
from core.localrepo.entities import PlaybookResult
from infra.id_generator import UUIDv4Generator
from infra.repositories.in_memory import (
    InMemoryAuditEventRepository,
    InMemoryImageGroupRepository,
    InMemoryImageRepository,
    InMemoryJobRepository,
    InMemoryStageRepository,
)
from orchestrator.cleanup.use_cases.cleanup_job import CleanupJobUseCase
from orchestrator.common.result_poller import ResultPoller

pytestmark = pytest.mark.unit

LOG = "/opt/omnia/build_stream/logs/j/deploy_orchestrator.yml_20261006_000000_attempt2.log"


class _Results:
    def poll_results(self, callback):  # pragma: no cover - unused
        return 0


class _Queue:
    def __init__(self):
        self.submitted = []

    def submit_request(self, request, correlation_id):  # pylint: disable=unused-argument
        self.submitted.append(request)


def _poller(stage_repo, audit_repo, ig_repo=None, job_repo=None):
    return ResultPoller(
        result_service=_Results(),
        job_repo=job_repo or InMemoryJobRepository(),
        stage_repo=stage_repo,
        audit_repo=audit_repo,
        uuid_generator=UUIDv4Generator(),
        image_group_repo=ig_repo,
    )


@pytest.mark.parametrize("status", ["success", "failed"])
def test_stage_log_path_and_attempt_recorded_for_every_outcome(status):
    """log_file_path is stored and audited on success and on failure."""
    job_id = JobId(str(uuid.uuid4()))
    stage_repo = InMemoryStageRepository()
    stage_repo.save(Stage(
        job_id=job_id,
        stage_name=StageName("deploy"),
        stage_state=StageState.IN_PROGRESS,
        attempt=2,
    ))
    audit_repo = InMemoryAuditEventRepository()
    result = PlaybookResult(
        job_id=str(job_id), stage_name="deploy", request_id="r",
        status=status, exit_code=0 if status == "success" else 2,
        log_file_path=LOG,
    )

    _poller(stage_repo, audit_repo)._on_result_received(result)

    stage = stage_repo.find_by_job_and_name(job_id, StageName("deploy"))
    assert stage.log_file_path == LOG
    details = [
        e.details for e in audit_repo.find_by_job(job_id)
        if e.event_type.startswith("STAGE_")
    ][0]
    assert details["log_file_path"] == LOG
    assert details["attempt"] == 2


def test_cleanup_result_audits_log_path():
    """The cleanup playbook log path is recorded in the cleanup audit event."""
    job_id = JobId(str(uuid.uuid4()))
    ig_repo = InMemoryImageGroupRepository()
    ig_repo.save(ImageGroup(
        id=ImageGroupId("ig-1"), job_id=job_id, status=ImageGroupStatus.CLEANING,
    ))
    audit_repo = InMemoryAuditEventRepository()
    result = PlaybookResult(
        job_id=str(job_id), stage_name="cleanup", request_id="r",
        status="failed", exit_code=2, log_file_path=LOG,
    )

    _poller(InMemoryStageRepository(), audit_repo, ig_repo)._on_result_received(result)

    event = [e for e in audit_repo.find_by_job(job_id)
             if e.event_type == "JOB_CLEANUP_FAILED"][0]
    assert event.details["log_file_path"] == LOG


def test_get_stage_response_exposes_attempt():
    """The job API exposes the stage attempt alongside the log path."""
    response = GetStageResponse(
        stage_name="build-image", stage_state="FAILED", attempt=3,
        log_file_path=LOG,
    )

    assert response.model_dump()["attempt"] == 3
    assert GetStageResponse(stage_name="x", stage_state="PENDING").attempt == 1


def _cleanup_case(tmp_path, prior_submissions):
    job_id = JobId(str(uuid.uuid4()))
    client = ClientId(str(uuid.uuid4()))
    job_repo = InMemoryJobRepository()
    job_repo.save(Job(job_id=job_id, client_id=client, request_client_id=str(client)))
    ig_repo = InMemoryImageGroupRepository()
    ig_repo.save(ImageGroup(
        id=ImageGroupId("ig-1"), job_id=job_id, status=ImageGroupStatus.FAILED,
    ))
    audit_repo = InMemoryAuditEventRepository()
    for _ in range(prior_submissions):
        audit_repo.save(AuditEvent(
            event_id=str(uuid.uuid4()), job_id=job_id,
            event_type="JOB_CLEANUP_SUBMITTED",
            correlation_id=str(uuid.uuid4()), client_id="cron",
            timestamp=datetime.now(timezone.utc),
        ))
    queue = _Queue()
    use_case = CleanupJobUseCase(
        job_repo=job_repo,
        stage_repo=InMemoryStageRepository(),
        audit_repo=audit_repo,
        image_group_repo=ig_repo,
        image_repo=InMemoryImageRepository(),
        uuid_generator=UUIDv4Generator(),
        queue_service=queue,
        nfs_artifact_base=str(tmp_path),
    )
    use_case.execute_auto(str(job_id), correlation_id=str(uuid.uuid4()))
    return queue.submitted[0].extra_vars.to_dict()


@pytest.mark.parametrize("prior,expected", [(0, 1), (2, 3)])
def test_cleanup_request_carries_incrementing_attempt(tmp_path, prior, expected):
    """Each cleanup retry is submitted with the next attempt number."""
    assert _cleanup_case(tmp_path, prior)["attempt"] == expected


def test_api_log_base_is_build_stream_logs():
    """API job/event logs live under <data>/build_stream/logs, not <data>/log."""
    from api import logging_utils  # pylint: disable=import-outside-toplevel

    data = Path(os.getenv("OMNIA_DATA_PATH", "/opt/omnia"))
    assert logging_utils._LOG_BASE == data / "build_stream" / "logs"
    assert "log/build_stream" not in str(logging_utils._LOG_BASE)
