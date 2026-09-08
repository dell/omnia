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
"""User-facing messages for Orchestrator input validation."""

from typing import Any


VALIDATION_START_MSG = "=== Orchestrator Validation Start ==="
VALIDATION_END_MSG = "=== Orchestrator Validation End ==="
LANGUAGE_REQUIRED_MSG = (
    "orchestrator_config: 'language' is required and must not be empty."
)
NETWORK_SPEC_EMPTY_MSG = (
    "network_spec: File is empty or not a valid YAML object."
)
NETWORK_SPEC_NETWORKS_REQUIRED_MSG = (
    "network_spec: 'Networks' list is required and must not be empty."
)
NETWORK_SPEC_ADMIN_REQUIRED_MSG = (
    "network_spec: At least one 'admin_network' entry is required in Networks."
)
NETWORK_SPEC_NETMASK_REQUIRED_MSG = (
    "network_spec: admin_network.netmask_bits is required."
)


def required_file_not_found_msg(path: str) -> str:
    """Return the required-file error message."""
    return f"Required file not found: {path}"


def optional_file_skipped_msg(path: str) -> str:
    """Return the optional-file skip message."""
    return f"Optional file not found (skipped): {path}"


def vault_file_skipped_msg(path: str) -> str:
    """Return the vault-encrypted file skip message."""
    return f"Vault-encrypted file (skipped schema check): {path}"


def yaml_parse_failed_msg(path: str) -> str:
    """Return the YAML parsing error message."""
    return f"Failed to parse YAML: {path}"


def schema_file_not_found_msg(path: str) -> str:
    """Return the missing-schema error message."""
    return f"Schema file not found: {path}"


def invalid_schema_msg(file_label: str, detail: str) -> str:
    """Return the invalid-schema error message."""
    return f"{file_label}: Invalid JSON schema: {detail}"


def schema_validation_msg(path: str, detail: str) -> str:
    """Return a JSON Schema validation error message."""
    return f"{path}: {detail}"


def language_unsupported_msg(language: Any) -> str:
    """Return the unsupported-language error message."""
    return (
        f"orchestrator_config: 'language' value '{language}' is not supported. "
        "Must contain 'en_US.UTF-8'."
    )


def lease_time_invalid_msg(value: Any) -> str:
    """Return the invalid DHCP lease-time error message."""
    return (
        f"orchestrator_config: 'default_lease_time' value '{value}' is invalid. "
        "Must be a positive integer (seconds)."
    )


def kernel_version_format_msg(value: Any) -> str:
    """Return the invalid kernel-version error message."""
    return (
        "orchestrator_config: 'kernel_version_override' value "
        f"'{value}' does not match expected format X.Y.Z-<suffix> "
        "(e.g. 5.14.0-427.13.1.el9_4.x86_64)."
    )


def s3_endpoint_required_msg(provider: str) -> str:
    """Return the missing S3 endpoint error message."""
    return (
        "orchestrator_config: 's3_endpoint' is required when "
        f"s3_storage_provider is '{provider}'."
    )


def s3_endpoint_ignored_msg() -> str:
    """Return the warning for an endpoint supplied with managed MinIO."""
    return (
        "orchestrator_config: 's3_endpoint' should not be set when "
        "s3_storage_provider is 'minio' (auto-managed)."
    )


def cloud_init_file_missing_msg(path: str) -> str:
    """Return the missing additional cloud-init file error message."""
    return (
        "orchestrator_config: 'additional_cloud_init_config_file' path "
        f"'{path}' does not exist."
    )


def pxe_mapping_not_found_msg(path: str) -> str:
    """Return the missing PXE mapping file error message."""
    return f"orchestrator_config: pxe_mapping_file_path '{path}' does not exist."


def pxe_mapping_read_failed_msg(path: str, detail: str) -> str:
    """Return the PXE mapping read error message."""
    return f"orchestrator_config: Failed to read mapping file '{path}': {detail}"


def pxe_mapping_missing_columns_msg(path: str, columns: list[str]) -> str:
    """Return the missing PXE mapping columns error message."""
    return (
        f"orchestrator_config: Mapping file '{path}' is missing required "
        f"columns: {columns}"
    )


def pxe_mapping_duplicates_msg(field: str, values: list[str]) -> str:
    """Return a duplicate PXE mapping value error message."""
    return f"orchestrator_config: Duplicate {field}(s) in mapping file: {values}"


def pxe_mapping_invalid_ip_msg(address: str) -> str:
    """Return an invalid PXE ADMIN_IP error message."""
    return f"orchestrator_config: Invalid ADMIN_IP '{address}' in mapping file."


def mapping_ip_outside_subnets_msg(address: str, networks: list[str]) -> str:
    """Return the mapping IP subnet-membership error message."""
    return (
        f"orchestrator_config: ADMIN_IP '{address}' in mapping file is not in "
        f"any configured admin subnet: {', '.join(networks)}."
    )


def network_entry_type_msg(label: str) -> str:
    """Return the invalid network entry type error message."""
    return f"network_spec: {label} must be an object."


def network_definition_invalid_msg(label: str) -> str:
    """Return the invalid network address/prefix error message."""
    return (
        f"network_spec: {label}.subnet/netmask_bits must define an IPv4 "
        "network address."
    )


def router_outside_network_msg(label: str, router: str, network: str) -> str:
    """Return the router subnet-membership error message."""
    return f"network_spec: {label}.router '{router}' is outside {network}."


def dynamic_range_invalid_msg(label: str) -> str:
    """Return the invalid DHCP range error message."""
    return (
        f"network_spec: {label}.dynamic_range must be an ordered IPv4 "
        "start_ip-end_ip range."
    )


def dynamic_range_outside_network_msg(label: str, network: str) -> str:
    """Return the DHCP range subnet-membership error message."""
    return f"network_spec: {label}.dynamic_range is outside {network}."


def admin_ip_invalid_msg(address: str) -> str:
    """Return the invalid primary admin IP error message."""
    return (
        "network_spec: admin_network.primary_oim_admin_ip "
        f"'{address}' is not a valid IPv4 address."
    )


def admin_ip_outside_network_msg(address: str, network: str) -> str:
    """Return the primary admin IP subnet-membership error message."""
    return (
        "network_spec: admin_network.primary_oim_admin_ip "
        f"'{address}' is outside {network}."
    )


def admin_ip_in_dynamic_range_msg() -> str:
    """Return the primary admin IP DHCP-range error message."""
    return (
        "network_spec: admin_network.primary_oim_admin_ip must not be inside "
        "dynamic_range."
    )


def subnet_overlap_msg(label: str) -> str:
    """Return the overlapping subnet error message."""
    return f"network_spec: {label} overlaps another configured admin subnet."


def dynamic_range_overlap_msg(label: str) -> str:
    """Return the overlapping DHCP range error message."""
    return (
        f"network_spec: {label}.dynamic_range overlaps another configured "
        "DHCP range."
    )


def storage_required_msg(references: list[str]) -> str:
    """Return the conditionally required storage file error message."""
    return (
        "storage_config.yml is required because omnia_config.yml references "
        f"storage: {', '.join(references)}"
    )


def duplicate_storage_names_msg(names: list[str]) -> str:
    """Return the duplicate storage mount-name error message."""
    return f"storage_config.yml contains duplicate mount names: {', '.join(names)}"


def missing_storage_names_msg(names: list[str]) -> str:
    """Return the missing referenced-storage error message."""
    return (
        "storage_config.yml does not define referenced storage: "
        f"{', '.join(names)}"
    )


def l2_validation_errors_msg(file_label: str, errors: list[str]) -> str:
    """Return the L2 validation log message."""
    return f"L2 {file_label} errors: {errors}"


def validation_status_msg(status: str) -> str:
    """Return the overall validation status message."""
    return f"Orchestrator configuration validation {status}."


def validation_counts_msg(valid_count: int, invalid_count: int) -> str:
    """Return the validation file-count message."""
    return f"Valid files: {valid_count}, Invalid files: {invalid_count}."


def validation_log_msg(path: str) -> str:
    """Return the validation log path message."""
    return f"Log file: {path}"
