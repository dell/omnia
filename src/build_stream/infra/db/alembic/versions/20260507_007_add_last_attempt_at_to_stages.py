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

# pylint: disable=C0103,E0401,E1102
# C0103: Module name and constant names follow Alembic migration naming conventions
# E0401: Import errors due to pylint running outside package context
# E1102: SQLAlchemy func.now() is callable at runtime

"""Add last_attempt_at column to job_stages table.

Revision ID: 007
Revises: 006
Create Date: 2026-05-07

Tracks the timestamp of the most recent retry/re-run attempt for each stage.
Used by the Resume & Retry feature (Component 4) to record when a stage
was last reset for retry.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'job_stages',
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('job_stages', 'last_attempt_at')
