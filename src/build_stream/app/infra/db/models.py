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

# pylint: disable=line-too-long

# Third-party imports
from sqlalchemy import (
    Boolean,
    CheckConstraint,
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


class JobModel(Base):  # pylint: disable=too-few-public-methods
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

    # Catalog versioning (ER-BSM-002)
    composite_image_group_id = Column(String(256), nullable=True, index=True)
    catalog_identifier = Column(String(128), nullable=True)
    catalog_version = Column(String(20), nullable=True)
    catalog_schema_version = Column(Integer, nullable=True)

    # Pipeline phase (nullable — NULL for direct invocation)
    pipeline_phase = Column(String(10), nullable=True)

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

    # 1:1 relationship with ImageGroup (singular, not a list)
    image_group = relationship(
        "ImageGroupModel",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Composite indexes
    __table_args__ = (
        Index("ix_jobs_client_state", "client_id", "job_state"),
        Index("ix_jobs_created_tombstoned", "created_at", "tombstoned"),
    )


class StageModel(Base):  # pylint: disable=too-few-public-methods
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
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)

    # Error tracking
    error_code = Column(String(50), nullable=True)
    error_summary = Column(Text, nullable=True)

    # Log file path
    log_file_path = Column(String(512), nullable=True)

    # Result detail JSONB for validation results
    result_detail = Column(JSONB, nullable=True)

    # Optimistic locking
    version = Column(Integer, nullable=False, default=1)

    # Relationships
    job = relationship("JobModel", back_populates="stages")

    # Composite indexes
    __table_args__ = (
        Index("ix_stages_job_state", "job_id", "stage_state"),
    )


class IdempotencyKeyModel(Base):  # pylint: disable=too-few-public-methods
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


class AuditEventModel(Base):  # pylint: disable=too-few-public-methods
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
    job_id = Column(
        String(36),
        ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Business attributes
    stage_name = Column(String(50), nullable=False)
    label = Column(String(100), nullable=False)
    artifact_ref = Column(JSONB, nullable=False)
    kind = Column(String(20), nullable=False)
    content_type = Column(String(100), nullable=False)
    tags = Column(JSONB, nullable=True)

    # Timestamp
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),  # pylint: disable=not-callable
        nullable=False,
    )

    # Composite indexes
    __table_args__ = (
        Index("idx_artifact_metadata_job_id", "job_id"),
        Index("idx_artifact_metadata_job_label", "job_id", "label"),
    )


class ImageGroupModel(Base):  # pylint: disable=too-few-public-methods
    """ORM model for image_groups table.

    Tracks the lifecycle of built images independently of transient Job states.
    Enforces a 1:1 mapping between Job and ImageGroup via UNIQUE constraint on job_id.

    The primary key 'id' is the composite ImageGroupID: ``identifier-vVersion``
    (e.g. 'omnia-slurm-rhel-10-0-x86-64-aarch64-v1.0').
    """

    __tablename__ = "image_groups"

    # Primary key — composite ImageGroupID from catalog (NOT a UUID)
    id = Column(String(256), primary_key=True, nullable=False)

    # Foreign key to jobs table — UNIQUE enforces 1:1 mapping
    job_id = Column(
        String(36),
        ForeignKey("jobs.job_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Catalog versioning (ER-BSM-002)
    catalog_identifier = Column(String(128), nullable=True)
    catalog_version = Column(String(20), nullable=True)
    catalog_schema_version = Column(Integer, nullable=True)

    # Business attributes
    status = Column(String(20), nullable=False, default="BUILT", index=True)

    # Retention fields (ER-BSM-002 — used by Story 4)
    deploy_count = Column(Integer, nullable=False, default=0)
    is_protected = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),  # pylint: disable=not-callable
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),  # pylint: disable=not-callable
        nullable=False,
    )
    last_deployed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    job = relationship("JobModel", back_populates="image_group", uselist=False)
    images = relationship(
        "ImageModel",
        back_populates="image_group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("idx_image_groups_job_id", "job_id", unique=True),
        Index("idx_image_groups_status", "status"),
        Index("idx_image_groups_catalog_identifier", "catalog_identifier"),
        CheckConstraint(
            "status IN ('BUILT', 'DEPLOYING', 'DEPLOYED', 'RESTARTING', "
            "'RESTARTED', 'VALIDATING', 'PASSED', 'FAILED', 'CLEANING', "
            "'CLEANED', 'CLEANUP_FAILED')",
            name="ck_image_groups_status",
        ),
    )


class ImageModel(Base):  # pylint: disable=too-few-public-methods
    """ORM model for images table.

    Stores constituent images within an Image Group, identified by
    functional role (e.g., slurm_node, kube_control_plane).

    Each Image Group contains one image per role, enforced by the
    UNIQUE constraint on (image_group_id, role).
    """

    __tablename__ = "images"

    # Primary key — UUID
    id = Column(String(36), primary_key=True, nullable=False)

    # Foreign key to image_groups table
    image_group_id = Column(
        String(128),
        ForeignKey("image_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Business attributes
    role = Column(String(128), nullable=False)
    image_name = Column(String(512), nullable=False)
    manifest_path = Column(String(512), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),  # pylint: disable=not-callable
        nullable=False,
    )

    # Relationships
    image_group = relationship("ImageGroupModel", back_populates="images")

    # Constraints
    __table_args__ = (
        Index("idx_images_image_group_id", "image_group_id"),
        Index(
            "idx_images_image_group_id_role",
            "image_group_id",
            "role",
        ),
    )
