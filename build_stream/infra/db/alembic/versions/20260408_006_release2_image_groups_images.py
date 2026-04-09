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

"""Release 2: Create image_groups and images tables, modify jobs and job_stages.

Revision ID: 006
Revises: 005
Create Date: 2026-04-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── 1. Modify jobs table — add pipeline_phase ───
    op.add_column(
        "jobs",
        sa.Column("pipeline_phase", sa.String(10), nullable=True),
    )

    # ─── 2. Modify job_stages table — add result_detail JSONB ───
    op.add_column(
        "job_stages",
        sa.Column("result_detail", JSONB, nullable=True),
    )

    # ─── 3. Create image_groups table ───
    op.create_table(
        "image_groups",
        sa.Column("id", sa.String(128), primary_key=True, nullable=False),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="BUILT"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('BUILT', 'DEPLOYING', 'DEPLOYED', 'RESTARTING', "
            "'RESTARTED', 'VALIDATING', 'PASSED', 'FAILED', 'CLEANED')",
            name="ck_image_groups_status",
        ),
    )
    op.create_index(
        "idx_image_groups_job_id", "image_groups", ["job_id"], unique=True
    )
    op.create_index("idx_image_groups_status", "image_groups", ["status"])

    # ─── 4. Create images table ───
    op.create_table(
        "images",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "image_group_id",
            sa.String(128),
            sa.ForeignKey("image_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(128), nullable=False),
        sa.Column("image_name", sa.String(256), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_images_image_group_id", "images", ["image_group_id"])
    op.create_index(
        "uq_images_image_group_id_role",
        "images",
        ["image_group_id", "role"],
        unique=True,
    )


def downgrade() -> None:
    # Drop images table
    op.drop_index("uq_images_image_group_id_role", table_name="images")
    op.drop_index("idx_images_image_group_id", table_name="images")
    op.drop_table("images")

    # Drop image_groups table
    op.drop_index("idx_image_groups_status", table_name="image_groups")
    op.drop_index("idx_image_groups_job_id", table_name="image_groups")
    op.drop_table("image_groups")

    # Remove result_detail from job_stages
    op.drop_column("job_stages", "result_detail")

    # Remove pipeline_phase from jobs
    op.drop_column("jobs", "pipeline_phase")
