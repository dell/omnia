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

"""Audit event entity."""

from dataclasses import dataclass, field
from datetime import datetime

from ..value_objects import ClientId, CorrelationId, JobId


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit event record.

    Captures significant domain events for audit trail and compliance.

    Attributes:
        event_id: Unique event identifier.
        job_id: Associated job identifier.
        event_type: Type of event (e.g., JOB_CREATED, STAGE_COMPLETED).
        correlation_id: Request correlation identifier.
        client_id: Client who triggered the event.
        timestamp: Event occurrence timestamp.
        details: Additional event-specific details.
    """

    event_id: str
    job_id: JobId
    event_type: str
    correlation_id: CorrelationId
    client_id: ClientId
    timestamp: datetime
    details: dict = field(default_factory=dict)
