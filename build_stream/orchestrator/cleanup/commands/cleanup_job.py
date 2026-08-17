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

"""Command DTO for the CleanUp Job use case."""

from dataclasses import dataclass

from core.jobs.value_objects import ClientId, CorrelationId, JobId


@dataclass(frozen=True)
class CleanupJobCommand:
    """Command for triggering hard delete (cleanup) of a Job.

    Attributes:
        job_id: Job identifier from URL path.
        client_id: Authenticated client (from JWT token).
        correlation_id: Request tracing identifier.
    """

    job_id: JobId
    client_id: ClientId
    correlation_id: CorrelationId
