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
OMNIA_CONFIG_EMPTY_MSG = (
    "omnia_config.yml: File is empty or not a valid YAML object."
)
HA_CONFIG_EMPTY_MSG = (
    "high_availability_config.yml: File is missing, empty, or not a valid "
    "YAML object for the selected Kubernetes workload."
)
HA_OMNIA_CONFIG_INVALID_MSG = (
    "high_availability_config.yml: omnia_config.yml must define a valid "
    "service_k8s_cluster list."
)
HA_CONTROL_PLANE_REQUIRED_MSG = (
    "high_availability_config.yml: PXE mapping must contain at least one "
    "service_kube_control_plane functional group with a valid ADMIN_IP."
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


def cloud_init_yaml_parse_failed_msg(path: str, detail: str) -> str:
    """Return the invalid additional cloud-init YAML message."""
    return (
        f"additional_cloud_init: Failed to parse YAML file '{path}' "
        f"({detail})."
    )


def cloud_init_read_failed_msg(path: str, detail: str) -> str:
    """Return the unreadable additional cloud-init file message."""
    return (
        f"additional_cloud_init: Failed to read file '{path}' ({detail})."
    )


def cloud_init_type_msg(
    path: str, actual_type: str, expected: str
) -> str:
    """Return an additional cloud-init value-type error message."""
    return (
        f"additional_cloud_init: {path} must be {expected}, "
        f"not {actual_type}."
    )


def cloud_init_unknown_key_msg(path: str, key: str, allowed: str) -> str:
    """Return an unsupported additional cloud-init key message."""
    return (
        f"additional_cloud_init: {path} key '{key}' is unsupported; "
        f"only {allowed} are allowed."
    )


def cloud_init_prohibited_key_msg(path: str, key: str) -> str:
    """Return a platform-owned cloud-init key error message."""
    return (
        f"additional_cloud_init: {path} key '{key}' is platform-managed "
        "and must not be overridden."
    )


def cloud_init_required_field_msg(path: str, field: str) -> str:
    """Return a missing write-files field error message."""
    return (
        f"additional_cloud_init: {path}.{field} must be a non-empty string."
    )


def cloud_init_invalid_value_msg(
    path: str, value: str, allowed: str
) -> str:
    """Return an invalid additional cloud-init scalar-value message."""
    return (
        f"additional_cloud_init: {path} value '{value}' is invalid; "
        f"expected {allowed}."
    )


def cloud_init_invalid_group_msg(group_name: str) -> str:
    """Return a cloud-init functional-group selection error message."""
    return (
        f"additional_cloud_init: groups key '{group_name}' is not selected "
        "in pxe_mapping_file.csv."
    )


def pxe_mapping_not_found_msg(path: str) -> str:
    """Return the missing PXE mapping file error message."""
    return f"orchestrator_config: pxe_mapping_file_path '{path}' does not exist."


def pxe_mapping_read_failed_msg(path: str, detail: str) -> str:
    """Return the PXE mapping read error message."""
    return f"orchestrator_config: Failed to read mapping file '{path}': {detail}"


def pxe_mapping_empty_msg(path: str) -> str:
    """Return the empty PXE mapping error message."""
    return f"orchestrator_config: Mapping file '{path}' has no data rows."


def pxe_mapping_duplicate_headers_msg(
    path: str, headers: list[str]
) -> str:
    """Return the duplicate PXE mapping columns error message."""
    return (
        f"orchestrator_config: Mapping file '{path}' has duplicate columns: "
        f"{headers}"
    )


def pxe_mapping_noncanonical_headers_msg(
    path: str, headers: list[str]
) -> str:
    """Return a noncanonical PXE mapping header error message."""
    return (
        f"orchestrator_config: Mapping file '{path}' contains noncanonical "
        f"column names: {headers}. Use the uppercase column names from the "
        "shipped pxe_mapping_file.csv template."
    )


def pxe_mapping_header_contract_msg(
    path: str, actual: list[str], expected: list[str]
) -> str:
    """Return an exact PXE mapping header-contract error message."""
    return (
        f"orchestrator_config: Mapping file '{path}' has header {actual}; "
        f"expected exactly {expected}. Preserve all columns in this order, "
        "including IB_NIC_NAME and IB_IP."
    )


def pxe_mapping_row_width_msg(
    path: str, row: int, actual: int, expected: int
) -> str:
    """Return the malformed PXE mapping row-width error message."""
    return (
        f"orchestrator_config: Mapping file '{path}' row {row} has {actual} "
        f"columns; expected {expected}."
    )


def pxe_mapping_required_cell_msg(field: str, row: int) -> str:
    """Return the missing required PXE mapping cell error message."""
    return (
        f"orchestrator_config: Mapping row {row} requires a non-empty "
        f"{field}."
    )


def pxe_mapping_invalid_tag_msg(
    field: str, value: str, row: int
) -> str:
    """Return an invalid optional service-tag error message."""
    return (
        f"orchestrator_config: Invalid {field} '{value}' at mapping row "
        f"{row}; when set, the value must be alphanumeric."
    )


def pxe_mapping_invalid_mac_msg(
    field: str, value: str, row: int
) -> str:
    """Return an invalid PXE mapping MAC-address error message."""
    return (
        f"orchestrator_config: Invalid {field} '{value}' at mapping row "
        f"{row}; expected six hexadecimal octets separated consistently "
        "by ':' or '-'."
    )


def pxe_mapping_invalid_ip_field_msg(
    field: str, value: str, row: int
) -> str:
    """Return an invalid PXE mapping IPv4 error message."""
    return (
        f"orchestrator_config: Invalid IPv4 {field} '{value}' at mapping "
        f"row {row}."
    )


def pxe_mapping_invalid_hostname_msg(value: str, row: int) -> str:
    """Return an invalid PXE mapping hostname error message."""
    return (
        f"orchestrator_config: Invalid HOSTNAME '{value}' at mapping row "
        f"{row}; expected a lowercase hostname label that starts with a "
        "letter."
    )


def pxe_mapping_dns_hostname_msg(value: str, row: int) -> str:
    """Return a DNS-enabled PXE hostname-policy error message."""
    return (
        f"orchestrator_config: HOSTNAME '{value}' at mapping row {row} "
        "must match nid001-nid999 when dns_enabled is true."
    )


def pxe_mapping_invalid_group_msg(value: str, row: int) -> str:
    """Return an invalid PXE logical-group name error message."""
    return (
        f"orchestrator_config: Invalid GROUP_NAME '{value}' at mapping row "
        f"{row}; expected grp0-grp100 or an SU name ending in 1-100."
    )


def pxe_mapping_invalid_functional_group_msg(value: str, row: int) -> str:
    """Return an invalid functional-group name error message."""
    return (
        f"orchestrator_config: Invalid FUNCTIONAL_GROUP_NAME '{value}' at "
        f"mapping row {row}; use letters, numbers, underscores, or hyphens."
    )


def pxe_mapping_unsupported_functional_group_msg(value: str, row: int) -> str:
    """Return an unsupported PXE functional-group error message."""
    return (
        f"orchestrator_config: FUNCTIONAL_GROUP_NAME '{value}' at mapping "
        f"row {row} uses the unsupported baseos_* prefix; use the "
        "corresponding os_* functional group instead."
    )


def pxe_mapping_functional_group_architecture_msg(
    value: str, row: int
) -> str:
    """Return a missing functional-group architecture suffix message."""
    return (
        f"orchestrator_config: FUNCTIONAL_GROUP_NAME '{value}' at mapping "
        f"row {row} must end in _x86_64 or _aarch64."
    )


def pxe_mapping_ib_pair_msg(row: int) -> str:
    """Return an incomplete InfiniBand mapping pair error message."""
    return (
        f"orchestrator_config: Mapping row {row} must set both IB_NIC_NAME "
        "and IB_IP, or leave both empty."
    )


def pxe_mapping_invalid_ib_nic_name_msg(value: str, row: int) -> str:
    """Return an unsupported InfiniBand NIC-name format message."""
    return (
        f"orchestrator_config: Invalid IB_NIC_NAME '{value}' at mapping row "
        f"{row}; supported formats are InfiniBand.PCIe.Slot.X-Y, "
        "InfiniBand.Slot.X-Y, NIC.InfiniBand.X-Y, and "
        "InfiniBand.Single-Y."
    )


def pxe_mapping_conflicting_group_msg(
    group: str, functional_groups: list[str]
) -> str:
    """Return a conflicting logical-group assignment error message."""
    return (
        f"orchestrator_config: GROUP_NAME '{group}' is assigned to "
        "conflicting functional groups: "
        f"{', '.join(functional_groups)}."
    )


def pxe_mapping_architecture_mismatch_msg(
    slurm_arches: list[str], compiler_arches: list[str]
) -> str:
    """Return an incompatible Slurm/compiler architecture error message."""
    return (
        "orchestrator_config: login_compiler_node architecture is "
        "incompatible with slurm_node; "
        f"Slurm={slurm_arches}, compiler={compiler_arches}."
    )


def pxe_mapping_unknown_catalog_group_msg(
    value: str, row: int, path: str
) -> str:
    """Return an active-catalog functional-group error message."""
    return (
        f"orchestrator_config: FUNCTIONAL_GROUP_NAME '{value}' at mapping "
        f"row {row} is not defined by active catalog '{path}'."
    )


def pxe_mapping_catalog_unavailable_msg(path: str, detail: str) -> str:
    """Return an explicitly configured catalog read error message."""
    return (
        f"orchestrator_config: Active catalog '{path}' cannot be used to "
        f"validate PXE functional groups: {detail}."
    )


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


def admin_bmc_ip_same_msg(label: str, address: str) -> str:
    """Return the duplicate OIM admin/BMC address error message."""
    return (
        f"network_spec: {label}.primary_oim_bmc_ip '{address}' must differ "
        "from primary_oim_admin_ip."
    )


def bmc_ip_in_dynamic_range_msg(
    label: str, address: str, range_label: str
) -> str:
    """Return the OIM BMC address DHCP-range error message."""
    return (
        f"network_spec: {label}.primary_oim_bmc_ip '{address}' must not be "
        f"inside {range_label}.dynamic_range."
    )


def ib_admin_subnet_overlap_msg(
    ib_label: str,
    ib_network: str,
    admin_label: str,
    admin_network: str,
) -> str:
    """Return the overlapping IB/admin subnet error message."""
    return (
        f"network_spec: {ib_label} subnet {ib_network} overlaps "
        f"{admin_label} subnet {admin_network}."
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


def omnia_duplicate_cluster_names_msg(
    section: str, names: list[str]
) -> str:
    """Return a duplicate Omnia cluster-name error message."""
    return (
        f"omnia_config.yml: '{section}' contains duplicate cluster_name "
        f"values: {', '.join(names)}."
    )


def omnia_selected_section_required_msg(section: str) -> str:
    """Return a selected-workload cluster-section error message."""
    return (
        f"omnia_config.yml: '{section}' must be a non-empty list because "
        "matching functional groups are selected in pxe_mapping_file.csv."
    )


def omnia_k8s_deployment_count_msg(count: int) -> str:
    """Return the Kubernetes deployment-selection error message."""
    return (
        "omnia_config.yml: Exactly one service_k8s_cluster entry must set "
        "deployment to true when Kubernetes functional groups are selected; "
        f"found {count}."
    )


def omnia_k8s_network_invalid_msg(cluster: str, field: str) -> str:
    """Return an invalid Kubernetes address-contract error message."""
    return (
        f"omnia_config.yml: Kubernetes cluster '{cluster}' has an invalid "
        f"{field}; CIDRs must be canonical IPv4 networks and external pools "
        "must be ordered IPv4 ranges or CIDRs."
    )


def omnia_k8s_network_overlap_msg(
    cluster: str, first: str, second: str
) -> str:
    """Return an overlapping Kubernetes address-range error message."""
    return (
        f"omnia_config.yml: Kubernetes cluster '{cluster}' has overlapping "
        f"{first} and {second} address ranges."
    )


def omnia_k8s_physical_network_overlap_msg(
    cluster: str, field: str, networks: list[str]
) -> str:
    """Return a Kubernetes/physical-network overlap error message."""
    return (
        f"omnia_config.yml: Kubernetes cluster '{cluster}' {field} overlaps "
        f"configured physical network(s): {', '.join(networks)}."
    )


def omnia_external_pool_address_conflict_msg(
    cluster: str, source: str, addresses: list[str]
) -> str:
    """Return a reserved-address conflict in the external pool."""
    return (
        f"omnia_config.yml: Kubernetes cluster '{cluster}' "
        "pod_external_ip_range contains address(es) reserved by "
        f"{source}: {', '.join(addresses)}."
    )


def omnia_external_pool_dhcp_overlap_msg(
    cluster: str, ranges: list[str]
) -> str:
    """Return an external-pool/DHCP overlap error message."""
    return (
        f"omnia_config.yml: Kubernetes cluster '{cluster}' "
        "pod_external_ip_range overlaps DHCP pool(s): "
        f"{', '.join(ranges)}."
    )


def omnia_storage_config_invalid_msg() -> str:
    """Return an invalid selected-workload storage structure message."""
    return (
        "omnia_config.yml: Referenced storage cannot be validated because "
        "storage_config.yml does not define a valid mounts list."
    )


def omnia_storage_reference_count_msg(
    section: str,
    cluster: str,
    field: str,
    name: str,
    count: int,
) -> str:
    """Return an unresolved or duplicate storage-reference message."""
    return (
        f"omnia_config.yml: {section} cluster '{cluster}' {field} '{name}' "
        "must match exactly one storage_config.yml mount; "
        f"found {count}."
    )


def omnia_storage_mount_on_oim_msg(
    section: str, cluster: str, field: str, name: str
) -> str:
    """Return a missing OIM-mount selection error message."""
    return (
        f"omnia_config.yml: {section} cluster '{cluster}' {field} '{name}' "
        "must reference a storage_config.yml mount with mount_on_oim set "
        "to true."
    )


def omnia_hardware_defaults_mode_msg(cluster: str, mode: str) -> str:
    """Return an incompatible hardware-discovery mode error message."""
    return (
        f"omnia_config.yml: Slurm cluster '{cluster}' defines "
        f"node_hardware_defaults while node_discovery_mode is '{mode}'; "
        "the mode must be 'homogeneous'."
    )


def omnia_hardware_defaults_groups_msg(
    cluster: str, groups: list[str]
) -> str:
    """Return an unknown Slurm hardware-default group error message."""
    return (
        f"omnia_config.yml: Slurm cluster '{cluster}' "
        "node_hardware_defaults references group(s) not assigned to mapped "
        f"Slurm compute nodes: {', '.join(groups)}."
    )


def omnia_slurm_config_file_missing_msg(
    cluster: str, config_name: str, path: str
) -> str:
    """Return a missing custom Slurm configuration error message."""
    return (
        f"omnia_config.yml: Slurm cluster '{cluster}' "
        f"config_sources.{config_name} path '{path}' is not a regular file."
    )


def omnia_slurm_config_file_invalid_msg(
    cluster: str, config_name: str, path: str
) -> str:
    """Return an invalid custom Slurm configuration error message."""
    return (
        f"omnia_config.yml: Slurm cluster '{cluster}' "
        f"config_sources.{config_name} file '{path}' cannot be parsed as a "
        "Slurm configuration."
    )


def omnia_slurm_config_duplicate_keys_msg(
    cluster: str, config_name: str, path: str, keys: list[str]
) -> str:
    """Return duplicate custom Slurm scalar keys."""
    return (
        f"omnia_config.yml: Slurm cluster '{cluster}' "
        f"config_sources.{config_name} file '{path}' contains duplicate "
        f"scalar key(s): {', '.join(keys)}."
    )


def omnia_slurm_config_invalid_keys_msg(
    cluster: str, config_name: str, keys: list[str]
) -> str:
    """Return unsupported custom Slurm configuration keys."""
    return (
        f"omnia_config.yml: Slurm cluster '{cluster}' "
        f"config_sources.{config_name} contains invalid key(s): "
        f"{', '.join(keys)}."
    )


def omnia_slurm_config_type_errors_msg(
    cluster: str, config_name: str, details: list[str]
) -> str:
    """Return custom Slurm configuration value-type errors."""
    return (
        f"omnia_config.yml: Slurm cluster '{cluster}' "
        f"config_sources.{config_name} has invalid value type(s): "
        f"{' | '.join(details)}."
    )


def omnia_powerscale_csi_not_deployed_msg(cluster: str) -> str:
    """Return a CSI enablement on a non-deployed cluster error message."""
    return (
        f"omnia_config.yml: Kubernetes cluster '{cluster}' enables "
        "PowerScale CSI but deployment is not true; CSI enablement is valid "
        "only on the deployed cluster."
    )


def omnia_powerscale_csi_file_missing_msg(
    cluster: str, file_kind: str, path: str
) -> str:
    """Return a missing PowerScale CSI input file error message."""
    return (
        f"omnia_config.yml: Kubernetes cluster '{cluster}' PowerScale CSI "
        f"{file_kind} path '{path}' is not a regular file."
    )


_POWERSCALE_CSI_CONTENT_REQUIREMENTS = {
    "yaml_mapping": "must be a readable, non-empty YAML mapping",
    "vault_key": (
        "is Ansible Vault encrypted but .csi_powerscale_secret_vault "
        "is missing"
    ),
    "vault_content": (
        "cannot be decrypted and parsed as YAML using "
        ".csi_powerscale_secret_vault"
    ),
    "isilon_clusters": "must define a non-empty isilonClusters list",
    "cluster_mapping": "requires every isilonClusters entry to be a mapping",
    "required_clusterName": (
        "requires every isilonClusters entry to define a non-empty "
        "clusterName string"
    ),
    "required_username": (
        "requires every isilonClusters entry to define a username string; "
        "credential collection populates its value"
    ),
    "required_password": (
        "requires every isilonClusters entry to define a password string; "
        "credential collection populates its value"
    ),
    "required_endpoint": (
        "requires every isilonClusters entry to define a non-empty endpoint "
        "string"
    ),
    "is_default": (
        "requires every isilonClusters entry to define isDefault as a boolean"
    ),
    "endpoint_port": (
        "requires endpointPort, when provided, to be an integer from 1 "
        "through 65535"
    ),
    "secret_skip_certificate_validation": (
        "requires skipCertificateValidation, when provided, to be a boolean"
    ),
    "isi_path": "requires isiPath to be an absolute path",
    "default_cluster": (
        "requires exactly one isilonClusters entry to set isDefault to true"
    ),
    "controller_count": "requires controller.controllerCount to equal 1",
    "replication_disabled": (
        "requires controller.replication.enabled to be false"
    ),
    "resizer_boolean": (
        "requires controller.resizer.enabled to be a boolean"
    ),
    "snapshot_enabled": "requires controller.snapshot.enabled to be true",
    "skip_certificate_validation": (
        "requires skipCertificateValidation to be a boolean"
    ),
    "isi_auth_type": "requires isiAuthType to be 0 or 1",
    "isi_access_zone": "requires isiAccessZone to be a non-empty string",
    "isi_volume_permissions": (
        "requires isiVolumePathPermissions to be a 3- or 4-digit octal string"
    ),
}


def omnia_powerscale_csi_content_msg(
    cluster: str, file_kind: str, path: str, issue: str
) -> str:
    """Return a PowerScale CSI file-content error message."""
    requirement = _POWERSCALE_CSI_CONTENT_REQUIREMENTS.get(issue, issue)
    return (
        f"omnia_config.yml: Kubernetes cluster '{cluster}' PowerScale CSI "
        f"{file_kind} file '{path}' {requirement}."
    )


def ha_entry_count_msg(count: int) -> str:
    """Return an HA configuration entry-count error message."""
    return (
        "high_availability_config.yml: Exactly one service_k8s_cluster_ha "
        "entry is required for the selected Kubernetes workload; "
        f"found {count}."
    )


def ha_omnia_deployment_count_msg(count: int) -> str:
    """Return an unresolved deployed Kubernetes cluster error message."""
    return (
        "high_availability_config.yml: Cannot resolve the active Kubernetes "
        "cluster because omnia_config.yml must contain exactly one deployed "
        f"service_k8s_cluster entry; found {count}."
    )


def ha_cluster_name_mismatch_msg(actual: str, expected: str) -> str:
    """Return an HA/Kubernetes cluster-name mismatch error message."""
    return (
        f"high_availability_config.yml: HA cluster_name '{actual}' must match "
        "the deployed omnia_config.yml Kubernetes cluster "
        f"'{expected}'."
    )


def ha_vip_invalid_msg(value: str) -> str:
    """Return an invalid HA virtual IPv4 address error message."""
    return (
        "high_availability_config.yml: virtual_ip_address "
        f"'{value}' is not a valid IPv4 address."
    )


def ha_vip_address_conflict_msg(vip: str, source: str) -> str:
    """Return an HA virtual-IP address collision error message."""
    return (
        f"high_availability_config.yml: virtual_ip_address '{vip}' conflicts "
        f"with an address defined by {source}."
    )


def ha_vip_dhcp_conflict_msg(vip: str, ranges: list[str]) -> str:
    """Return an HA virtual-IP DHCP-pool collision error message."""
    return (
        f"high_availability_config.yml: virtual_ip_address '{vip}' belongs "
        f"to DHCP pool(s): {', '.join(ranges)}."
    )


def ha_vip_external_pool_conflict_msg(vip: str, pool: str) -> str:
    """Return an HA virtual-IP external-pool collision error message."""
    return (
        f"high_availability_config.yml: virtual_ip_address '{vip}' belongs "
        f"to Kubernetes pod_external_ip_range '{pool}'."
    )


def ha_control_plane_network_unresolved_msg(addresses: list[str]) -> str:
    """Return an unresolved control-plane admin-subnet error message."""
    return (
        "high_availability_config.yml: Control-plane ADMIN_IP address(es) "
        "must belong to exactly one configured admin subnet: "
        f"{', '.join(addresses)}."
    )


def ha_control_plane_multiple_subnets_msg(networks: list[str]) -> str:
    """Return a split control-plane admin-subnet error message."""
    return (
        "high_availability_config.yml: All Kubernetes control-plane nodes "
        "must share one admin subnet for kube-vip and MetalLB L2 operation; "
        f"found {', '.join(networks)}."
    )


def ha_vip_control_plane_subnet_msg(vip: str, network: str) -> str:
    """Return an HA virtual-IP subnet-membership error message."""
    return (
        f"high_availability_config.yml: virtual_ip_address '{vip}' must be "
        f"a usable host address in the control-plane subnet {network}."
    )


def ha_external_pool_control_plane_subnet_msg(
    pool: str, network: str
) -> str:
    """Return a MetalLB pool/control-plane subnet error message."""
    return (
        "high_availability_config.yml: Kubernetes pod_external_ip_range "
        f"'{pool}' must be fully contained in the control-plane subnet "
        f"{network} for MetalLB L2 operation."
    )


def storage_required_msg(references: list[str]) -> str:
    """Return the conditionally required storage file error message."""
    return (
        "storage_config.yml is required because omnia_config.yml references "
        f"storage: {', '.join(references)}"
    )


def cluster_storage_name_required_msg(section: str) -> str:
    """Return the missing required cluster-storage reference message."""
    return (
        f"omnia_config.yml: '{section}' must define a non-empty "
        "nfs_storage_name because matching functional groups are selected "
        "in pxe_mapping_file.csv."
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


def security_ldap_connection_type_msg(value: str) -> str:
    """Return an unsupported LDAP transport message."""
    return (
        f"security_config.yml: ldap_connection_type '{value}' is invalid; "
        "supported values are TLS and SSL."
    )


def storage_unknown_prefix_msg(
    section: str, entry: str, prefix: str
) -> str:
    """Return an unmatched storage functional-group prefix message."""
    return (
        f"storage_config.yml: {section} entry '{entry}' has "
        f"functional_group_prefix '{prefix}', which does not match a "
        "supported, catalog, or mapped functional group."
    )


def storage_unknown_group_msg(
    section: str, entry: str, group: str, valid_groups: list[str]
) -> str:
    """Return a storage target absent from the PXE mapping."""
    return (
        f"storage_config.yml: {section} entry '{entry}' targets unknown "
        f"GROUP_NAME '{group}'; mapped groups are {valid_groups}."
    )


def storage_duplicate_mount_point_msg(
    target: str, mount_point: str, entries: list[str]
) -> str:
    """Return a duplicate storage destination message."""
    return (
        f"storage_config.yml: Mount point '{mount_point}' is duplicated for "
        f"functional group or group '{target}' in entries: "
        f"{', '.join(entries)}."
    )


def storage_swap_overlap_msg(
    prefix: str, entry: str, previous_entry: str
) -> str:
    """Return a duplicate swap target-prefix message."""
    return (
        f"storage_config.yml: Swap entry '{entry}' repeats "
        f"functional_group_prefix '{prefix}' already used by "
        f"'{previous_entry}'."
    )


def storage_swap_size_msg(
    entry: str, size: str, maxsize: str
) -> str:
    """Return a swap maximum smaller than its requested size."""
    return (
        f"storage_config.yml: Swap entry '{entry}' has maxsize "
        f"'{maxsize}' smaller than size '{size}'."
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
