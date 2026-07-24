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

"""Upload files command."""

from dataclasses import dataclass
from typing import List, Tuple

from core.jobs.value_objects import JobId, ClientId, CorrelationId


@dataclass(frozen=True)
class UploadFilesCommand:
    """Command to upload configuration files to a job.
    
    Attributes:
        job_id: Target job identifier.
        files: List of (filename, content) tuples to upload.
        client_id: Client who owns this job (from auth).
        correlation_id: Request correlation identifier for tracing.
    """
    job_id: JobId
    files: List[Tuple[str, bytes]]
    client_id: ClientId
    correlation_id: CorrelationId
