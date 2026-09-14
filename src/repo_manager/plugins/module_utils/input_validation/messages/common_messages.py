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

INVALID_GROUP_NAME_MSG = "Groups must be defined in the form of grp<n> where n is 0-99."

# =============================================================================
# SWITCH MESSAGES
# =============================================================================

INVALID_SWITCH_PORTS_MSG = "Please provide any port ranges as start-end (example: 0-15,4:4,51-53)."

# =============================================================================
# REPO MANAGER VALIDATION MESSAGES
# =============================================================================

CERTIFICATE_FILE_NOT_FOUND_MSG = "Certificate file not found"
KEY_FILE_NOT_FOUND_MSG = "Key file not found"
NO_REQUIRED_REPO_URLS_MSG = "No required repo URLs found"
DUPLICATE_REPO_NAME_IN_ARCH_MSG = "Duplicate repo name '{name}' in {arch}"
PRIORITY_MUST_BE_INTEGER_MSG = "{repo_path}: priority must be integer"
PRIORITY_MUST_BE_IN_RANGE_MSG = "{repo_path}: priority must be 1-100"
ADDITIONAL_REPO_PRIORITY_CONFLICT_MSG = (
    "{repo_path}: additional_repos are published as one Pulp repository and "
    "must use one effective priority; found {priorities}"
)
MISSING_REPO_CONFIGURATION_MSG = (
    "Catalog package references repository '{reponame}' for architecture(s) {archs}, "
    "but this repository is not configured in repo_manager_config.yml under "
    "repositories.{cluster_os_version}.{{arch}}. Please add the repository configuration."
)
MISSING_REPO_URL_MSG = (
    "Catalog-selected repository '{reponame}' for architecture '{arch}' has no "
    "usable URL in repositories.{cluster_os_version}.{arch}"
)
MISSING_ARCH_SOURCE_MSG = (
    "Catalog-selected package '{package_name}' has no source for architecture "
    "'{arch}' or an explicit 'noarch' source"
)
RPM_REPO_STREAMED_POLICY_MSG = (
    "Catalog package '{package_name}' uses packagetype 'rpm_repo' from repository "
    "'{reponame}' for architecture '{arch}', but its effective Pulp policy is "
    "'streamed'. rpm_repo requires retained package payloads. Enable caching for "
    "this repository (caching: true) or select a non-streamed policy."
)



# =============================================================================
# BOOLEAN VALIDATION
# =============================================================================



# =============================================================================
# TLS/CERTIFICATE MESSAGES
# =============================================================================



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
