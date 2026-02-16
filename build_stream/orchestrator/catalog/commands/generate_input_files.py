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

"""GenerateInputFiles command DTO."""

from dataclasses import dataclass
from typing import ClassVar, Optional

from core.artifacts.value_objects import SafePath
from core.jobs.value_objects import CorrelationId, JobId


@dataclass(frozen=True)
class GenerateInputFilesCommand:
    """Command to execute the generate-input-files stage.

    Attributes:
        job_id: Job identifier (validated UUID).
        correlation_id: Request correlation identifier for tracing.
        adapter_policy_path: Optional custom adapter policy path.
                             If None, the default policy is used.
    """

    job_id: JobId
    correlation_id: CorrelationId
    adapter_policy_path: Optional[SafePath] = None
