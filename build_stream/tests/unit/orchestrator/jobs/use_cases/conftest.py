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

"""Shared fixtures for use case tests."""

import uuid
from typing import Optional, List, Dict

import pytest

from build_stream.core.jobs.entities import Job, Stage, IdempotencyRecord, AuditEvent
from build_stream.core.jobs.value_objects import JobId, IdempotencyKey, StageName
from build_stream.core.jobs.repositories import JobIdGenerator, UUIDGenerator


class FakeJobRepository:
    """In-memory fake implementation of JobRepository."""
    def __init__(self) -> None:
        """Initialize the fake repository."""
        self._jobs: Dict[str, Job] = {}

    def save(self, job: Job) -> None:
        """Save a job to the fake repository."""
        self._jobs[str(job.job_id)] = job

    def find_by_id(self, job_id: JobId) -> Optional[Job]:
        """Find a job by its ID."""
        return self._jobs.get(str(job_id))

    def exists(self, job_id: JobId) -> bool:
        """Check if a job exists."""
        return str(job_id) in self._jobs


class FakeStageRepository:
    """In-memory fake implementation of StageRepository."""
    def __init__(self) -> None:
        """Initialize the fake repository."""
        self._stages: Dict[str, Stage] = {}

    def save(self, stage: Stage) -> None:
        """Save a stage to the fake repository."""
        key = f"{stage.job_id}:{stage.stage_name}"
        self._stages[key] = stage

    def save_all(self, stages: List[Stage]) -> None:
        """Save multiple stages to the fake repository."""
        for stage in stages:
            self.save(stage)

    def find_by_job_and_name(
        self,
        job_id: JobId,
        stage_name: StageName
    ) -> Optional[Stage]:
        """Find a stage by job ID and stage name."""
        key = f"{job_id}:{stage_name}"
        return self._stages.get(key)

    def find_all_by_job(self, job_id: JobId) -> List[Stage]:
        """Find all stages for a given job ID."""
        return [
            stage for stage in self._stages.values()
            if str(stage.job_id) == str(job_id)
        ]


class FakeIdempotencyRepository:
    """In-memory fake implementation of IdempotencyRepository."""
    def __init__(self) -> None:
        """Initialize the fake repository."""
        self._records: Dict[str, IdempotencyRecord] = {}

    def save(self, record: IdempotencyRecord) -> None:
        """Save an idempotency record."""
        self._records[str(record.idempotency_key)] = record

    def find_by_key(self, key: IdempotencyKey) -> Optional[IdempotencyRecord]:
        """Find an idempotency record by its key."""
        return self._records.get(str(key))


class FakeAuditEventRepository:
    """In-memory fake implementation of AuditEventRepository."""
    def __init__(self) -> None:
        """Initialize the fake repository."""
        self._events: List[AuditEvent] = []

    def save(self, event: AuditEvent) -> None:
        """Save an audit event."""
        self._events.append(event)

    def find_by_job(self, job_id: JobId) -> List[AuditEvent]:
        """Find all audit events for a given job ID."""
        return [
            event for event in self._events
            if str(event.job_id) == str(job_id)
        ]


class FakeJobIdGenerator(JobIdGenerator):
    """Fake JobId generator for testing."""
    def __init__(self):
        """Initialize the fake generator."""
        self._counter = 1

    def generate(self) -> JobId:
        """Generate a predictable JobId for testing."""
        job_id = f"018e1234-5678-7abc-9def-123456789{self._counter:03d}"
        self._counter += 1
        return JobId(job_id)


class FakeUUIDGenerator(UUIDGenerator):
    """Fake UUID generator for testing."""
    def __init__(self):
        """Initialize the fake generator."""
        self._counter = 1

    def generate(self) -> uuid.UUID:
        """Generate a predictable UUID for testing."""
        uuid_str = f"123e4567-e89b-12d3-a456-426614174{self._counter:03d}"
        self._counter += 1
        return uuid.UUID(uuid_str)


@pytest.fixture
def job_repo():
    """Provide fake job repository."""
    return FakeJobRepository()


@pytest.fixture
def stage_repo():
    """Provide fake stage repository."""
    return FakeStageRepository()


@pytest.fixture
def idempotency_repo():
    """Provide fake idempotency repository."""
    return FakeIdempotencyRepository()


@pytest.fixture
def audit_repo():
    """Provide fake audit event repository."""
    return FakeAuditEventRepository()


@pytest.fixture
def job_id_generator():
    """Provide fake JobId generator."""
    return FakeJobIdGenerator()


@pytest.fixture
def _job_id_generator():
    """Provide fake JobId generator (alias for job_id_generator)."""
    return FakeJobIdGenerator()


@pytest.fixture
def uuid_generator():
    """Provide fake UUID generator."""
    return FakeUUIDGenerator()
