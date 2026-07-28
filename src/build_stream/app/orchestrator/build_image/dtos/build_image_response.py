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

"""Build Image response DTO."""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class BuildImageResponse:
    """Response DTO for build image stage acceptance.

    Attributes:
        job_id: Job identifier.
        stage_name: Stage identifier.
        status: Acceptance status.
        submitted_at: Submission timestamp (ISO 8601).
        correlation_id: Correlation identifier.
        architecture: Target architecture.
        image_key: Image identifier key.
        functional_groups: List of functional groups to build.
    """

    job_id: str
    stage_name: str
    status: str
    submitted_at: str
    correlation_id: str
    architecture: str
    image_key: str
    functional_groups: List[str]
