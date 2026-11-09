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

# pylint: disable=protected-access,too-few-public-methods,unused-argument,missing-function-docstring,too-many-instance-attributes

"""Unit tests: build-image success is completed only after image registration.

OMN-DEF #1380: the result poller marked build-image COMPLETED before it
registered the ImageGroup and Images, and silently skipped the registration
when the catalog metadata could not be loaded. These tests pin the corrected
contract: register first, complete second, and fail the stage (and the job)
with a specific error code whenever registration cannot be performed.
"""

import json
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError

from core.artifacts.entities import ArtifactRecord
from core.artifacts.exceptions import ArtifactNotFoundError
from core.artifacts.value_objects import (
    ArtifactDigest,
    ArtifactKey,
    ArtifactKind,
    ArtifactRef,
)
from core.image_group.entities import ImageGroup
from core.image_group.value_objects import ImageGroupId, ImageGroupStatus
from core.jobs.entities import Job, Stage
from core.jobs.value_objects import ClientId, JobId, JobState, StageName, StageState
from core.localrepo.entities import PlaybookResult
from orchestrator.common.result_poller import (
    CATALOG_METADATA_INVALID,
    CATALOG_METADATA_MISSING,
    IMAGE_GROUP_REGISTRATION_FAILED,
    ResultPoller,
)

pytestmark = pytest.mark.unit

GROUP_ID = "test-cluster-v1"
METADATA = {
    "image_group_id": "test-cluster",
    "composite_image_group_id": GROUP_ID,
    "catalog_version": "1",
    "roles": ["slurm_node_x86_64"],
    "role_images": {"slurm_node_x86_64": "slurm_node_x86_64.img"},
}


# --- Test doubles -----------------------------------------------------------

class _Session:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def flush(self):
        pass

    def rollback(self):
        self.rollbacks += 1


class _StageRepo:
    def __init__(self):
        self._stages = {}

    def save(self, stage):
        self._stages[(str(stage.job_id), stage.stage_name.value)] = stage

    def find_by_job_and_name(self, job_id, stage_name):
        return self._stages.get((str(job_id), stage_name.value))


class _JobRepo:
    def __init__(self):
        self._jobs = {}

    def save(self, job):
        self._jobs[str(job.job_id)] = job

    def find_by_id(self, job_id):
        return self._jobs.get(str(job_id))


class _AuditRepo:
    def __init__(self):
        self.events = []

    def save(self, event):
        self.events.append(event)

    def types(self):
        return [event.event_type for event in self.events]


class _UUIDs:
    def generate(self):
        return uuid.uuid4()


class _ArtifactStore:
    """Artifact store whose retrieve() behaviour each test can choose."""

    def __init__(self, content=None, error=None):
        self._content = content
        self._error = error

    def retrieve(self, key, kind, destination=None):
        if self._error is not None:
            raise self._error
        if self._content is None:
            raise ArtifactNotFoundError(key=str(key.value))
        return self._content


class _MetadataRepo:
    def __init__(self, session, record=None, error=None):
        self.session = session
        self._record = record
        self._error = error

    def find_by_job_stage_and_label(self, job_id, stage_name, label):
        if self._error is not None:
            raise self._error
        return self._record


class _ImageGroupRepo:
    def __init__(self, session):
        self.session = session
        self.groups = {}

    def save(self, image_group):
        if str(image_group.id) in self.groups:
            raise IntegrityError("INSERT image_groups", {}, Exception("duplicate key"))
        self.groups[str(image_group.id)] = image_group

    def find_by_id(self, image_group_id):
        return self.groups.get(str(image_group_id))

    def find_by_job_id(self, job_id):
        return next(
            (g for g in self.groups.values() if str(g.job_id) == str(job_id)), None
        )


class _ImageRepo:
    def __init__(self, session, error=None):
        self.session = session
        self.images = []
        self._error = error

    def save_batch(self, images):
        if self._error is not None:
            raise self._error
        self.images.extend(images)


def _record(job_id):
    key = ArtifactKey("catalog/abcdef123456/catalog-metadata.bin")
    return ArtifactRecord(
        id=str(uuid.uuid4()),
        job_id=job_id,
        stage_name=StageName("parse-catalog"),
        label="catalog-metadata",
        artifact_ref=ArtifactRef(
            key=key,
            digest=ArtifactDigest("a" * 64),
            size_bytes=1,
            uri=f"file:///{key.value}",
        ),
        kind=ArtifactKind.FILE,
        content_type="application/json",
    )


class _Case:
    """A build-image stage IN_PROGRESS, its job, and a wired result poller."""

    def __init__(self, *, content=b"", record=True, store_error=None,
                 lookup_error=None, image_error=None):
        self.job_id = JobId(str(uuid.uuid4()))
        client = ClientId(str(uuid.uuid4()))
        self.job_repo = _JobRepo()
        job = Job(job_id=self.job_id, client_id=client, request_client_id=str(client))
        job.start()
        self.job_repo.save(job)
        self.stage_repo = _StageRepo()
        self.stage_repo.save(Stage(
            job_id=self.job_id,
            stage_name=StageName("build-image"),
            stage_state=StageState.IN_PROGRESS,
            attempt=1,
        ))
        self.audit_repo = _AuditRepo()
        self.session = _Session()
        self.ig_repo = _ImageGroupRepo(self.session)
        self.image_repo = _ImageRepo(self.session, error=image_error)
        if content == b"":
            content = json.dumps(METADATA).encode("utf-8")
        self.poller = ResultPoller(
            result_service=None,
            job_repo=self.job_repo,
            stage_repo=self.stage_repo,
            audit_repo=self.audit_repo,
            uuid_generator=_UUIDs(),
            image_group_repo=self.ig_repo,
            image_repo=self.image_repo,
            artifact_store=_ArtifactStore(content=content, error=store_error),
            artifact_metadata_repo=_MetadataRepo(
                self.session,
                record=_record(self.job_id) if record else None,
                error=lookup_error,
            ),
        )

    def deliver_success(self):
        self.poller._on_result_received(PlaybookResult(
            job_id=str(self.job_id),
            stage_name="build-image",
            request_id=str(uuid.uuid4()),
            status="success",
            exit_code=0,
            duration_seconds=60,
        ))

    @property
    def stage(self):
        return self.stage_repo.find_by_job_and_name(
            str(self.job_id), StageName("build-image")
        )

    @property
    def job(self):
        return self.job_repo.find_by_id(self.job_id)

    def assert_hard_failure(self, error_code):
        assert self.stage.stage_state == StageState.FAILED
        assert self.stage.error_code == error_code
        assert self.job.job_state == JobState.FAILED
        assert "STAGE_COMPLETED" not in self.audit_repo.types()
        assert "JOB_FAILED" in self.audit_repo.types()
        stage_failed = [e for e in self.audit_repo.events if e.event_type == "STAGE_FAILED"]
        assert len(stage_failed) == 1
        assert stage_failed[0].details["error_code"] == error_code
        assert self.ig_repo.find_by_job_id(self.job_id) is None
        assert not self.image_repo.images


def _discovered(bucket_uri, identity, role_names):
    return {role: [f"s3://boot-images/{role}/{identity}/"] for role in role_names}


# --- Success path -------------------------------------------------------------

@patch("orchestrator.common.result_poller._discover_s3_image_paths")
def test_registration_runs_before_stage_completion(mock_discover):
    """The ImageGroup is registered while the stage is still IN_PROGRESS."""
    case = _Case()
    states_during_registration = []

    def _discover(bucket_uri, identity, role_names):
        states_during_registration.append(case.stage.stage_state)
        return _discovered(bucket_uri, identity, role_names)

    mock_discover.side_effect = _discover
    case.deliver_success()

    assert states_during_registration
    assert set(states_during_registration) == {StageState.IN_PROGRESS}
    assert case.stage.stage_state == StageState.COMPLETED
    group = case.ig_repo.find_by_job_id(case.job_id)
    assert group is not None and group.status == ImageGroupStatus.BUILT
    assert [i.role for i in case.image_repo.images] == ["slurm_node_x86_64"]
    assert case.audit_repo.types().count("STAGE_COMPLETED") == 1
    assert "STAGE_FAILED" not in case.audit_repo.types()


@patch("orchestrator.common.result_poller._discover_s3_image_paths",
       side_effect=_discovered)
def test_redelivered_result_for_same_job_is_idempotent(mock_discover):
    """An ImageGroup already registered by the same job counts as success."""
    case = _Case()
    case.ig_repo.groups[GROUP_ID] = ImageGroup(
        id=ImageGroupId(GROUP_ID), job_id=case.job_id, status=ImageGroupStatus.BUILT,
    )

    case.deliver_success()

    assert case.stage.stage_state == StageState.COMPLETED
    assert case.session.rollbacks >= 1


# --- Hard failures --------------------------------------------------------------

def test_missing_metadata_record_fails_stage_and_job():
    """No catalog-metadata row in the database -> CATALOG_METADATA_MISSING."""
    case = _Case(record=False)
    case.deliver_success()

    case.assert_hard_failure(CATALOG_METADATA_MISSING)
    assert "No catalog-metadata record" in case.stage.error_summary


def test_missing_metadata_file_fails_stage_and_job():
    """Row exists but the file is gone (artifacts deleted, DB kept)."""
    case = _Case(content=None)
    case.deliver_success()

    case.assert_hard_failure(CATALOG_METADATA_MISSING)
    summary = case.stage.error_summary
    assert "catalog/abcdef123456/catalog-metadata.bin" in summary
    assert "PostgreSQL was retained" in summary
    assert "Submit a new job" in summary


def test_missing_metadata_file_distinguished_from_missing_record():
    """The two missing cases carry different, specific summaries."""
    no_record, no_file = _Case(record=False), _Case(content=None)
    no_record.deliver_success()
    no_file.deliver_success()

    assert no_record.stage.error_summary != no_file.stage.error_summary
    assert "referenced in the database" in no_file.stage.error_summary


def test_invalid_json_metadata_fails_stage():
    """Corrupt metadata content -> CATALOG_METADATA_INVALID."""
    case = _Case(content=b"{not json")
    case.deliver_success()

    case.assert_hard_failure(CATALOG_METADATA_INVALID)


@pytest.mark.parametrize("payload", [
    [],
    {"roles": ["a"]},
    {"image_group_id": "g", "role_images": ["a.img"]},
])
def test_metadata_without_required_fields_fails_stage(payload):
    """Metadata lacking an image-group id or a role mapping is invalid."""
    case = _Case(content=json.dumps(payload).encode("utf-8"))
    case.deliver_success()

    case.assert_hard_failure(CATALOG_METADATA_INVALID)


def test_unreadable_metadata_file_fails_stage():
    """A storage error while reading is reported, not treated as success."""
    case = _Case(store_error=PermissionError("permission denied"))
    case.deliver_success()

    case.assert_hard_failure(IMAGE_GROUP_REGISTRATION_FAILED)
    assert "permission denied" in case.stage.error_summary


def test_metadata_lookup_error_fails_stage():
    """A database error while looking up the record fails the stage."""
    case = _Case(lookup_error=RuntimeError("database is down"))
    case.deliver_success()

    case.assert_hard_failure(IMAGE_GROUP_REGISTRATION_FAILED)
    assert case.session.rollbacks >= 1


@patch("orchestrator.common.result_poller._discover_s3_image_paths",
       side_effect=_discovered)
def test_database_error_on_persist_rolls_back_and_fails(mock_discover):
    """A persistence error rolls the shared session back and fails the stage."""
    case = _Case(image_error=RuntimeError("insert failed"))
    case.deliver_success()

    assert case.stage.stage_state == StageState.FAILED
    assert case.stage.error_code == IMAGE_GROUP_REGISTRATION_FAILED
    assert case.job.job_state == JobState.FAILED
    assert case.session.rollbacks >= 1
    assert case.session.commits == 0


@patch("orchestrator.common.result_poller._discover_s3_image_paths",
       side_effect=_discovered)
def test_image_group_owned_by_another_job_fails_stage(mock_discover):
    """A duplicate ImageGroup from a different job is a registration failure."""
    case = _Case()
    case.ig_repo.groups[GROUP_ID] = ImageGroup(
        id=ImageGroupId(GROUP_ID),
        job_id=JobId(str(uuid.uuid4())),
        status=ImageGroupStatus.BUILT,
    )

    case.deliver_success()

    assert case.stage.stage_state == StageState.FAILED
    assert case.stage.error_code == IMAGE_GROUP_REGISTRATION_FAILED
    assert case.job.job_state == JobState.FAILED
    assert "conflicts with an existing record" in case.stage.error_summary


def test_failed_build_image_result_is_unchanged():
    """A failed playbook result still fails the stage with its own code."""
    case = _Case(record=False)
    case.poller._on_result_received(PlaybookResult(
        job_id=str(case.job_id),
        stage_name="build-image",
        request_id=str(uuid.uuid4()),
        status="failed",
        exit_code=2,
        error_code="PLAYBOOK_FAILED",
        error_summary="build failed",
    ))

    assert case.stage.stage_state == StageState.FAILED
    assert case.stage.error_code == "PLAYBOOK_FAILED"
    assert case.job.job_state == JobState.FAILED
