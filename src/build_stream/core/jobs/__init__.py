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

"""Job domain module for Build Stream."""

from .entities import Job, Stage, IdempotencyRecord, AuditEvent
from .exceptions import (
    JobDomainError,
    JobNotFoundError,
    JobAlreadyExistsError,
    InvalidStateTransitionError,
    TerminalStateViolationError,
    IdempotencyConflictError,
)
from .repositories import (
    JobRepository,
    StageRepository,
    IdempotencyRepository,
    AuditEventRepository,
    JobIdGenerator,
    UUIDGenerator,
)
from .services import FingerprintService
from .value_objects import (
    JobId,
    CorrelationId,
    IdempotencyKey,
    StageName,
    StageType,
    RequestFingerprint,
    ClientId,
    JobState,
)

__all__ = [
    "Job",
    "Stage",
    "IdempotencyRecord",
    "AuditEvent",
    "JobDomainError",
    "JobNotFoundError",
    "JobAlreadyExistsError",
    "InvalidStateTransitionError",
    "TerminalStateViolationError",
    "IdempotencyConflictError",
    "JobRepository",
    "StageRepository",
    "IdempotencyRepository",
    "AuditEventRepository",
    "JobIdGenerator",
    "UUIDGenerator",
    "FingerprintService",
    "JobId",
    "CorrelationId",
    "IdempotencyKey",
    "StageName",
    "StageType",
    "RequestFingerprint",
    "ClientId",
    "JobState",
]
