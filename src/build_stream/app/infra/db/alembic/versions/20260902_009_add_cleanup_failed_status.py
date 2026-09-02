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

"""Add CLEANUP_FAILED status to image_groups check constraint.

The cleanup workflow needs a terminal state for when the cleanup playbook fails.
This prevents indefinite polling and allows the user to see the failure clearly.

Revision ID: 009
Revises: 008
Create Date: 2026-09-02
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration: Add CLEANUP_FAILED to image_groups status check constraint."""
    # Drop the old constraint
    op.drop_constraint("ck_image_groups_status", "image_groups", type_="check")

    # Create the new constraint with CLEANUP_FAILED added
    op.create_check_constraint(
        "ck_image_groups_status",
        "image_groups",
        "status IN ('BUILT', 'DEPLOYING', 'DEPLOYED', 'RESTARTING', "
        "'RESTARTED', 'VALIDATING', 'PASSED', 'FAILED', 'CLEANING', 'CLEANED', 'CLEANUP_FAILED')",
    )


def downgrade() -> None:
    """Revert migration: Remove CLEANUP_FAILED from image_groups status check constraint."""
    # Drop the new constraint
    op.drop_constraint("ck_image_groups_status", "image_groups", type_="check")

    # Recreate the old constraint without CLEANUP_FAILED
    op.create_check_constraint(
        "ck_image_groups_status",
        "image_groups",
        "status IN ('BUILT', 'DEPLOYING', 'DEPLOYED', 'RESTARTING', "
        "'RESTARTED', 'VALIDATING', 'PASSED', 'FAILED', 'CLEANING', 'CLEANED')",
    )
