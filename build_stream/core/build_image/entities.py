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

"""Domain entities for Build Image module."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.localrepo.value_objects import ExecutionTimeout, ExtraVars, PlaybookPath


@dataclass(frozen=True)
# pylint: disable=too-many-instance-attributes
class BuildImageRequest:
    """Immutable entity representing a build image request.

    Written to the NFS queue for OIM Core consumption.
    Compatible with PlaybookRequest interface for reuse of existing repository.

    Attributes:
        job_id: Parent job identifier.
        stage_name: Stage identifier (build-image).
        playbook_path: Validated path to the playbook.
        extra_vars: Ansible extra variables (includes architecture, image_key, functional_groups).
        inventory_file_path: Optional path to inventory file for aarch64 builds.
        correlation_id: Request tracing identifier.
        timeout: Execution timeout configuration.
        submitted_at: Request submission timestamp.
        request_id: Unique request identifier.
    """

    job_id: str
    stage_name: str
    playbook_path: PlaybookPath
    extra_vars: ExtraVars
    correlation_id: str
    timeout: ExecutionTimeout
    submitted_at: str
    request_id: str
    inventory_file_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize request to dictionary for JSON file writing."""
        request_dict = {
            "job_id": self.job_id,
            "stage_name": self.stage_name,
            "playbook_path": str(self.playbook_path),
            "extra_vars": self.extra_vars.to_dict(),
            "correlation_id": self.correlation_id,
            "timeout_minutes": self.timeout.minutes,
            "submitted_at": self.submitted_at,
            "request_id": self.request_id,
        }
        
        # Add inventory file path if present
        if self.inventory_file_path:
            request_dict["inventory_file_path"] = self.inventory_file_path
            
        return request_dict

    def generate_filename(self) -> str:
        """Generate request file name following naming convention.

        Returns:
            Filename: {job_id}_{stage_name}_{timestamp}.json
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"{self.job_id}_{self.stage_name}_{timestamp}.json"

    def get_playbook_command(self) -> str:
        """Generate the ansible-playbook command based on request parameters.

        Returns:
            Complete ansible-playbook command string.
        """
        # Base command
        cmd = f'ansible-playbook {self.playbook_path}'
        
        # Add inventory file for aarch64
        if self.inventory_file_path:
            cmd += f' -i {self.inventory_file_path}'
        
        # Add extra vars
        extra_vars = self.extra_vars.to_dict()
        cmd += f' -e job_id="{extra_vars["job_id"]}"'
        cmd += f' -e image_key="{extra_vars["image_key"]}"'
        cmd += f' -e functional_groups=\'{extra_vars["functional_groups"]}\''
        
        return cmd
