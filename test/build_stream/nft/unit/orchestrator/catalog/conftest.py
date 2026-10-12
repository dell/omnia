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

# pylint: disable=W0621,W0611,R0903

"""Shared fixtures for catalog orchestrator tests."""

import uuid

import pytest

from core.jobs.entities import Job, Stage
from core.jobs.value_objects import (
    ClientId,
    CorrelationId,
    JobId,
    StageName,
    StageState,
    StageType,
)
from infra.artifact_store.in_memory_artifact_store import InMemoryArtifactStore
from infra.artifact_store.in_memory_artifact_metadata import (
    InMemoryArtifactMetadataRepository,
)
from infra.repositories import (
    InMemoryAuditEventRepository,
    InMemoryJobRepository,
    InMemoryStageRepository,
)


VALID_JOB_ID = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
VALID_CORRELATION_ID = "018f3c4b-2d9e-7d1a-8a2b-111111111111"


class FakeUUIDGenerator:
    """Deterministic UUID generator for tests."""

    def __init__(self) -> None:
        """Initialize the UUID generator with a counter starting at 0."""
        self._counter = 0

    def generate(self) -> uuid.UUID:
        """Generate a deterministic UUID based on an internal counter.

        Returns:
            A UUID with a predictable format for testing.
        """
        self._counter += 1
        return uuid.UUID(f"00000000-0000-4000-8000-{self._counter:012d}")


@pytest.fixture
def job_id() -> JobId:
    """Provide a valid JobId for testing.

    Returns:
        A JobId instance with a predefined valid UUID.
    """
    return JobId(VALID_JOB_ID)


@pytest.fixture
def correlation_id() -> CorrelationId:
    """Provide a valid CorrelationId for testing.

    Returns:
        A CorrelationId instance with a predefined valid UUID.
    """
    return CorrelationId(VALID_CORRELATION_ID)


@pytest.fixture
def job_repo() -> InMemoryJobRepository:
    """Provide an in-memory job repository for testing.

    Returns:
        An InMemoryJobRepository instance.
    """
    return InMemoryJobRepository()


@pytest.fixture
def stage_repo() -> InMemoryStageRepository:
    """Provide an in-memory stage repository for testing.

    Returns:
        An InMemoryStageRepository instance.
    """
    return InMemoryStageRepository()


@pytest.fixture
def audit_repo() -> InMemoryAuditEventRepository:
    """Provide an in-memory audit event repository for testing.

    Returns:
        An InMemoryAuditEventRepository instance.
    """
    return InMemoryAuditEventRepository()


@pytest.fixture
def artifact_store() -> InMemoryArtifactStore:
    """Provide an in-memory artifact store for testing.

    Returns:
        An InMemoryArtifactStore instance.
    """
    return InMemoryArtifactStore()


@pytest.fixture
def artifact_metadata_repo() -> InMemoryArtifactMetadataRepository:
    """Provide an in-memory artifact metadata repository for testing.

    Returns:
        An InMemoryArtifactMetadataRepository instance.
    """
    return InMemoryArtifactMetadataRepository()


@pytest.fixture
def uuid_generator() -> FakeUUIDGenerator:
    """Provide a deterministic UUID generator for testing.

    Returns:
        A FakeUUIDGenerator instance.
    """
    return FakeUUIDGenerator()


@pytest.fixture
def created_job(job_id) -> Job:  # pylint: disable=redefined-outer-name
    """A job in CREATED state."""
    return Job(
        job_id=job_id,
        client_id=ClientId("test-client"),
        request_client_id="test-client",
    )


@pytest.fixture
def in_progress_job(job_id) -> Job:  # pylint: disable=redefined-outer-name
    """A job in IN_PROGRESS state."""
    job = Job(
        job_id=job_id,
        client_id=ClientId("test-client"),
        request_client_id="test-client",
    )
    job.start()
    return job


@pytest.fixture
def parse_catalog_stage(job_id) -> Stage:  # pylint: disable=redefined-outer-name
    """A parse-catalog stage in PENDING state."""
    return Stage(
        job_id=job_id,
        stage_name=StageName(StageType.PARSE_CATALOG.value),
        stage_state=StageState.PENDING,
    )


@pytest.fixture
def completed_parse_catalog_stage(job_id) -> Stage:  # pylint: disable=redefined-outer-name
    """A parse-catalog stage in COMPLETED state."""
    stage = Stage(
        job_id=job_id,
        stage_name=StageName(StageType.PARSE_CATALOG.value),
        stage_state=StageState.PENDING,
    )
    stage.start()
    stage.complete()
    return stage
