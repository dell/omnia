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
User-facing validation messages for build_stream input validation.

All messages are centralized here for consistency and i18n readiness.
"""


# =============================================================================
# SCHEMA VALIDATION MESSAGES (L1)
# =============================================================================

def schema_type_mismatch_msg(file_label, expected, actual):
    """Returns message when top-level type doesn't match schema."""
    return f"[{file_label}] Expected type '{expected}', got '{actual}'."


def missing_required_property_msg(file_label, prop):
    """Returns message for a missing required property."""
    return f"[{file_label}] Missing required property: '{prop}'."


def invalid_enum_value_msg(file_label, prop, value, allowed):
    """Returns message for an invalid enum value."""
    return (
        f"[{file_label}] Invalid value for '{prop}': '{value}'. "
        f"Allowed: {allowed}."
    )


def unexpected_property_msg(file_label, prop):
    """Returns message for an unexpected additional property."""
    return f"[{file_label}] Unexpected property: '{prop}'."


# =============================================================================
# BUILD STREAM CONFIG MESSAGES (L2)
# =============================================================================

def build_stream_disabled_msg():
    """Returns message when build_stream is disabled."""
    return "enable_build_stream is set to false. Skipping validation."


def missing_host_ip_msg():
    """Returns message when build_stream_host_ip is missing."""
    return (
        "build_stream_host_ip is required when enable_build_stream is true. "
        "Provide the IP address of the OIM server."
    )


def invalid_port_msg(port):
    """Returns message for an invalid BSM port."""
    return (
        f"build_stream_port '{port}' is invalid. "
        "Must be a number between 1 and 65535."
    )


def missing_gitlab_host_msg():
    """Returns message when gitlab_host is missing."""
    return (
        "gitlab_host is required when enable_build_stream is true. "
        "Provide the IP address of the GitLab server."
    )


def invalid_gitlab_port_msg(port):
    """Returns message for an invalid GitLab HTTPS port."""
    return (
        f"gitlab_https_port '{port}' is invalid. "
        "Must be a number between 1 and 65535."
    )


def same_host_warning_msg():
    """Returns warning when BSM and GitLab share the same host."""
    return (
        "WARNING: build_stream_host_ip and gitlab_host are the same. "
        "GitLab and BSM should run on separate hosts for production."
    )


# =============================================================================
# CREDENTIAL MESSAGES (L2)
# =============================================================================

def missing_credential_msg(field):
    """Returns message when a required credential field is missing."""
    return f"Required credential field '{field}' is missing or empty."


def vault_encrypted_msg(file_path):
    """Returns message when a vault-encrypted file is encountered."""
    return (
        f"Credentials file '{file_path}' is Ansible Vault encrypted. "
        "Decrypt before validation or provide vault password."
    )


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

VALIDATION_START_MSG = "=== Build Stream Validation Start ==="
VALIDATION_END_MSG = "=== Build Stream Validation End ==="
