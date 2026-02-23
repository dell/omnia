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

"""Create job_stages table

Revision ID: 002
Revises: 001
Create Date: 2026-02-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_stages",
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("stage_name", sa.String(50), nullable=False),
        sa.Column("stage_state", sa.String(20), nullable=False),
        sa.Column("attempt", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column("error_summary", sa.Text, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("job_id", "stage_name"),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.job_id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "stage_state IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'SKIPPED')",
            name="ck_stage_state",
        ),
    )

    op.create_index("ix_stages_job_id", "job_stages", ["job_id"])
    op.create_index("ix_stages_stage_state", "job_stages", ["stage_state"])
    op.create_index("ix_stages_job_stage", "job_stages", ["job_id", "stage_name"])


def downgrade() -> None:
    op.drop_index("ix_stages_job_stage", table_name="job_stages")
    op.drop_index("ix_stages_stage_state", table_name="job_stages")
    op.drop_index("ix_stages_job_id", table_name="job_stages")
    op.drop_table("job_stages")
