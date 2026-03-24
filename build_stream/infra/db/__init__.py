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

"""Database infrastructure package.

Provides ORM models, mappers, SQL repository implementations,
and session management for PostgreSQL persistence.
"""

from .models import Base, JobModel, StageModel, IdempotencyKeyModel, AuditEventModel, ArtifactMetadata
from .mappers import JobMapper, StageMapper, IdempotencyRecordMapper, AuditEventMapper
from .repositories import (
    SqlJobRepository,
    SqlStageRepository,
    SqlIdempotencyRepository,
    SqlAuditEventRepository,
    SqlArtifactMetadataRepository,
)
from .session import get_db_session, get_db, SessionLocal

__all__ = [
    "Base",
    "JobModel",
    "StageModel",
    "IdempotencyKeyModel",
    "AuditEventModel",
    "ArtifactMetadata",
    "JobMapper",
    "StageMapper",
    "IdempotencyRecordMapper",
    "AuditEventMapper",
    "SqlJobRepository",
    "SqlStageRepository",
    "SqlIdempotencyRepository",
    "SqlAuditEventRepository",
    "SqlArtifactMetadataRepository",
    "get_db_session",
    "get_db",
    "SessionLocal",
]
