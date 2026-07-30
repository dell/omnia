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
Validation Messages

All error messages, success messages, and fix instructions for
configuration validation. No inline messages elsewhere.
"""

from typing import Dict

VALIDATION_MSGS: Dict[str, str] = {

    # =========================================================================
    # GENERAL
    # =========================================================================
    "config_file_missing": (
        "Configuration file not found: {path}\n"
        "HOW TO FIX: Create {filename} in the main/ module directory."
    ),
    "config_file_empty": (
        "Configuration file is empty: {path}\n"
        "HOW TO FIX: Add required fields to {filename}."
    ),
    "config_valid": "Configuration validation passed: {source}",
    "config_invalid": "Configuration validation failed with {count} error(s)",

    # =========================================================================
    # IP ADDRESS
    # =========================================================================
    "invalid_ipv4": (
        "Invalid IPv4 address for '{field}': '{value}'\n"
        "Expected format: x.x.x.x (e.g., 192.168.1.100)\n"
        "Each octet must be 0-255."
    ),
    "invalid_ipv4_or_localhost": (
        "Invalid value for '{field}': '{value}'\n"
        "Expected: valid IPv4 address, 'localhost', or empty (for local mode)."
    ),

    # =========================================================================
    # UNIX PATH
    # =========================================================================
    "invalid_unix_path": (
        "Invalid path for '{field}': '{value}'\n"
        "Path must start with '/' and contain no spaces.\n"
        "Example: /opt/omnia/shared"
    ),

    # =========================================================================
    # REPORT
    # =========================================================================
    "invalid_report_path": (
        "Invalid report path: '{value}'\n"
        "Report path must be either:\n"
        "  - An absolute path (starts with '/'), e.g., /var/reports\n"
        "  - A folder name (no spaces), e.g., reports\n"
        "Spaces are NOT allowed in the report path."
    ),
    "invalid_report_id": (
        "Invalid report ID: '{value}'\n"
        "Report ID must contain only letters, numbers, underscores, and hyphens.\n"
        "No spaces allowed. Example: my_run_01, sprint-42"
    ),

    # =========================================================================
    # USERNAME
    # =========================================================================
    "invalid_username": (
        "Invalid username for '{field}': '{value}'\n"
        "Username must start with a letter or underscore, followed by\n"
        "letters, digits, underscores, hyphens, or dots.\n"
        "Example: root, admin_user, test.user"
    ),

    # =========================================================================
    # PORT
    # =========================================================================
    "invalid_port": (
        "Invalid port for '{field}': '{value}'\n"
        "Port must be an integer between 1 and 65535."
    ),

    # =========================================================================
    # ENUM
    # =========================================================================
    "invalid_enum": (
        "Invalid value for '{field}': '{value}'\n"
        "Allowed values: {allowed}"
    ),

    # =========================================================================
    # BOOLEAN
    # =========================================================================
    "invalid_bool": (
        "Invalid value for '{field}': '{value}'\n"
        "Expected: true or false."
    ),

    # =========================================================================
    # REQUIRED FIELDS
    # =========================================================================
    "missing_required": (
        "Missing required parameter '{field}' in {source}\n"
        "This field is required for {context}."
    ),

    # =========================================================================
    # STORAGE-SPECIFIC
    # =========================================================================
    "nfs_external_missing": (
        "Missing required NFS external parameter '{field}' in {source}\n"
        "Required for NFS external: nfs_server_ip, nfs_server_share_path, omnia_shared_path"
    ),
    "nfs_internal_missing": (
        "Missing required NFS internal parameter '{field}' in {source}\n"
        "Required for NFS internal: nfs_server_share_path, omnia_shared_path"
    ),
    "local_missing": (
        "Missing required Local storage parameter '{field}' in {source}\n"
        "Required for Local storage: omnia_shared_path"
    ),

    # =========================================================================
    # DATASET
    # =========================================================================
    "dataset_not_found": (
        "Dataset directory not found: {path}\n"
        "Available datasets: {available}\n"
        "HOW TO FIX: Set 'dataset' to one of the available options in test_config.yml."
    ),
    "dataset_config_missing": (
        "Dataset config file not found: {path}\n"
        "Each dataset must contain an install_config.yml file."
    ),
    "dataset_field_invalid": (
        "Invalid value in dataset '{dataset}' for '{field}': '{value}'\n"
        "{detail}"
    ),
}
