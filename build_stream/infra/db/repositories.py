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

"""SQL repository implementations for BuildStreaM persistence.

These implement the repository Protocol ports defined in core/jobs/repositories.py
using SQLAlchemy ORM against PostgreSQL.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.jobs.entities.audit import AuditEvent
from core.jobs.entities.idempotency import IdempotencyRecord
from core.jobs.entities.job import Job
from core.jobs.entities.stage import Stage
from core.jobs.exceptions import OptimisticLockError
from core.jobs.value_objects import IdempotencyKey, JobId, StageName
from core.artifacts.ports import ArtifactMetadataRepository
from core.artifacts.entities import ArtifactRecord, ArtifactRef, ArtifactKind
from core.artifacts.value_objects import ArtifactKey, ArtifactDigest
from .mappers import (
    AuditEventMapper,
    IdempotencyRecordMapper,
    JobMapper,
    StageMapper,
)
from .models import AuditEventModel, IdempotencyKeyModel, JobModel, StageModel


class SqlJobRepository:
    """SQL implementation of JobRepository protocol."""

    def __init__(self, session: Session) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy session for database operations.
        """
        self.session = session

    def save(self, job: Job) -> None:
        """Persist a job aggregate.

        Uses upsert semantics: inserts if new, updates with optimistic
        locking if existing.

        Args:
            job: Job entity to persist.

        Raises:
            OptimisticLockError: If version conflict detected.
        """
        existing = self.session.get(JobModel, str(job.job_id))

        if existing:
            if existing.version != job.version - 1:
                raise OptimisticLockError(
                    entity_type="Job",
                    entity_id=str(job.job_id),
                    expected_version=job.version - 1,
                    actual_version=existing.version,
                )

            existing.client_id = str(job.client_id)
            existing.request_client_id = job.request_client_id
            existing.client_name = job.client_name
            existing.job_state = job.job_state.value
            existing.updated_at = job.updated_at
            existing.version = job.version
            existing.tombstoned = job.tombstoned
        else:
            job_model = JobMapper.to_orm(job)
            self.session.add(job_model)

        try:
            self.session.flush()
        except IntegrityError as exc:
            raise OptimisticLockError(
                entity_type="Job",
                entity_id=str(job.job_id),
                expected_version=job.version - 1,
                actual_version=-1,
            ) from exc

    def find_by_id(self, job_id: JobId) -> Optional[Job]:
        """Retrieve a job by its identifier.

        Args:
            job_id: Unique job identifier.

        Returns:
            Job entity if found, None otherwise.
        """
        job_model = self.session.get(JobModel, str(job_id))
        if job_model is None:
            return None
        return JobMapper.to_domain(job_model)

    def exists(self, job_id: JobId) -> bool:
        """Check if a job exists.

        Args:
            job_id: Unique job identifier.

        Returns:
            True if job exists, False otherwise.
        """
        stmt = select(JobModel.job_id).where(JobModel.job_id == str(job_id))
        result = self.session.execute(stmt).first()
        return result is not None


class SqlStageRepository:
    """SQL implementation of StageRepository protocol."""

    def __init__(self, session: Session) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy session for database operations.
        """
        self.session = session

    def save(self, stage: Stage) -> None:
        """Persist a single stage.

        Uses upsert semantics: inserts if new, updates with optimistic
        locking if existing.

        Args:
            stage: Stage entity to persist.

        Raises:
            OptimisticLockError: If version conflict detected.
        """
        stmt = select(StageModel).where(
            StageModel.job_id == str(stage.job_id),
            StageModel.stage_name == stage.stage_name.value,
        )
        existing = self.session.execute(stmt).scalar_one_or_none()
        
        if existing:
            if existing.version != stage.version - 1:
                raise OptimisticLockError(
                    entity_type="Stage",
                    entity_id=f"{stage.job_id}/{stage.stage_name.value}",
                    expected_version=stage.version - 1,
                    actual_version=existing.version,
                )

            existing.stage_state = stage.stage_state.value
            existing.attempt = stage.attempt
            existing.started_at = stage.started_at
            existing.ended_at = stage.ended_at
            existing.error_code = stage.error_code
            existing.error_summary = stage.error_summary
            existing.version = stage.version
        else:
            stage_model = StageMapper.to_orm(stage)
            self.session.add(stage_model)

        try:
            self.session.flush()
        except IntegrityError as exc:
            raise OptimisticLockError(
                entity_type="Stage",
                entity_id=f"{stage.job_id}/{stage.stage_name}",
                expected_version=stage.version - 1,
                actual_version=-1,
            ) from exc

    def save_all(self, stages: List[Stage]) -> None:
        """Persist multiple stages atomically.

        Args:
            stages: List of stage entities to persist.

        Raises:
            OptimisticLockError: If version conflict detected.
        """
        for stage in stages:
            self.save(stage)

    def find_by_job_and_name(
        self,
        job_id: JobId,
        stage_name: StageName,
    ) -> Optional[Stage]:
        """Retrieve a stage by job and stage name.

        Args:
            job_id: Parent job identifier.
            stage_name: Stage identifier.

        Returns:
            Stage entity if found, None otherwise.
        """
        stmt = select(StageModel).where(
            StageModel.job_id == str(job_id),
            StageModel.stage_name == str(stage_name),
        )
        stage_model = self.session.execute(stmt).scalar_one_or_none()
        if stage_model is None:
            return None
        return StageMapper.to_domain(stage_model)

    def find_all_by_job(self, job_id: JobId) -> List[Stage]:
        """Retrieve all stages for a job.

        Args:
            job_id: Parent job identifier.

        Returns:
            List of stage entities (may be empty).
        """
        stmt = (
            select(StageModel)
            .where(StageModel.job_id == str(job_id))
            .order_by(StageModel.stage_name)
        )
        stage_models = self.session.execute(stmt).scalars().all()
        return [StageMapper.to_domain(model) for model in stage_models]


class SqlIdempotencyRepository:
    """SQL implementation of IdempotencyRepository protocol."""

    def __init__(self, session: Session) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy session for database operations.
        """
        self.session = session

    def save(self, record: IdempotencyRecord) -> None:
        """Persist an idempotency record.

        Args:
            record: Idempotency record to persist.
        """
        record_model = IdempotencyRecordMapper.to_orm(record)
        self.session.merge(record_model)
        self.session.flush()

    def find_by_key(self, key: IdempotencyKey) -> Optional[IdempotencyRecord]:
        """Retrieve an idempotency record by key.

        Args:
            key: Idempotency key.

        Returns:
            IdempotencyRecord if found, None otherwise.
        """
        record_model = self.session.get(IdempotencyKeyModel, str(key))
        if record_model is None:
            return None
        return IdempotencyRecordMapper.to_domain(record_model)


class SqlAuditEventRepository:
    """SQL implementation of AuditEventRepository protocol."""

    def __init__(self, session: Session) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy session for database operations.
        """
        self.session = session

    def save(self, event: AuditEvent) -> None:
        """Persist an audit event.

        Args:
            event: Audit event to persist.
        """
        event_model = AuditEventMapper.to_orm(event)
        self.session.add(event_model)
        self.session.flush()

    def find_by_job(self, job_id: JobId) -> List[AuditEvent]:
        """Retrieve all audit events for a job.

        Args:
            job_id: Job identifier.

        Returns:
            List of audit events (may be empty).
        """
        stmt = (
            select(AuditEventModel)
            .where(AuditEventModel.job_id == str(job_id))
            .order_by(AuditEventModel.timestamp)
        )
        event_models = self.session.execute(stmt).scalars().all()
        return [AuditEventMapper.to_domain(model) for model in event_models]


class SqlArtifactMetadataRepository(ArtifactMetadataRepository):
    """SQL implementation of artifact metadata repository."""

    def __init__(self, session: Session):
        """Initialize with a SQLAlchemy session."""
        self._session = session

    def save(self, record: ArtifactRecord) -> None:
        """Save an artifact record to the database."""
        from infra.db.models import ArtifactMetadata
        
        db_record = ArtifactMetadata(
            id=record.id,
            job_id=str(record.job_id),
            stage_name=record.stage_name.value,
            label=record.label,
            artifact_ref={
                "key": str(record.artifact_ref.key),
                "digest": str(record.artifact_ref.digest),
                "size_bytes": record.artifact_ref.size_bytes,
                "uri": record.artifact_ref.uri,
            },
            kind=record.kind.value,
            content_type=record.content_type,
            tags=record.tags,
        )
        self._session.add(db_record)

    def get_by_job_id_and_label(
        self, job_id: JobId, label: str
    ) -> Optional[ArtifactRecord]:
        """Get artifact record by job ID and label."""
        from infra.db.models import ArtifactMetadata
        
        db_record = (
            self._session.query(ArtifactMetadata)
            .filter(
                ArtifactMetadata.job_id == str(job_id),
                ArtifactMetadata.label == label,
            )
            .first()
        )
        
        if not db_record:
            return None
            
        return self._db_record_to_entity(db_record)

    def find_by_job_stage_and_label(
        self,
        job_id: JobId,
        stage_name: StageName,
        label: str,
    ) -> Optional[ArtifactRecord]:
        """Find an artifact record by job, stage, and label."""
        from infra.db.models import ArtifactMetadata
        
        db_record = (
            self._session.query(ArtifactMetadata)
            .filter(
                ArtifactMetadata.job_id == str(job_id),
                ArtifactMetadata.stage_name == stage_name.value,
                ArtifactMetadata.label == label,
            )
            .first()
        )
        
        if not db_record:
            return None
            
        return self._db_record_to_entity(db_record)

    def list_by_job_id(self, job_id: JobId) -> List[ArtifactRecord]:
        """List all artifact records for a job."""
        from infra.db.models import ArtifactMetadata
        
        db_records = (
            self._session.query(ArtifactMetadata)
            .filter(ArtifactMetadata.job_id == str(job_id))
            .all()
        )
        
        return [self._db_record_to_entity(r) for r in db_records]

    def _db_record_to_entity(self, db_record) -> ArtifactRecord:
        """Convert database record to domain entity."""
        from infra.db.models import ArtifactMetadata
        
        artifact_ref_data = db_record.artifact_ref
        artifact_ref = ArtifactRef(
            key=ArtifactKey(artifact_ref_data["key"]),
            digest=ArtifactDigest(artifact_ref_data["digest"]),
            size_bytes=artifact_ref_data["size_bytes"],
            uri=artifact_ref_data["uri"],
        )
        
        return ArtifactRecord(
            id=db_record.id,
            job_id=JobId(db_record.job_id),
            stage_name=StageName(db_record.stage_name),
            label=db_record.label,
            artifact_ref=artifact_ref,
            kind=ArtifactKind(db_record.kind),
            content_type=db_record.content_type,
            tags=db_record.tags or {},
        )
