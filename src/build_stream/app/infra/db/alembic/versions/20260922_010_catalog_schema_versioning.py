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

# pylint: disable=C0103,E0401,E1102,E1101
# C0103: Module name and constant names follow Alembic migration naming conventions
# E0401: Import errors due to pylint running outside package context
# E1102: SQLAlchemy func.now() is callable at runtime
# E1101: Alembic op functions are dynamically added

"""Add catalog schema versioning and composite ImageGroupID columns.

ER-BSM-002 Phase 1: Schema migration.
  - jobs: composite_image_group_id, catalog_identifier, catalog_version,
          catalog_schema_version
  - image_groups: catalog_identifier, catalog_version, catalog_schema_version,
                  deploy_count, is_protected, last_deployed_at; widen id to 256
  - images: manifest_path

Revision ID: 010
Revises: 009
Create Date: 2026-09-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration: Add catalog versioning columns."""
    # --- jobs table ---
    op.add_column(
        "jobs",
        sa.Column("composite_image_group_id", sa.String(256), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("catalog_identifier", sa.String(128), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("catalog_version", sa.String(20), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("catalog_schema_version", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_jobs_composite_image_group_id",
        "jobs",
        ["composite_image_group_id"],
    )

    # --- image_groups table ---
    op.add_column(
        "image_groups",
        sa.Column("catalog_identifier", sa.String(128), nullable=True),
    )
    op.add_column(
        "image_groups",
        sa.Column("catalog_version", sa.String(20), nullable=True),
    )
    op.add_column(
        "image_groups",
        sa.Column("catalog_schema_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "image_groups",
        sa.Column("deploy_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "image_groups",
        sa.Column("is_protected", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "image_groups",
        sa.Column(
            "last_deployed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_image_groups_catalog_identifier",
        "image_groups",
        ["catalog_identifier"],
    )

    # --- images table ---
    op.add_column(
        "images",
        sa.Column("manifest_path", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    """Revert migration: Remove catalog versioning columns."""
    # --- images table ---
    op.drop_column("images", "manifest_path")

    # --- image_groups table ---
    op.drop_index("idx_image_groups_catalog_identifier", table_name="image_groups")
    op.drop_column("image_groups", "last_deployed_at")
    op.drop_column("image_groups", "is_protected")
    op.drop_column("image_groups", "deploy_count")
    op.drop_column("image_groups", "catalog_schema_version")
    op.drop_column("image_groups", "catalog_version")
    op.drop_column("image_groups", "catalog_identifier")

    # --- jobs table ---
    op.drop_index("ix_jobs_composite_image_group_id", table_name="jobs")
    op.drop_column("jobs", "catalog_schema_version")
    op.drop_column("jobs", "catalog_version")
    op.drop_column("jobs", "catalog_identifier")
    op.drop_column("jobs", "composite_image_group_id")
