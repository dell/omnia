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

"""Mappers for domain ↔ ORM model conversion.

Explicit mapping between domain entities and ORM models.
No domain logic lives here — only data transformation.
"""

from typing import Dict, Any

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
from .models import AuditEventModel, IdempotencyKeyModel, JobModel, StageModel


class JobMapper:
    """Mapper for Job entity ↔ JobModel ORM."""

    @staticmethod
    def to_orm(job: Job) -> JobModel:
        """Convert Job domain entity to ORM model.

        Args:
            job: Job domain entity.

        Returns:
            JobModel ORM instance.
        """
        return JobModel(
            job_id=str(job.job_id),
            client_id=str(job.client_id),
            request_client_id=job.request_client_id,
            client_name=job.client_name,
            job_state=job.job_state.value,
            created_at=job.created_at,
            updated_at=job.updated_at,
            version=job.version,
            tombstoned=job.tombstoned,
        )

    @staticmethod
    def to_domain(model: JobModel) -> Job:
        """Convert JobModel ORM to Job domain entity.

        Args:
            model: JobModel ORM instance.

        Returns:
            Job domain entity.
        """
        return Job(
            job_id=JobId(model.job_id),
            client_id=ClientId(model.client_id),
            request_client_id=model.request_client_id,
            client_name=model.client_name,
            job_state=JobState(model.job_state),
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            tombstoned=model.tombstoned,
        )


class StageMapper:
    """Mapper for Stage entity ↔ StageModel ORM."""

    @staticmethod
    def to_orm(stage: Stage) -> StageModel:
        """Convert Stage domain entity to ORM model.

        Args:
            stage: Stage domain entity.

        Returns:
            StageModel ORM instance.
        """
        return StageModel(
            job_id=str(stage.job_id),
            stage_name=stage.stage_name.value,
            stage_state=stage.stage_state.value,
            attempt=stage.attempt,
            started_at=stage.started_at,
            ended_at=stage.ended_at,
            error_code=stage.error_code,
            error_summary=stage.error_summary,
            version=stage.version,
        )

    @staticmethod
    def to_domain(model: StageModel) -> Stage:
        """Convert StageModel ORM to Stage domain entity.

        Args:
            model: StageModel ORM instance.

        Returns:
            Stage domain entity.
        """
        return Stage(
            job_id=JobId(model.job_id),
            stage_name=StageName(model.stage_name),
            stage_state=StageState(model.stage_state),
            attempt=model.attempt,
            started_at=model.started_at,
            ended_at=model.ended_at,
            error_code=model.error_code,
            error_summary=model.error_summary,
            version=model.version,
        )


class IdempotencyRecordMapper:
    """Mapper for IdempotencyRecord entity ↔ IdempotencyKeyModel ORM."""

    @staticmethod
    def to_orm(record: IdempotencyRecord) -> IdempotencyKeyModel:
        """Convert IdempotencyRecord domain entity to ORM model.

        Args:
            record: IdempotencyRecord domain entity.

        Returns:
            IdempotencyKeyModel ORM instance.
        """
        return IdempotencyKeyModel(
            idempotency_key=str(record.idempotency_key),
            job_id=str(record.job_id),
            request_fingerprint=str(record.request_fingerprint),
            client_id=str(record.client_id),
            created_at=record.created_at,
            expires_at=record.expires_at,
        )

    @staticmethod
    def to_domain(model: IdempotencyKeyModel) -> IdempotencyRecord:
        """Convert IdempotencyKeyModel ORM to IdempotencyRecord domain entity.

        Args:
            model: IdempotencyKeyModel ORM instance.

        Returns:
            IdempotencyRecord domain entity.
        """
        return IdempotencyRecord(
            idempotency_key=IdempotencyKey(model.idempotency_key),
            job_id=JobId(model.job_id),
            request_fingerprint=RequestFingerprint(model.request_fingerprint),
            client_id=ClientId(model.client_id),
            created_at=model.created_at,
            expires_at=model.expires_at,
        )


class AuditEventMapper:
    """Mapper for AuditEvent entity ↔ AuditEventModel ORM."""

    @staticmethod
    def to_orm(event: AuditEvent) -> AuditEventModel:
        """Convert AuditEvent domain entity to ORM model.

        Args:
            event: AuditEvent domain entity.

        Returns:
            AuditEventModel ORM instance.
        """
        return AuditEventModel(
            event_id=event.event_id,
            job_id=str(event.job_id),
            event_type=event.event_type,
            correlation_id=str(event.correlation_id),
            client_id=str(event.client_id),
            timestamp=event.timestamp,
            details=event.details if event.details else None,
        )

    @staticmethod
    def to_domain(model: AuditEventModel) -> AuditEvent:
        """Convert AuditEventModel ORM to AuditEvent domain entity.

        Args:
            model: AuditEventModel ORM instance.

        Returns:
            AuditEvent domain entity.
        """
        return AuditEvent(
            event_id=model.event_id,
            job_id=JobId(model.job_id),
            event_type=model.event_type,
            correlation_id=CorrelationId(model.correlation_id),
            client_id=ClientId(model.client_id),
            timestamp=model.timestamp,
            details=model.details if model.details else {},
        )
