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

"""CreateBuildImage command DTO."""

from dataclasses import dataclass
from typing import List, Optional

from core.jobs.value_objects import ClientId, CorrelationId, JobId


@dataclass(frozen=True)
class CreateBuildImageCommand:
    """Command to trigger build image stage.

    Immutable command object representing the intent to execute
    the build-image stage for a given job.

    Domain-segregated (Omnia 2.3+): architecture, image_key, and functional_groups
    are optional. When omitted, the image_build_manager.yml playbook reads the
    catalog directly and builds all images for all architectures.

    Attributes:
        job_id: Job identifier from URL path.
        client_id: Client who owns this job (from auth).
        correlation_id: Request correlation identifier for tracing.
        architecture: Optional target architecture (legacy, read from catalog if omitted).
        image_key: Optional image identifier key (legacy, read from catalog if omitted).
        functional_groups: Optional list of functional groups (legacy, read from catalog if omitted).
    """

    job_id: JobId
    client_id: ClientId
    correlation_id: CorrelationId
    architecture: Optional[str] = None
    image_key: Optional[str] = None
    functional_groups: Optional[List[str]] = None
