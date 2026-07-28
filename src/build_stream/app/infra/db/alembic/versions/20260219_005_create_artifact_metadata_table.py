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

"""Create artifact_metadata table

Revision ID: 005
Revises: 004
Create Date: 2026-02-19 13:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create artifact_metadata table
    op.create_table(
        'artifact_metadata',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('stage_name', sa.String(length=50), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=False),
        sa.Column('artifact_ref', sa.JSON(), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.job_id'], ondelete='CASCADE'),
    )
    
    # Create indexes for performance
    op.create_index('idx_artifact_metadata_job_id', 'artifact_metadata', ['job_id'])
    op.create_index('idx_artifact_metadata_job_label', 'artifact_metadata', ['job_id', 'label'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_artifact_metadata_job_label', table_name='artifact_metadata')
    op.drop_index('idx_artifact_metadata_job_id', table_name='artifact_metadata')
    
    # Drop table
    op.drop_table('artifact_metadata')
