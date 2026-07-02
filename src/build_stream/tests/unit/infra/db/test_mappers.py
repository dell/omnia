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

"""Unit tests for mappers."""

import pytest
from datetime import datetime, timezone

from core.jobs.entities.audit import AuditEvent
from core.jobs.entities.idempotency import IdempotencyRecord
from core.jobs.entities.job import Job
from core.jobs.entities.stage import Stage
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
from infra.db.mappers import (
    AuditEventMapper,
    IdempotencyRecordMapper,
    JobMapper,
    StageMapper,
)
from infra.db.models import AuditEventModel, IdempotencyKeyModel, JobModel, StageModel


class TestJobMapper:
    """Test Job entity ↔ JobModel mapping."""

    def test_to_orm(self) -> None:
        """Convert domain entity to ORM model."""
        job = Job(
            job_id=JobId("12345678-1234-5678-9abc-123456789abc"),
            client_id=ClientId("test-client"),
            request_client_id="request-client-123",
            client_name="Test Client",
            job_state=JobState.IN_PROGRESS,
            created_at=datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 26, 10, 30, tzinfo=timezone.utc),
            version=2,
            tombstoned=False,
        )

        model = JobMapper.to_orm(job)

        assert model.job_id == "12345678-1234-5678-9abc-123456789abc"
        assert model.client_id == "test-client"
        assert model.request_client_id == "request-client-123"
        assert model.client_name == "Test Client"
        assert model.job_state == "IN_PROGRESS"
        assert model.created_at == datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc)
        assert model.updated_at == datetime(2026, 1, 26, 10, 30, tzinfo=timezone.utc)
        assert model.version == 2
        assert model.tombstoned is False

    def test_to_domain(self) -> None:
        """Convert ORM model to domain entity."""
        model = JobModel(
            job_id="12345678-1234-5678-9abc-123456789abc",
            client_id="test-client",
            request_client_id="request-client-123",
            client_name="Test Client",
            job_state="IN_PROGRESS",
            created_at=datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 26, 10, 30, tzinfo=timezone.utc),
            version=2,
            tombstoned=False,
        )

        job = JobMapper.to_domain(model)

        assert str(job.job_id) == "12345678-1234-5678-9abc-123456789abc"
        assert str(job.client_id) == "test-client"
        assert job.request_client_id == "request-client-123"
        assert job.client_name == "Test Client"
        assert job.job_state == JobState.IN_PROGRESS
        assert job.created_at == datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc)
        assert job.updated_at == datetime(2026, 1, 26, 10, 30, tzinfo=timezone.utc)
        assert job.version == 2
        assert job.tombstoned is False

    def test_roundtrip(self) -> None:
        """Roundtrip conversion preserves all data."""
        original = Job(
            job_id=JobId("12345678-1234-5678-9abc-123456789abc"),
            client_id=ClientId("test-client"),
            request_client_id="request-client-123",
            client_name=None,  # Test nullable field
            job_state=JobState.COMPLETED,
            created_at=datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 26, 11, 0, tzinfo=timezone.utc),
            version=5,
            tombstoned=True,
        )

        model = JobMapper.to_orm(original)
        converted = JobMapper.to_domain(model)

        assert str(converted.job_id) == str(original.job_id)
        assert str(converted.client_id) == str(original.client_id)
        assert converted.request_client_id == original.request_client_id
        assert converted.client_name == original.client_name
        assert converted.job_state == original.job_state
        assert converted.created_at == original.created_at
        assert converted.updated_at == original.updated_at
        assert converted.version == original.version
        assert converted.tombstoned == original.tombstoned


class TestStageMapper:
    """Test Stage entity ↔ StageModel mapping."""

    def test_to_orm(self) -> None:
        """Convert domain entity to ORM model."""
        stage = Stage(
            job_id=JobId("12345678-1234-5678-9abc-123456789abc"),
            stage_name=StageName("parse-catalog"),
            stage_state=StageState.FAILED,
            attempt=2,
            started_at=datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 1, 26, 10, 30, tzinfo=timezone.utc),
            error_code="TIMEOUT",
            error_summary="Stage timed out after 30 minutes",
            version=3,
        )

        model = StageMapper.to_orm(stage)

        assert model.job_id == "12345678-1234-5678-9abc-123456789abc"
        assert model.stage_name == "parse-catalog"
        assert model.stage_state == "FAILED"
        assert model.attempt == 2
        assert model.started_at == datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc)
        assert model.ended_at == datetime(2026, 1, 26, 10, 30, tzinfo=timezone.utc)
        assert model.error_code == "TIMEOUT"
        assert model.error_summary == "Stage timed out after 30 minutes"
        assert model.version == 3

    def test_to_domain(self) -> None:
        """Convert ORM model to domain entity."""
        model = StageModel(
            job_id="12345678-1234-5678-9abc-123456789abc",
            stage_name="parse-catalog",
            stage_state="FAILED",
            attempt=2,
            started_at=datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 1, 26, 10, 30, tzinfo=timezone.utc),
            error_code="TIMEOUT",
            error_summary="Stage timed out after 30 minutes",
            version=3,
        )

        stage = StageMapper.to_domain(model)

        assert str(stage.job_id) == "12345678-1234-5678-9abc-123456789abc"
        assert str(stage.stage_name) == "parse-catalog"
        assert stage.stage_state == StageState.FAILED
        assert stage.attempt == 2
        assert stage.started_at == datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc)
        assert stage.ended_at == datetime(2026, 1, 26, 10, 30, tzinfo=timezone.utc)
        assert stage.error_code == "TIMEOUT"
        assert stage.error_summary == "Stage timed out after 30 minutes"
        assert stage.version == 3


class TestIdempotencyRecordMapper:
    """Test IdempotencyRecord entity ↔ IdempotencyKeyModel mapping."""

    def test_to_orm(self) -> None:
        """Convert domain entity to ORM model."""
        record = IdempotencyRecord(
            idempotency_key=IdempotencyKey("unique-key-123"),
            job_id=JobId("12345678-1234-5678-9abc-123456789abc"),
            request_fingerprint=RequestFingerprint("a" * 64),
            client_id=ClientId("test-client"),
            created_at=datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc),
            expires_at=datetime(2026, 1, 26, 11, 0, tzinfo=timezone.utc),
        )

        model = IdempotencyRecordMapper.to_orm(record)

        assert model.idempotency_key == "unique-key-123"
        assert model.job_id == "12345678-1234-5678-9abc-123456789abc"
        assert model.request_fingerprint == "a" * 64
        assert model.client_id == "test-client"
        assert model.created_at == datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc)
        assert model.expires_at == datetime(2026, 1, 26, 11, 0, tzinfo=timezone.utc)


class TestAuditEventMapper:
    """Test AuditEvent entity ↔ AuditEventModel mapping."""

    def test_to_orm_with_details(self) -> None:
        """Convert domain entity to ORM model with details."""
        event = AuditEvent(
            event_id="12345678-1234-5678-9abc-123456789abc",
            job_id=JobId("12345678-1234-5678-9abc-123456789abc"),
            event_type="job_created",
            correlation_id=CorrelationId("87654321-4321-8765-cba9-876543210cba"),
            client_id=ClientId("test-client"),
            timestamp=datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc),
            details={"stage": "parse-catalog", "duration_ms": 5000},
        )

        model = AuditEventMapper.to_orm(event)

        assert model.event_id == "12345678-1234-5678-9abc-123456789abc"
        assert model.job_id == "12345678-1234-5678-9abc-123456789abc"
        assert model.event_type == "job_created"
        assert model.correlation_id == "87654321-4321-8765-cba9-876543210cba"
        assert model.client_id == "test-client"
        assert model.timestamp == datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc)
        assert model.details == {"stage": "parse-catalog", "duration_ms": 5000}

    def test_to_orm_without_details(self) -> None:
        """Convert domain entity to ORM model without details."""
        event = AuditEvent(
            event_id="12345678-1234-5678-9abc-123456789abc",
            job_id=JobId("12345678-1234-5678-9abc-123456789abc"),
            event_type="job_created",
            correlation_id=CorrelationId("87654321-4321-8765-cba9-876543210cba"),
            client_id=ClientId("test-client"),
            timestamp=datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc),
        )

        model = AuditEventMapper.to_orm(event)

        assert model.details is None

    def test_to_domain_with_null_details(self) -> None:
        """Convert ORM model to domain entity with null details."""
        model = AuditEventModel(
            event_id="12345678-1234-5678-9abc-123456789abc",
            job_id="12345678-1234-5678-9abc-123456789abc",
            event_type="job_created",
            correlation_id="87654321-4321-8765-cba9-876543210cba",
            client_id="test-client",
            timestamp=datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc),
            details=None,
        )

        event = AuditEventMapper.to_domain(model)

        assert event.details == {}
