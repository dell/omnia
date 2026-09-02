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

"""ParseCatalog command DTO."""

from dataclasses import dataclass

from core.jobs.value_objects import ClientId, CorrelationId, JobId


@dataclass(frozen=True)
class ParseCatalogCommand:
    """Command to trigger the parse-catalog stage.

    Immutable command object representing the intent to execute the
    parse-catalog stage for a given job. The catalog itself is not carried
    in the command -- it reads the ``catalog_rhel.json`` already uploaded
    for this job via ``PUT /api/v1/jobs/{job_id}/upload`` (the "upload"
    stage), consistent with the rest of the Omnia 2.3+ domain-segregated
    flow where the catalog is uploaded once and consumed directly.

    Attributes:
        job_id: Job identifier from URL path.
        client_id: Client who owns this job (from auth).
        correlation_id: Request correlation identifier for tracing.
    """

    job_id: JobId
    client_id: ClientId
    correlation_id: CorrelationId
