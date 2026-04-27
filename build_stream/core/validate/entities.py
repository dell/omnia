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

"""Domain entities for Validate module."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass(frozen=True)
class ValidateRequest:
    """Immutable entity representing a validate stage request.

    Written to the NFS queue for the Playbook Watcher to consume.
    Uses command_type 'test_automation' to distinguish from ansible-playbook requests.

    Attributes:
        request_id: Unique request identifier (validate_{job_id}_{timestamp}).
        job_id: Parent job identifier (UUID).
        stage_type: Stage identifier ('validate').
        command_type: Command type ('test_automation') — distinguishes from 'ansible-playbook'.
        scenario_names: Test scenarios to run (e.g. ['discovery'], ['all']).
        test_suite: Optional suite filter (e.g. 'smoke', 'sanity', 'regression').
        timeout_minutes: Max execution time in minutes.
        artifact_dir: Path for test artifacts output.
        config_path: Path to omnia_test_config.yml.
        correlation_id: Request tracing identifier.
        submitted_at: Request submission timestamp (ISO 8601).
        attempt: Attempt number for this validate stage.
    """

    request_id: str
    job_id: str
    stage_type: str = "validate"
    command_type: str = "test_automation"
    scenario_names: List[str] = field(default_factory=lambda: ["all"])
    test_suite: str = ""
    timeout_minutes: int = 120
    artifact_dir: str = ""
    config_path: str = "/opt/omnia/automation/omnia_test_config.yml"
    correlation_id: str = ""
    submitted_at: str = ""
    attempt: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize request to dictionary for JSON file writing."""
        return {
            "request_id": self.request_id,
            "job_id": self.job_id,
            "stage_type": self.stage_type,
            "command_type": self.command_type,
            "scenario_names": self.scenario_names,
            "test_suite": self.test_suite,
            "timeout_minutes": self.timeout_minutes,
            "artifact_dir": self.artifact_dir,
            "config_path": self.config_path,
            "correlation_id": self.correlation_id,
            "submitted_at": self.submitted_at,
            "attempt": self.attempt,
        }

    def generate_filename(self) -> str:
        """Generate request file name following naming convention.

        Returns:
            Filename: {job_id}_{stage_type}_{timestamp}.json
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"{self.job_id}_{self.stage_type}_{timestamp}.json"
