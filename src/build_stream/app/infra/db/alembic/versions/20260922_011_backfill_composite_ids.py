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

"""Backfill composite ImageGroupID for existing rows.

ER-BSM-002 Phase 1 (cont.): Data migration.
  - Populate composite_image_group_id from existing image_groups.id + default
    version "1.0"
  - Populate catalog_schema_version with default value 2 (Omnia 2.3)
  - Populate catalog_identifier from existing image_groups.id
  - Populate catalog_version with "1.0"

Revision ID: 011
Revises: 010
Create Date: 2026-09-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply data migration: Backfill composite IDs from existing data."""
    conn = op.get_bind()

    # Backfill image_groups: derive catalog_identifier from existing id,
    # set default version "1.0", schema_version 2, and build composite id.
    conn.execute(
        sa.text(
            """
            UPDATE image_groups
            SET catalog_identifier = id,
                catalog_version = '1.0',
                catalog_schema_version = 2
            WHERE catalog_identifier IS NULL
            """
        )
    )

    # Convert image_groups.id to composite form (identifier-vVersion).
    # Must also update images.image_group_id FK to keep referential
    # integrity. Drop and re-add the FK to allow the PK update.
    conn.execute(
        sa.text(
            """
            ALTER TABLE images
                DROP CONSTRAINT IF EXISTS images_image_group_id_fkey
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE images
            SET image_group_id = image_group_id || '-v1.0'
            WHERE image_group_id NOT LIKE '%-v%'
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE image_groups
            SET id = id || '-v1.0'
            WHERE id NOT LIKE '%-v%'
            """
        )
    )

    conn.execute(
        sa.text(
            """
            ALTER TABLE images
                ADD CONSTRAINT images_image_group_id_fkey
                FOREIGN KEY (image_group_id)
                REFERENCES image_groups(id) ON DELETE CASCADE
            """
        )
    )

    # Backfill jobs from their linked image_group (now composite).
    conn.execute(
        sa.text(
            """
            UPDATE jobs
            SET composite_image_group_id = ig.id,
                catalog_identifier = ig.catalog_identifier,
                catalog_version = '1.0',
                catalog_schema_version = 2
            FROM image_groups ig
            WHERE ig.job_id = jobs.job_id
              AND jobs.composite_image_group_id IS NULL
            """
        )
    )


def downgrade() -> None:
    """Revert data migration: Clear backfilled composite ID fields."""
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            UPDATE jobs
            SET composite_image_group_id = NULL,
                catalog_identifier = NULL,
                catalog_version = NULL,
                catalog_schema_version = NULL
            """
        )
    )

    # Revert image_groups.id from composite form back to raw identifier.
    conn.execute(
        sa.text(
            """
            ALTER TABLE images
                DROP CONSTRAINT IF EXISTS images_image_group_id_fkey
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE images
            SET image_group_id = regexp_replace(image_group_id, '-v[^-]+$', '')
            WHERE image_group_id LIKE '%-v%'
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE image_groups
            SET id = catalog_identifier
            WHERE catalog_identifier IS NOT NULL
            """
        )
    )

    conn.execute(
        sa.text(
            """
            ALTER TABLE images
                ADD CONSTRAINT images_image_group_id_fkey
                FOREIGN KEY (image_group_id)
                REFERENCES image_groups(id) ON DELETE CASCADE
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE image_groups
            SET catalog_identifier = NULL,
                catalog_version = NULL,
                catalog_schema_version = NULL
            """
        )
    )
