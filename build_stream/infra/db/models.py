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

"""SQLAlchemy ORM models for BuildStreaM persistence.

ORM models are infrastructure-only and never exposed outside this layer.
Domain ↔ ORM conversion is handled by mappers in mappers.py.
"""

# Third-party imports
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class JobModel(Base):
    """ORM model for jobs table.

    Maps to Job domain entity via JobMapper.
    """

    __tablename__ = "jobs"

    # Primary key
    job_id = Column(String(36), primary_key=True, nullable=False)

    # Business attributes
    client_id = Column(String(128), nullable=False, index=True)
    request_client_id = Column(String(128), nullable=False)
    client_name = Column(String(128), nullable=True)
    job_state = Column(String(20), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    # Optimistic locking
    version = Column(Integer, nullable=False, default=1)

    # Soft delete
    tombstoned = Column(Boolean, nullable=False, default=False, index=True)

    # Relationships
    stages = relationship(
        "StageModel",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Composite indexes
    __table_args__ = (
        Index("ix_jobs_client_state", "client_id", "job_state"),
        Index("ix_jobs_created_tombstoned", "created_at", "tombstoned"),
    )


class StageModel(Base):
    """ORM model for job_stages table.

    Maps to Stage domain entity via StageMapper.
    Composite primary key: (job_id, stage_name).
    """

    __tablename__ = "job_stages"

    # Composite primary key
    job_id = Column(
        String(36),
        ForeignKey("jobs.job_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    stage_name = Column(String(30), primary_key=True, nullable=False)

    # Business attributes
    stage_state = Column(String(20), nullable=False, index=True)
    attempt = Column(Integer, nullable=False, default=1)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Error tracking
    error_code = Column(String(50), nullable=True)
    error_summary = Column(Text, nullable=True)

    # Optimistic locking
    version = Column(Integer, nullable=False, default=1)

    # Relationships
    job = relationship("JobModel", back_populates="stages")

    # Composite indexes
    __table_args__ = (
        Index("ix_stages_job_state", "job_id", "stage_state"),
    )


class IdempotencyKeyModel(Base):
    """ORM model for idempotency_keys table.

    Maps to IdempotencyRecord domain entity via IdempotencyRecordMapper.
    """

    __tablename__ = "idempotency_keys"

    # Primary key
    idempotency_key = Column(String(255), primary_key=True, nullable=False)

    # Business attributes
    job_id = Column(String(36), nullable=False, index=True)
    request_fingerprint = Column(String(64), nullable=False)
    client_id = Column(String(128), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Composite indexes
    __table_args__ = (
        Index("ix_idempotency_client_created", "client_id", "created_at"),
        Index("ix_idempotency_expires", "expires_at"),
    )


class AuditEventModel(Base):
    """ORM model for audit_events table.

    Maps to AuditEvent domain entity via AuditEventMapper.
    """

    __tablename__ = "audit_events"

    # Primary key
    event_id = Column(String(36), primary_key=True, nullable=False)

    # Business attributes
    job_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    correlation_id = Column(String(36), nullable=False, index=True)
    client_id = Column(String(128), nullable=False, index=True)

    # Timestamp
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Event details
    details = Column(JSONB, nullable=True)

    # Composite indexes
    __table_args__ = (
        Index("ix_audit_job_timestamp", "job_id", "timestamp"),
        Index("ix_audit_correlation", "correlation_id"),
        Index("ix_audit_client_timestamp", "client_id", "timestamp"),
    )


class ArtifactMetadata(Base):
    """
    SQLAlchemy model for artifact metadata storage.
    
    Maps to ArtifactRecord domain entity via SqlArtifactMetadataRepository.
    """

    __tablename__ = "artifact_metadata"

    # Primary key
    id = Column(String(36), primary_key=True, nullable=False)

    # Foreign key to jobs table
    job_id = Column(String(36), ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False, index=True)

    # Business attributes
    stage_name = Column(String(50), nullable=False)
    label = Column(String(100), nullable=False)
    artifact_ref = Column(JSONB, nullable=False)
    kind = Column(String(20), nullable=False)
    content_type = Column(String(100), nullable=False)
    tags = Column(JSONB, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Composite indexes
    __table_args__ = (
        Index("idx_artifact_metadata_job_id", "job_id"),
        Index("idx_artifact_metadata_job_label", "job_id", "label"),
    )
