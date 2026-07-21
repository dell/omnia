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

"""Test-specific database models with SQLite-compatible types."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    JSON,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Job(Base):
    """Job model."""

    __tablename__ = "jobs"

    # Primary key
    job_id = Column(String(36), primary_key=True)

    # Business attributes
    client_id = Column(String(128), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    stages = relationship("Stage", back_populates="job", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="job", cascade="all, delete-orphan")
    idempotency_records = relationship("IdempotencyRecord", back_populates="job", cascade="all, delete-orphan")
    artifact_records = relationship("ArtifactRecord", back_populates="job", cascade="all, delete-orphan")


class Stage(Base):
    """Stage model."""

    __tablename__ = "stages"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key
    job_id = Column(String(36), ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False, index=True)

    # Business attributes
    stage_name = Column(String(50), nullable=False)
    stage_state = Column(String(20), nullable=False)
    error_code = Column(String(100), nullable=True)
    error_summary = Column(String(256), nullable=True)
    error_details = Column(Text, nullable=True)

    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    job = relationship("Job", back_populates="stages")

    # Composite indexes
    __table_args__ = (
        Index("ix_stage_job_name", "job_id", "stage_name"),
        Index("ix_stage_state", "stage_state"),
    )


class AuditEvent(Base):
    """Audit event model."""

    __tablename__ = "audit_events"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key
    job_id = Column(String(36), ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False, index=True)

    # Business attributes
    event_type = Column(String(50), nullable=False)
    correlation_id = Column(String(36), nullable=True)

    # Timestamp
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Event details
    details = Column(JSON, nullable=True)

    # Composite indexes
    __table_args__ = (
        Index("ix_audit_job_timestamp", "job_id", "timestamp"),
        Index("ix_audit_correlation", "correlation_id"),
    )

    # Relationships
    job = relationship("Job", back_populates="audit_events")


class IdempotencyRecord(Base):
    """Idempotency record model."""

    __tablename__ = "idempotency_keys"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Business attributes
    idempotency_key = Column(String(255), nullable=False, unique=True, index=True)
    job_id = Column(String(36), ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False, index=True)
    request_fingerprint = Column(String(64), nullable=False, index=True)
    client_id = Column(String(128), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    job = relationship("Job", back_populates="idempotency_records")


class ArtifactRecord(Base):
    """Artifact record model."""

    __tablename__ = "artifacts"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign key
    job_id = Column(String(36), ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False, index=True)

    # Business attributes
    stage_name = Column(String(50), nullable=False)
    label = Column(String(100), nullable=False)
    artifact_ref = Column(JSON, nullable=False)
    kind = Column(String(20), nullable=False)
    content_type = Column(String(100), nullable=False)
    tags = Column(JSON, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    job = relationship("Job", back_populates="artifact_records")


class StageLock(Base):
    """Stage lock model for concurrency control."""

    __tablename__ = "stage_locks"

    # Primary key
    stage_name = Column(String(50), primary_key=True)

    # Lock attributes
    locked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    locked_by = Column(String(128), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
