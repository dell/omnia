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
Image build manager validation messages.

This module contains all user-facing validation messages for the
image_build_manager domain. Messages are grouped by config file
and validation concern.
"""

# =============================================================================
# S3 CONFIGURATION MESSAGES
# =============================================================================

S3_ENDPOINT_REQUIRED_POWERSCALE_MSG = (
    "image_build_config: s3_configurations.endpoint_url is required "
    "when provider is 'powerscale'."
)

S3_ENDPOINT_NOT_SET_MINIO_MSG = (
    "image_build_config: s3_configurations.endpoint_url should not be set "
    "when provider is 'minio' (auto-managed by deploy_minio role)."
)

# =============================================================================
# AARCH64 CONFIGURATION MESSAGES
# =============================================================================

AARCH64_SSH_USER_REQUIRED_MSG = (
    "image_build_config: aarch64_ssh_user is required when "
    "aarch64_inventory_host_ip is set."
)

# =============================================================================
# BUILD IMAGE SETTINGS MESSAGES
# =============================================================================


def build_timeout_too_low_msg(build_timeout):
    """Returns message when build_timeout is below minimum."""
    return (
        f"image_build_config: build_image.build_timeout ({build_timeout}s) must be >= "
        f"600s (10 minutes). Image builds typically take 5–30 minutes."
    )


MAX_PARALLEL_INVALID_MSG = (
    "image_build_config: build_image.max_parallel must be 0 (unlimited) "
    "or a positive integer."
)

# =============================================================================
# FUNCTIONAL GROUPS MESSAGES
# =============================================================================

FUNCTIONAL_GROUPS_REQUIRED_MSG = (
    "image_build_config: functional_groups list in image_build_config.yml is "
    "deprecated. Groups are now derived from package_groups.yml keys (config "
    "mode) or catalog layers (catalog mode)."
)

FUNCTIONAL_GROUPS_IGNORED_MSG = (
    "image_build_config: functional_groups list in image_build_config.yml is "
    "deprecated and will be ignored. Groups are derived from package_groups.yml "
    "keys (config mode) or catalog layers (catalog mode)."
)

# =============================================================================
# CREDENTIAL VALIDATION MESSAGES
# =============================================================================

S3_ACCESS_ID_REQUIRED_MSG = (
    "image_build_credentials: s3_access_id is required when "
    "s3_configurations.provider is 'powerscale'."
)

AARCH64_SSH_PASSWORD_REQUIRED_MSG = (
    "image_build_credentials: aarch64_ssh_password is required when "
    "aarch64_inventory_host_ip is set."
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

VALIDATION_START_MSG = "=== Image Build Manager Validation Start ==="
VALIDATION_END_MSG = "=== Image Build Manager Validation End ==="
