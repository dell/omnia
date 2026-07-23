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
Common validation messages used across all validators.

This module contains generic validation messages that are not specific
to any particular configuration file or domain.
"""

# =============================================================================
# GENERIC VALIDATION MESSAGES
# =============================================================================

MANDATORY_FIELD_FAIL_MSG = "must not be empty"
FILE_PATH_FAIL_MSG = "path does not exist"

# =============================================================================
# GROUP AND ROLE MESSAGES
# =============================================================================

MAX_NUMBER_OF_ROLES_MSG = "A max of 100 roles can be supported."
MIN_NUMBER_OF_GROUPS_MSG = "At least 1 group is required."
MIN_NUMBER_OF_ROLES_MSG = "At least 1 role is required."
MAX_NUMBER_OF_ROLES_PER_GROUP_MSG = "Groups can support a maximum of 5 roles."
GRP_EXIST_MSG = "A valid group must be provided."
GRP_ROLE_MSG = "Please associate this group with a role."
INVALID_GROUP_NAME_MSG = "Groups must be defined in the form of grp<n> where n is 0-99."
DUPLICATE_GROUP_NAME_MSG = "Duplicate group names are not allowed."
NO_GROUPS_MSG = "Outer Group object was probably not defined."
NO_ROLES_MSG = "Outer Role object was probably not defined."
INVALID_ATTRIBUTES_ROLE_MSG = (
    "Please provide valid attributes for the role, both 'name' and 'groups' are mandatory."
)

# =============================================================================
# SWITCH MESSAGES
# =============================================================================

INVALID_SWITCH_IP_MSG = "Please provide a valid switch IPv4 address (example: 10.5.0.1)."
INVALID_SWITCH_PORTS_MSG = "Please provide any port ranges as start-end (example: 0-15,4:4,51-53)."
DUPLICATE_SWITCH_IP_PORT_MSG = "Please remove duplicate ports."
SWITCH_DETAILS_INCOMPLETE_MSG = (
    "If providing switch details, please provide both the IP and Ports fields."
)
SWITCH_DETAILS_NO_BMC_DETAILS_MSG = (
    "If switch details are provided then bmc_detail's static_range must also be provided."
)

# =============================================================================
# BMC MESSAGES
# =============================================================================

BMC_STATIC_RANGE_INVALID_MSG = (
    "Static range should be in the following format: IPv4Start-IPv4End (example: 10.5.0.1-10.5.0.200)."
)
OVERLAPPING_STATIC_RANGE = "bmc_detail's static_range is overlapping with other static ranges."

# =============================================================================
# PASSWORD MESSAGES
# =============================================================================

INVALID_PASSWORD_MSG = (
    "Provided password is invalid. Password must meet the specified requirements: "
    "should not be empty, must have a length of at least 8 characters, and should not "
    "contain the following characters: '-', '\\', \"'\", or '\"'"
)

BMC_PASSWORD_FAIL_MSG = (
    "Incorrect bmc_password format. Password must meet the specified requirements: "
    "should not be empty, must have a length of at least 3 characters, and should not "
    "contain the following characters: '-', '\\', \"'\", or '\"'"
)

DOCKER_PASSWORD_FAIL_MSG = "Docker password must not be empty."


def bmc_username_fail_msg(min_username_length, max_length):
    """Returns a formatted message indicating bmc_username_fail_msg."""
    return (
        f"bmc_username length must be between {min_username_length} and "
        f"{max_length} characters. Must not contain '-', '\\', \"'\", or '\"'"
    )

# =============================================================================
# BOOLEAN VALIDATION
# =============================================================================


def boolean_fail_msg(value):
    """Returns a formatted message indicating boolean_fail_msg."""
    return f"{value} must be set to either true or false."

# =============================================================================
# TLS/CERTIFICATE MESSAGES
# =============================================================================


def tls_ext_fail_msg(valid_extensions):
    """Returns a formatted message indicating tls_ext_fail_msg."""
    extensions_list = ' or '.join(valid_extensions)
    return f"should have {extensions_list} extension"

# =============================================================================
# LOG FORMATTING
# =============================================================================


def get_header():
    """Returns a formatted header string for execution logs."""
    return f"{'#' * 30} START EXECUTION {'#' * 30}"


def get_footer():
    """Returns a formatted footer string for execution logs."""
    return f"{'#' * 30} END EXECUTION {'#' * 30}"


def get_validation_initiated(input_file_path):
    """Returns a formatted message indicating validation has started."""
    return f"{'#' * 10} Validation Initiated for {input_file_path} {'#' * 10}"


def get_schema_failed(input_file_path):
    """Returns a formatted message indicating schema validation failure."""
    return f"{'#' * 10} Schema validation failed for {input_file_path} {'#' * 10}"


def get_schema_success(input_file_path):
    """Returns a formatted message indicating schema validation success."""
    return f"{'#' * 10} Schema validation successful for {input_file_path} {'#' * 10}"


def get_logic_failed(input_file_path):
    """Returns a formatted message indicating logic validation failure."""
    return f"{'#' * 10} Logic validation failed for {input_file_path} {'#' * 10}"


def get_logic_success(input_file_path):
    """Returns a formatted message indicating logic validation success."""
    return f"{'#' * 10} Logic validation successful for {input_file_path} {'#' * 10}"
