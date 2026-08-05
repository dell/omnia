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

INPUT_VALIDATOR_LOG_PATH = "/var/log/omnia/telemetry"

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


def get_vault_password(file_name):
    """Returns the vault password filename for a given input file (unused in telemetry)."""
    return ""
