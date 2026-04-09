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

"""Restart response DTO."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RestartResponse:
    """Response DTO for restart stage acceptance.

    Attributes:
        job_id: Job identifier.
        stage_name: Stage identifier.
        status: Acceptance status.
        submitted_at: Submission timestamp (ISO 8601).
        image_group_id: Image group identifier from job metadata.
        correlation_id: Correlation identifier.
    """

    job_id: str
    stage_name: str
    status: str
    submitted_at: str
    image_group_id: str
    correlation_id: str
