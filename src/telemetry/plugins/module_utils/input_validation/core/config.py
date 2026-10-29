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

"""
Telemetry-specific validation configuration.
Standalone config.py scoped to the three telemetry input files only.
"""

import os
import re

INPUT_VALIDATOR_LOG_PATH = os.path.join(
    os.environ.get("OMNIA_DATA_PATH") or "/opt/omnia",
    "telemetry", "log"
)

files = {
    "telemetry_config": "telemetry_config.yml",
    "telemetry_storage_config": "telemetry_storage_config.yml",
    "telemetry_packages": "telemetry_packages.yml",
}

input_file_inventory = {
    "telemetry": [
        files["telemetry_config"],
        files["telemetry_storage_config"],
        files["telemetry_packages"],
    ],
}

passwords_set = {
    "password",
    "passwd",
    "secret",
    "telemetry_registry_password",
}

extensions = {
    "json": ".json",
    "yml": ".yml",
}


_PROJECT_NAME_PATTERN = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,254}')


def validate_project_name(project_name):
    """Validate project_name is a single safe path segment.

    Accepts only names matching ``^[A-Za-z0-9][A-Za-z0-9._-]*$``, rejects
    ``.`` and ``..``, and requires ``basename(x) == x``.  Modelled after
    Repo Manager's ``get_project_name`` validation.

    Args:
        project_name (str): The project name to validate.

    Returns:
        str: The validated project name (unchanged).

    Raises:
        ValueError: If *project_name* is empty, contains path separators,
            matches ``.`` / ``..``, or does not match the allowed pattern.
    """
    if not project_name:
        raise ValueError("project_name cannot be empty")
    if project_name in ('.', '..'):
        raise ValueError(
            "project_name is not a valid single-segment name"
        )
    if os.path.basename(project_name) != project_name:
        raise ValueError(
            "project_name is not a valid single-segment name"
        )
    if not _PROJECT_NAME_PATTERN.fullmatch(project_name):
        raise ValueError(
            "project_name is not a valid single-segment name"
        )
    return project_name


def get_vault_password(file_name) -> str:
    """Returns the vault password filename for a given input file (unused in telemetry)."""
    return ""
