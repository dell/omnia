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
Validation error/warning message constants for the orchestrator domain.

All message strings are defined here as UPPER_SNAKE_CASE constants to
keep validator logic free of inline strings.
"""

# ── orchestrator_config.yml messages ─────────────────────────────────────────

LANGUAGE_REQUIRED_MSG = "orchestrator_config: 'language' is required and must not be empty."
LANGUAGE_UNSUPPORTED_MSG = (
    "orchestrator_config: 'language' value '{}' is not supported. "
    "Must contain 'en_US.UTF-8'."
)

LEASE_TIME_INVALID_MSG = (
    "orchestrator_config: 'default_lease_time' value '{}' is invalid. "
    "Must be a positive integer (seconds)."
)

KERNEL_VERSION_FORMAT_MSG = (
    "orchestrator_config: 'kernel_version_override' value '{}' does not "
    "match expected format X.Y.Z-<suffix> (e.g. 5.14.0-427.13.1.el9_4.x86_64)."
)

CLOUD_INIT_FILE_MISSING_MSG = (
    "orchestrator_config: 'additional_cloud_init_config_file' path "
    "'{}' does not exist."
)

PXE_MAPPING_REQUIRED_MSG = "orchestrator_config: 'pxe_mapping_file_path' is required."
PXE_MAPPING_NOT_FOUND_MSG = "orchestrator_config: pxe_mapping_file_path '{}' does not exist."
PXE_MAPPING_READ_FAILED_MSG = "orchestrator_config: Failed to read mapping file '{}': {}"
PXE_MAPPING_MISSING_COLUMNS_MSG = (
    "orchestrator_config: Mapping file '{}' is missing required columns: {}"
)
PXE_MAPPING_DUP_SERVICE_TAG_MSG = "orchestrator_config: Duplicate SERVICE_TAG(s) in mapping file: {}"
PXE_MAPPING_DUP_HOSTNAME_MSG = "orchestrator_config: Duplicate HOSTNAME(s) in mapping file: {}"
PXE_MAPPING_DUP_ADMIN_IP_MSG = "orchestrator_config: Duplicate ADMIN_IP(s) in mapping file: {}"
PXE_MAPPING_INVALID_IP_MSG = "orchestrator_config: Invalid ADMIN_IP '{}' in mapping file."

ADMIN_IP_NOT_IN_SUBNET_MSG = (
    "orchestrator_config: ADMIN_IP '{}' in mapping file is not in "
    "admin_network subnet {}/{}."
)

# ── network_spec.yml messages ────────────────────────────────────────────────

NETWORK_SPEC_EMPTY_MSG = "network_spec: File is empty or not a valid YAML object."
NETWORK_SPEC_NETWORKS_REQUIRED_MSG = "network_spec: 'Networks' list is required and must not be empty."
NETWORK_SPEC_ADMIN_IP_INVALID_MSG = (
    "network_spec: admin_network.primary_oim_admin_ip '{}' is not a valid IPv4 address."
)
NETWORK_SPEC_NETMASK_REQUIRED_MSG = "network_spec: admin_network.netmask_bits is required."
NETWORK_SPEC_ADMIN_REQUIRED_MSG = (
    "network_spec: At least one 'admin_network' entry is required in Networks."
)

# ── Engine messages ──────────────────────────────────────────────────────────

VALIDATOR_EXCEPTION_MSG = "{}: Validator {} raised: {}"
