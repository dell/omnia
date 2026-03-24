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

"""CreateJob command DTO."""

from dataclasses import dataclass

from core.jobs.value_objects import (
    ClientId,
    CorrelationId,
    IdempotencyKey,
)


@dataclass(frozen=True)
class CreateJobCommand:
    """Command to create a new job.

    Immutable command object representing the intent to create a job.
    All validation is performed in the use case layer.

    Attributes:
        client_id: Client who owns this job (from auth).
        request_client_id: Client ID from request payload.
        client_name: Optional client name.
        correlation_id: Request correlation identifier for tracing.
        idempotency_key: Client-supplied key for retry deduplication.
    """

    client_id: ClientId
    request_client_id: str
    correlation_id: CorrelationId
    idempotency_key: IdempotencyKey
    client_name: str | None = None
