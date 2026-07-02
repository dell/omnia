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

"""Integration tests for SQL repositories against PostgreSQL."""

import os
import uuid
from datetime import datetime, timezone
from typing import Generator
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from core.jobs.entities.audit import AuditEvent
from core.jobs.entities.idempotency import IdempotencyRecord
from core.jobs.entities.job import Job
from core.jobs.entities.stage import Stage
from core.jobs.exceptions import OptimisticLockError
from core.jobs.value_objects import (
    ClientId,
    CorrelationId,
    IdempotencyKey,
    JobId,
    JobState,
    RequestFingerprint,
    StageName,
    StageState,
)
from infra.db.models import Base
from infra.db.repositories import (
    SqlAuditEventRepository,
    SqlIdempotencyRepository,
    SqlJobRepository,
    SqlStageRepository,
)
from infra.db.session import get_db_session


@pytest.fixture(scope="session")
def pg_url() -> str:
    """Get PostgreSQL URL from environment or use testcontainers."""
    # First try to get from environment (for manual testing)
    pg_url = os.getenv("TEST_DATABASE_URL")
    if pg_url:
        yield pg_url
        return

    # Fall back to testcontainers if available
    try:
        from testcontainers.postgres import PostgresContainer

        with PostgresContainer("postgres:15") as postgres:
            # Wait for container to be ready
            postgres.get_connection_url()
            yield postgres.get_connection_url()
            return
    except ImportError:
        pytest.skip("testcontainers-postgres not installed and TEST_DATABASE_URL not set")


@pytest.fixture
def db_engine(pg_url: str) -> Generator:
    """Create a fresh database for each test."""
    engine = create_engine(pg_url)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a database session for each test."""
    with db_engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection)
        yield session
        session.close()
        transaction.rollback()


@pytest.fixture
def job_repo(db_session: Session) -> SqlJobRepository:
    """Create SqlJobRepository instance."""
    return SqlJobRepository(db_session)


@pytest.fixture
def stage_repo(db_session: Session) -> SqlStageRepository:
    """Create SqlStageRepository instance."""
    return SqlStageRepository(db_session)


@pytest.fixture
def idempotency_repo(db_session: Session) -> SqlIdempotencyRepository:
    """Create SqlIdempotencyRepository instance."""
    return SqlIdempotencyRepository(db_session)


@pytest.fixture
def audit_repo(db_session: Session) -> SqlAuditEventRepository:
    """Create SqlAuditEventRepository instance."""
    return SqlAuditEventRepository(db_session)


class TestSqlJobRepository:
    """Test SqlJobRepository against PostgreSQL."""

    def test_save_and_find_by_id(self, job_repo: SqlJobRepository) -> None:
        """Save a job and retrieve it by ID."""
        job = Job(
            job_id=JobId("12345678-1234-5678-9abc-123456789abc"),
            client_id=ClientId("test-client"),
            request_client_id="request-123",
            client_name="Test Client",
            job_state=JobState.CREATED,
        )

        job_repo.save(job)
        found = job_repo.find_by_id(job.job_id)

        assert found is not None
        assert str(found.job_id) == str(job.job_id)
        assert str(found.client_id) == str(job.client_id)
        assert found.request_client_id == job.request_client_id
        assert found.client_name == job.client_name
        assert found.job_state == job.job_state
        assert found.version == 1

    def test_exists(self, job_repo: SqlJobRepository) -> None:
        """Check if a job exists."""
        job_id = JobId("12345678-1234-5678-9abc-123456789abc")
        assert not job_repo.exists(job_id)

        job = Job(
            job_id=job_id,
            client_id=ClientId("test-client"),
            request_client_id="request-123",
        )
        job_repo.save(job)

        assert job_repo.exists(job_id)

    def test_update_with_optimistic_locking(self, job_repo: SqlJobRepository) -> None:
        """Test optimistic locking on update."""
        job = Job(
            job_id=JobId("12345678-1234-5678-9abc-123456789abc"),
            client_id=ClientId("test-client"),
            request_client_id="request-123",
            job_state=JobState.CREATED,
        )
        job_repo.save(job)

        # Simulate concurrent update
        job.start()  # version becomes 2
        job_repo.save(job)

        # Try to save with stale version
        stale_job = Job(
            job_id=job.job_id,
            client_id=ClientId("test-client"),
            request_client_id="request-123",
            job_state=JobState.FAILED,  # Different state
            version=1,  # Stale version
        )

        with pytest.raises(OptimisticLockError) as exc_info:
            job_repo.save(stale_job)

        assert "Version conflict for Job" in str(exc_info.value)
        assert exc_info.value.expected_version == 0  # stale version - 1
        assert exc_info.value.actual_version == 2

    def test_find_by_id_not_found(self, job_repo: SqlJobRepository) -> None:
        """Return None when job doesn't exist."""
        found = job_repo.find_by_id(JobId("00000000-0000-0000-0000-000000000000"))
        assert found is None


class TestSqlStageRepository:
    """Test SqlStageRepository against PostgreSQL."""

    def test_save_and_find_by_job_and_name(
        self, stage_repo: SqlStageRepository, job_repo: SqlJobRepository
    ) -> None:
        """Save a stage and retrieve it."""
        # First create a job to satisfy foreign key constraint
        job = Job(
            job_id=JobId("12345678-1234-5678-9abc-123456789abc"),
            client_id=ClientId("test-client"),
            request_client_id="request-123",
        )
        job_repo.save(job)
        
        stage = Stage(
            job_id=JobId("12345678-1234-5678-9abc-123456789abc"),
            stage_name=StageName("parse-catalog"),
            stage_state=StageState.IN_PROGRESS,
            attempt=1,
        )

        stage_repo.save(stage)
        found = stage_repo.find_by_job_and_name(stage.job_id, stage.stage_name)

        assert found is not None
        assert str(found.job_id) == str(stage.job_id)
        assert str(found.stage_name) == str(stage.stage_name)
        assert found.stage_state == stage.stage_state
        assert found.attempt == stage.attempt

    def test_save_all_and_find_all_by_job(
        self, stage_repo: SqlStageRepository, job_repo: SqlJobRepository
    ) -> None:
        """Save multiple stages and retrieve all for a job."""
        job_id = JobId("12345678-1234-5678-9abc-123456789abc")
        
        # First create a job to satisfy foreign key constraint
        job = Job(
            job_id=job_id,
            client_id=ClientId("test-client"),
            request_client_id="request-123",
        )
        job_repo.save(job)
        
        stages = [
            Stage(
                job_id=job_id,
                stage_name=StageName("parse-catalog"),
                stage_state=StageState.COMPLETED,
            ),
            Stage(
                job_id=job_id,
                stage_name=StageName("generate-input-files"),
                stage_state=StageState.PENDING,
            ),
            Stage(
                job_id=job_id,
                stage_name=StageName("create-local-repository"),
                stage_state=StageState.PENDING,
            ),
        ]

        stage_repo.save_all(stages)
        found_stages = stage_repo.find_all_by_job(job_id)

        assert len(found_stages) == 3
        stage_names = [str(s.stage_name) for s in found_stages]
        assert "parse-catalog" in stage_names
        assert "generate-input-files" in stage_names
        assert "create-local-repository" in stage_names
        # Verify ordering by stage_name
        assert stage_names == sorted(stage_names)

    def test_update_with_optimistic_locking(
        self, stage_repo: SqlStageRepository, job_repo: SqlJobRepository
    ) -> None:
        """Test optimistic locking on stage update."""
        # First create a job to satisfy foreign key constraint
        job = Job(
            job_id=JobId("12345678-1234-5678-9abc-123456789abc"),
            client_id=ClientId("test-client"),
            request_client_id="request-123",
        )
        job_repo.save(job)
        
        stage = Stage(
            job_id=JobId("12345678-1234-5678-9abc-123456789abc"),
            stage_name=StageName("parse-catalog"),
            stage_state=StageState.PENDING,
            version=1,
        )
        stage_repo.save(stage)

        # Update successfully
        stage.start()  # version becomes 2
        stage_repo.save(stage)

        # Try to save with stale version
        stale_stage = Stage(
            job_id=stage.job_id,
            stage_name=stage.stage_name,
            stage_state=StageState.FAILED,
            version=1,  # Stale
        )

        with pytest.raises(OptimisticLockError) as exc_info:
            stage_repo.save(stale_stage)

        assert "Version conflict for Stage" in str(exc_info.value)


class TestSqlIdempotencyRepository:
    """Test SqlIdempotencyRepository against PostgreSQL."""

    def test_save_and_find_by_key(
        self, idempotency_repo: SqlIdempotencyRepository
    ) -> None:
        """Save and retrieve idempotency record."""
        record = IdempotencyRecord(
            idempotency_key=IdempotencyKey("unique-key-123"),
            job_id=JobId("12345678-1234-5678-9abc-123456789abc"),
            request_fingerprint=RequestFingerprint("a" * 64),
            client_id=ClientId("test-client"),
            created_at=datetime(2026, 1, 26, 10, 0),
            expires_at=datetime(2026, 1, 26, 11, 0),
        )

        idempotency_repo.save(record)
        found = idempotency_repo.find_by_key(record.idempotency_key)

        assert found is not None
        assert str(found.idempotency_key) == str(record.idempotency_key)
        assert str(found.job_id) == str(record.job_id)
        assert str(found.request_fingerprint) == str(record.request_fingerprint)
        assert str(found.client_id) == str(record.client_id)

    def test_find_by_key_not_found(
        self, idempotency_repo: SqlIdempotencyRepository
    ) -> None:
        """Return None when key doesn't exist."""
        found = idempotency_repo.find_by_key(IdempotencyKey("non-existent"))
        assert found is None


class TestSqlAuditEventRepository:
    """Test SqlAuditEventRepository against PostgreSQL."""

    def test_save_and_find_by_job(self, audit_repo: SqlAuditEventRepository) -> None:
        """Save audit events and retrieve all for a job."""
        job_id = JobId("12345678-1234-5678-9abc-123456789abc")
        events = [
            AuditEvent(
                event_id=str(uuid.uuid4()),
                job_id=job_id,
                event_type="job_created",
                correlation_id=CorrelationId("11111111-1111-1111-1111-111111111111"),
                client_id=ClientId("test-client"),
                timestamp=datetime(2026, 1, 26, 10, 0),
            ),
            AuditEvent(
                event_id=str(uuid.uuid4()),
                job_id=job_id,
                event_type="stage_completed",
                correlation_id=CorrelationId("22222222-2222-2222-2222-222222222222"),
                client_id=ClientId("test-client"),
                timestamp=datetime(2026, 1, 26, 10, 30),
                details={"stage": "parse-catalog"},
            ),
        ]

        for event in events:
            audit_repo.save(event)

        found_events = audit_repo.find_by_job(job_id)

        assert len(found_events) == 2
        event_types = [e.event_type for e in found_events]
        assert "job_created" in event_types
        assert "stage_completed" in event_types
        # Verify chronological order
        assert found_events[0].timestamp < found_events[1].timestamp


class TestDatabaseConstraints:
    """Test database constraints and relationships."""

    def test_foreign_key_cascade_delete(
        self, db_session: Session, job_repo: SqlJobRepository, stage_repo: SqlStageRepository
    ) -> None:
        """Test that deleting a job cascades to stages."""
        job = Job(
            job_id=JobId("12345678-1234-5678-9abc-123456789abc"),
            client_id=ClientId("test-client"),
            request_client_id="request-123",
        )
        job_repo.save(job)

        stage = Stage(
            job_id=job.job_id,
            stage_name=StageName("parse-catalog"),
            stage_state=StageState.PENDING,
        )
        stage_repo.save(stage)

        # Verify stage exists
        found = stage_repo.find_by_job_and_name(job.job_id, stage.stage_name)
        assert found is not None

        # Delete the job (simulating cascade)
        # Use a transaction to test the cascade
        db_session.begin_nested()
        db_session.execute(text("DELETE FROM jobs WHERE job_id = :job_id"), {"job_id": str(job.job_id)})
        db_session.flush()  # Ensure the delete is executed
        
        # Stage should be deleted by cascade
        found = stage_repo.find_by_job_and_name(job.job_id, stage.stage_name)
        assert found is None
        
        # Rollback the nested transaction
        db_session.rollback()

    def test_unique_constraint_on_stages(
        self, db_session: Session, stage_repo: SqlStageRepository, job_repo: SqlJobRepository
    ) -> None:
        """Test that stage_name is unique within a job."""
        job_id = JobId("12345678-1234-5678-9abc-123456789abc")
        
        # First create a job to satisfy foreign key constraint
        job = Job(
            job_id=job_id,
            client_id=ClientId("test-client"),
            request_client_id="request-123",
        )
        job_repo.save(job)
        
        stage = Stage(
            job_id=job_id,
            stage_name=StageName("parse-catalog"),
            stage_state=StageState.PENDING,
        )
        stage_repo.save(stage)

        # Try to insert duplicate (update with correct version)
        duplicate = Stage(
            job_id=job_id,
            stage_name=StageName("parse-catalog"),
            stage_state=StageState.IN_PROGRESS,
            version=2,  # Incremented version for update
        )

        # Should update instead of error due to upsert logic
        stage_repo.save(duplicate)
        found = stage_repo.find_by_job_and_name(job_id, StageName("parse-catalog"))
        assert found.stage_state == StageState.IN_PROGRESS
