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

def schema_type_mismatch_msg(file_label, expected, actual) -> str:
    """Returns message when top-level type doesn't match schema."""
    return f"[{file_label}] Expected type '{expected}', got '{actual}'."


def missing_required_property_msg(file_label, prop) -> str:
    """Returns message for a missing required property."""
    return f"[{file_label}] Missing required property: '{prop}'."


def invalid_enum_value_msg(file_label, prop, value, allowed) -> str:
    """Returns message for an invalid enum value."""
    return (
        f"[{file_label}] Invalid value for '{prop}': '{value}'. "
        f"Allowed: {allowed}."
    )


def unexpected_property_msg(file_label, prop) -> str:
    """Returns message for an unexpected additional property."""
    return f"[{file_label}] Unexpected property: '{prop}'."


# =============================================================================
# BUILD STREAM CONFIG MESSAGES (L2)
# =============================================================================

def build_stream_disabled_msg() -> str:
    """Returns message when build_stream is disabled."""
    return "enable_build_stream is set to false. Skipping validation."


def missing_host_ip_msg() -> str:
    """Returns message when build_stream_host_ip is missing."""
    return (
        "build_stream_host_ip is required when enable_build_stream is true. "
        "Provide the IP address of the OIM server."
    )


def invalid_port_msg(port) -> str:
    """Returns message for an invalid BSM port."""
    return (
        f"build_stream_port '{port}' is invalid. "
        "Must be a number between 1 and 65535."
    )


def missing_gitlab_host_msg() -> str:
    """Returns message when gitlab_host is missing."""
    return (
        "gitlab_host is required when enable_build_stream is true. "
        "Provide the IP address of the GitLab server."
    )


def invalid_gitlab_mode_msg() -> str:
    """Returns message when gitlab_mode is missing or not an allowed value."""
    return "gitlab_mode must be 'hosted' or 'external'."


def missing_external_param_msg(param) -> str:
    """Returns message when a parameter required for external mode is missing."""
    return f"{param} is required when gitlab_mode is 'external'."


def invalid_external_url_msg(value) -> str:
    """Returns message when gitlab_external_url is not an HTTPS URL."""
    return (
        f"gitlab_external_url '{value}' is invalid. Provide an HTTPS URL, "
        "for example https://gitlab.example.com."
    )


def invalid_project_namespace_msg(value) -> str:
    """Returns message when gitlab_project_namespace is malformed."""
    return (
        f"gitlab_project_namespace '{value}' is invalid. Use a GitLab group path "
        "such as 'infra/omnia-builds' (letters, digits, '_', '.', '-' and '/')."
    )


def gitlab_host_ignored_warning_msg() -> str:
    """Returns warning when gitlab_host is set although gitlab_mode is external."""
    return "WARNING: gitlab_host is ignored when gitlab_mode is 'external'."


def external_params_ignored_warning_msg() -> str:
    """Returns warning when external-only parameters are set in hosted mode."""
    return (
        "WARNING: gitlab_external_url and gitlab_project_namespace are ignored "
        "when gitlab_mode is 'hosted'."
    )


def ca_cert_error_msg(detail) -> str:
    """Returns message for a custom CA certificate problem."""
    return str(detail)


def unsupported_gitlab_version_msg(version) -> str:
    """Returns message when the external GitLab version is outside 17.x-19.x."""
    return (
        f"GitLab version {version} is not supported. "
        "Supported versions: 17.x, 18.x, 19.x."
    )


def missing_pat_scopes_msg(missing) -> str:
    """Returns message when the personal access token lacks required scopes."""
    return (
        f"gitlab_api_token is missing required scope(s): {', '.join(missing)}. "
        "Create the token with the 'api' and 'write_repository' scopes."
    )


def insufficient_namespace_role_msg(namespace) -> str:
    """Returns message when the token user is not Owner/Maintainer on the namespace."""
    return (
        f"The gitlab_api_token user needs the Owner or Maintainer role on "
        f"namespace '{namespace}'."
    )


def invalid_gitlab_port_msg(port) -> str:
    """Returns message for an invalid GitLab HTTPS port."""
    return (
        f"gitlab_https_port '{port}' is invalid. "
        "Must be a number between 1 and 65535."
    )


def same_host_warning_msg() -> str:
    """Returns warning when BSM and GitLab share the same host."""
    return (
        "WARNING: build_stream_host_ip and gitlab_host are the same. "
        "GitLab and BSM should run on separate hosts for production."
    )


def log_tail_default_exceeds_max_msg(default, maximum) -> str:
    """Returns message when log_tail_lines_default is above log_tail_lines_max."""
    return (
        f"log_tail_lines_default ({default}) must not exceed "
        f"log_tail_lines_max ({maximum})."
    )


def log_ci_preview_exceeds_max_msg(preview, maximum) -> str:
    """Returns message when log_ci_preview_lines is above log_tail_lines_max."""
    return (
        f"log_ci_preview_lines ({preview}) must not exceed "
        f"log_tail_lines_max ({maximum}); the CI preview uses the log query API."
    )


# =============================================================================
# REDACTION MESSAGES (L2)
# =============================================================================

def invalid_redaction_key_name_msg(index) -> str:
    """Returns message when an operator secret key name is not valid."""
    return f"redaction.additional_secret_key_names[{index}] is not a valid key name."


def invalid_redaction_pattern_id_msg(index) -> str:
    """Returns message when an operator pattern id is missing or not valid."""
    return f"redaction.additional_secret_patterns[{index}] has an invalid id."


def reserved_redaction_id_msg(rule_id) -> str:
    """Returns message when an operator pattern reuses a baseline or built-in rule id."""
    return (
        f"redaction.additional_secret_patterns: id '{rule_id}' is reserved "
        "by a built-in or baseline rule."
    )


def duplicate_redaction_id_msg(rule_id) -> str:
    """Returns message when two operator patterns share a rule id."""
    return f"redaction.additional_secret_patterns: id '{rule_id}' is used more than once."


def unsafe_redaction_pattern_msg(label, reason) -> str:
    """Returns message when an operator pattern fails the pattern-safety check."""
    return f"redaction.additional_secret_patterns {label} is unsafe: {reason}."


# =============================================================================
# CREDENTIAL MESSAGES (L2)
# =============================================================================

def missing_credential_msg(field) -> str:
    """Returns message when a required credential field is missing."""
    return f"Required credential field '{field}' is missing or empty."


def vault_encrypted_msg(file_path) -> str:
    """Returns message when a vault-encrypted file is encountered."""
    return (
        f"Credentials file '{file_path}' is Ansible Vault encrypted. "
        "Decrypt before validation or provide vault password."
    )


# =============================================================================
# FILE-LEVEL MESSAGES
# =============================================================================


def required_file_not_found_msg(path) -> str:
    """Returns message when a required config file is missing."""
    return f"Required file not found: {path}"


def yaml_parse_failed_msg(path) -> str:
    """Returns message when YAML parsing fails."""
    return f"Failed to parse YAML: {path}"


def schema_file_not_found_msg(path) -> str:
    """Returns message when a schema file is missing."""
    return f"Schema file not found: {path}"


# =============================================================================
# LOG HEADER/FOOTER MESSAGES
# =============================================================================

VALIDATION_START_MSG = "=== Build Stream Validation Start ==="
VALIDATION_END_MSG = "=== Build Stream Validation End ==="
