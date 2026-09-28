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
Utils domain validation messages.

This module contains all user-facing validation messages for the
utils domain. Messages are grouped by config file and validation concern.
"""

# =============================================================================
# INSTALL_OS CONFIGURATION MESSAGES
# =============================================================================

SOURCE_ISO_REQUIRED_MSG = (
    "install_os_config: source_iso_path is required for build_iso, generate_ks, "
    "and end-to-end modes."
)

SOURCE_ISO_NOT_FOUND_MSG = (
    "install_os_config: source_iso_path file not found or not accessible."
)

CUSTOM_ISO_REQUIRED_MSG = (
    "install_os_config: custom_iso_path is required for build_iso, deploy, "
    "and end-to-end modes."
)

TARGET_BMC_IP_REQUIRED_MSG = (
    "install_os_config: target_bmc_ip is required for deploy and end-to-end modes."
)

TARGET_BMC_IP_INVALID_MSG = (
    "install_os_config: target_bmc_ip must be a valid IPv4 address."
)

TARGET_HOSTNAME_REQUIRED_MSG = (
    "install_os_config: target_hostname is required for build and end-to-end modes."
)

TARGET_ADMIN_IP_INVALID_MSG = (
    "install_os_config: target_admin_ip must be a valid IPv4 address."
)

KICKSTART_DELIVERY_INVALID_MSG = (
    "install_os_config: kickstart_delivery_method must be 'embedded' or 'nfs'."
)

SSH_KEY_NOT_FOUND_MSG = (
    "install_os_config: ssh_public_key_path file not found."
)

# =============================================================================
# BACKUP_OIM_LOGS CONFIGURATION MESSAGES
# =============================================================================

DOMAINS_LIST_EMPTY_MSG = (
    "backup_oim_logs_config: domains list cannot be empty when specified."
)

INVALID_DOMAIN_NAME_MSG = (
    "backup_oim_logs_config: '{domain}' is not a valid Omnia domain. "
    "Valid domains: repo_manager, image_build_manager, orchestrator, "
    "discovery, telemetry, build_stream, utils."
)

# =============================================================================
# SLURM_CONFIG_UTIL CONFIGURATION MESSAGES
# =============================================================================

OMNIA_CONFIG_PATH_INVALID_MSG = (
    "slurm_config_util_config: omnia_config_path must be a valid file path."
)

STORAGE_CONFIG_PATH_INVALID_MSG = (
    "slurm_config_util_config: storage_config_path must be a valid file path."
)

PXE_MAPPING_PATH_INVALID_MSG = (
    "slurm_config_util_config: pxe_mapping_path must be a valid file path "
    "with .yaml or .csv extension."
)

BACKUP_PATH_INVALID_MSG = (
    "slurm_config_util_config: backup_path must be a valid local path or "
    "NFS export format (server:/path)."
)

CLEANUP_CONFIRM_TOKEN_INVALID_MSG = (
    "slurm_config_util_config: slurm_cleanup_confirm_token must be 'YES' "
    "to proceed with destructive cleanup operations."
)

ROLLBACK_LIMIT_INVALID_MSG = (
    "slurm_config_util_config: rollback_backup_list_limit must be a positive integer."
)

# =============================================================================
# SCHEMA VALIDATION MESSAGES
# =============================================================================


def schema_type_mismatch_msg(file_label, expected, actual):
    """Returns message when top-level type doesn't match schema."""
    return f"{file_label}: Expected {expected} at top level, got {actual}"


def missing_required_property_msg(file_label, prop_name):
    """Returns message for a missing required property."""
    return f"{file_label}: Missing required property '{prop_name}'"


def invalid_enum_value_msg(file_label, prop_name, value, allowed):
    """Returns message for an invalid enum value."""
    return (
        f"{file_label}: Property '{prop_name}' has invalid value "
        f"'{value}'. Allowed: {allowed}"
    )


def unexpected_property_msg(file_label, prop_name):
    """Returns message for an unexpected additional property."""
    return f"{file_label}: Unexpected property '{prop_name}'"


# =============================================================================
# FILE-LEVEL MESSAGES
# =============================================================================


def required_file_not_found_msg(path):
    """Returns message when a required config file is missing."""
    return f"Required file not found: {path}"


def yaml_parse_failed_msg(path):
    """Returns message when YAML parsing fails."""
    return f"Failed to parse YAML: {path}"


def schema_file_not_found_msg(path):
    """Returns message when a schema file is missing."""
    return f"Schema file not found: {path}"


# =============================================================================
# LOG HEADER/FOOTER MESSAGES
# =============================================================================

VALIDATION_START_MSG = "=== Utils Domain Validation Start ==="
VALIDATION_END_MSG = "=== Utils Domain Validation End ==="
