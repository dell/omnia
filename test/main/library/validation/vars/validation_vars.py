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
Validation Variables

All constants, patterns, and allowed values for config validation.
"""

import re

# =============================================================================
# REGEX PATTERNS
# =============================================================================

# IPv4: 0-255.0-255.0-255.0-255
IPV4_PATTERN = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)

# Unix absolute path: starts with /, no spaces, no trailing whitespace
UNIX_PATH_PATTERN = re.compile(r"^/[^\s]+$")

# Report ID: alphanumeric, underscores, hyphens — no spaces, no special chars
REPORT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

# Username: alphanumeric, underscores, hyphens, dots — standard Linux usernames
USERNAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.-]*$")

# =============================================================================
# ALLOWED VALUES
# =============================================================================

# share_option in test_config.yml
VALID_SHARE_OPTIONS = {"NFS", "Local"}

# nfs_type in test_config.yml
VALID_NFS_TYPES = {"external", "internal"}

# dataset folder names under datasets/
VALID_DATASETS = {"nfs_external", "nfs_internal", "local_storage"}

# Commands for run_validation / test_run_config.yml
VALID_COMMANDS = {"deploy", "verify", "test"}

# =============================================================================
# REQUIRED CONFIG KEYS
# =============================================================================

# Keys that must always be present in test_config.yml (can be empty for local)
REQUIRED_CONFIG_KEYS = [
    "admin_nic_ip",
    "share_option",
]

# Keys required for NFS external
NFS_EXTERNAL_REQUIRED = [
    "nfs_server_ip",
    "nfs_server_share_path",
    "omnia_shared_path",
]

# Keys required for NFS internal
NFS_INTERNAL_REQUIRED = [
    "nfs_server_share_path",
    "omnia_shared_path",
]

# Keys required for Local storage
LOCAL_REQUIRED = [
    "omnia_shared_path",
]

# =============================================================================
# FIELD VALIDATION RULES
# =============================================================================
# Maps field name to (validator_type, allow_empty, description)
# validator_type: "ipv4", "ipv4_or_localhost", "unix_path", "username",
#                 "enum", "bool", "int", "report_path", "report_id"

FIELD_RULES = {
    # Target OIM Server
    "oim_server_ip": ("ipv4_or_localhost", True, "OIM server IP (blank for local mode)"),
    "oim_ssh_user": ("username", False, "SSH username for remote OIM"),
    "oim_ssh_port": ("port", False, "SSH port (1-65535)"),

    # Admin NIC
    "admin_nic_ip": ("ipv4", False, "Admin NIC IP of the OIM host"),

    # Storage
    "share_option": ("enum", False, "Storage option"),
    "nfs_type": ("enum", False, "NFS type (external/internal)"),
    "nfs_server_ip": ("ipv4", False, "NFS server IP address"),
    "nfs_server_share_path": ("unix_path", False, "NFS share path on server"),
    "omnia_shared_path": ("unix_path", False, "Local mount point for shared data"),

    # Dataset
    "dataset": ("enum", False, "Dataset folder name"),
    "use_dataset": ("bool", True, "Whether to use dataset override"),

    # Report
    "report_path": ("report_path", True, "Report output directory"),
    "report_name": ("report_id", False, "Report file base name"),
    "report_id": ("report_id", True, "Custom report ID (blank = timestamp)"),

    # Build
    "force_rebuild": ("bool", True, "Force container image rebuild"),
}

# Enum allowed values per field
ENUM_VALUES = {
    "share_option": VALID_SHARE_OPTIONS,
    "nfs_type": VALID_NFS_TYPES,
    "dataset": VALID_DATASETS,
}

# =============================================================================
# SSH PORT RANGE
# =============================================================================

MIN_PORT = 1
MAX_PORT = 65535
