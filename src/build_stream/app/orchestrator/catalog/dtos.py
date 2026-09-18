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

"""Response DTOs for catalog orchestrator use cases."""

from dataclasses import dataclass, field
from typing import List, Tuple

from core.artifacts.value_objects import ArtifactRef


@dataclass
class ParseCatalogResult:
    """Result DTO for ParseCatalogUseCase.

    Kept intentionally minimal (Omnia 2.3+ reintroduction): the stage's
    only job today is the image_group_id uniqueness check, so the result
    only carries what callers need to confirm that outcome. Root JSON
    generation and catalog-metadata artifact storage are handled elsewhere
    (create-local-repository / build-image) and are not duplicated here.
    """

    job_id: str
    stage_state: str
    message: str
    image_group_id: str
    completed_at: str  # ISO 8601


@dataclass
class GenerateInputFilesResult:
    """Result DTO for GenerateInputFilesUseCase."""

    job_id: str
    stage_state: str
    message: str
    configs_ref: ArtifactRef = field(metadata={"exclude": True})  # Exclude from JSON response
    config_file_count: int = field(metadata={"exclude": True})  # Exclude from JSON response
    config_files: List[str] = field(metadata={"exclude": True})  # Exclude from JSON response
    arch_os_combinations: List[Tuple[str, str, str]] = field(metadata={"exclude": True})  # Exclude from JSON response
    completed_at: str = field(metadata={"exclude": True})  # Exclude from JSON response
