# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Create audit_events table

Revision ID: 004
Revises: 003
Create Date: 2026-02-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("correlation_id", sa.String(36), nullable=False),
        sa.Column("client_id", sa.String(128), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", JSONB, nullable=True),
        sa.CheckConstraint(
            "event_type IN ("
            "'JOB_CREATED', 'JOB_RETRIEVED', 'JOB_DELETED', "
            "'STAGE_STARTED', 'STAGE_INVOKED', 'STAGE_COMPLETED', 'STAGE_FAILED'"
            ")",
            name="ck_audit_event_type",
        ),
    )

    op.create_index("ix_audit_job_id", "audit_events", ["job_id"])
    op.create_index("ix_audit_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_correlation_id", "audit_events", ["correlation_id"])
    op.create_index("ix_audit_client_id", "audit_events", ["client_id"])
    op.create_index("ix_audit_timestamp", "audit_events", ["timestamp"])
    op.create_index("ix_audit_job_timestamp", "audit_events", ["job_id", "timestamp"])
    op.create_index(
        "ix_audit_client_timestamp",
        "audit_events",
        ["client_id", "timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_client_timestamp", table_name="audit_events")
    op.drop_index("ix_audit_job_timestamp", table_name="audit_events")
    op.drop_index("ix_audit_timestamp", table_name="audit_events")
    op.drop_index("ix_audit_client_id", table_name="audit_events")
    op.drop_index("ix_audit_correlation_id", table_name="audit_events")
    op.drop_index("ix_audit_event_type", table_name="audit_events")
    op.drop_index("ix_audit_job_id", table_name="audit_events")
    op.drop_table("audit_events")
