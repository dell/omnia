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
"""L2 semantic validation for ``omnia_config.yml``."""

from __future__ import annotations

import csv
import ipaddress
import os
import subprocess
from collections import Counter
from logging import Logger
from typing import Any

import yaml

from ..messages import orchestrator_messages as msg
from .network_spec_validator import record_error
from .pxe_mapping_validator import read_mapping, resolve_mapping_path


AddressRange = tuple[ipaddress.IPv4Address, ipaddress.IPv4Address]
StorageReference = tuple[str, str, str, str]
FileStatuses = dict[str, bool]
VAULT_HEADER = "$ANSIBLE_VAULT"


def _mark_file_status(
    file_statuses: FileStatuses | None, path: str, is_valid: bool
) -> None:
    """Record auxiliary input status, preserving any earlier failure."""
    if file_statuses is None:
        return
    normalized_path = os.path.realpath(path)
    file_statuses[normalized_path] = (
        file_statuses.get(normalized_path, True) and is_valid
    )


def load_project_yaml(input_project_dir: str, filename: str) -> Any:
    """Safely load one project YAML file, returning ``None`` on failure."""
    path = os.path.realpath(os.path.join(input_project_dir, filename))
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as yaml_file:
            return yaml.safe_load(yaml_file)
    except (OSError, UnicodeError, yaml.YAMLError):
        return None


def load_pxe_mapping_rows(input_project_dir: str) -> list[dict[str, str]]:
    """Load normalized PXE mapping rows using the current path contract."""
    orchestrator_data = load_project_yaml(
        input_project_dir, "orchestrator_config.yml"
    )
    configured_path = ""
    if isinstance(orchestrator_data, dict):
        configured_path = orchestrator_data.get("pxe_mapping_file_path", "")
    if not isinstance(configured_path, str):
        configured_path = ""
    mapping_path = resolve_mapping_path(
        {"pxe_mapping_file_path": configured_path}, input_project_dir
    )
    if not os.path.isfile(mapping_path):
        return []

    try:
        _, normalized_fields, numbered_rows = read_mapping(mapping_path)
        return [
            dict(zip(normalized_fields, values))
            for _, values in numbered_rows
            if len(values) == len(normalized_fields)
        ]
    except (csv.Error, OSError, UnicodeError):
        return []


def selected_workloads(rows: list[dict[str, str]]) -> set[str]:
    """Return current workload categories selected by PXE functional groups."""
    functional_groups = {
        row.get("FUNCTIONAL_GROUP_NAME", "") for row in rows
    }
    workloads: set[str] = set()
    if any(name.startswith("service_kube_") for name in functional_groups):
        workloads.add("kubernetes")
    if any(
        name.startswith(
            ("slurm_", "login_node_", "login_compiler_node_")
        )
        for name in functional_groups
    ):
        workloads.add("slurm")
    return workloads


def parse_ipv4_range_or_cidr(value: Any) -> AddressRange | None:
    """Parse an ordered IPv4 range or CIDR into inclusive endpoints."""
    if not isinstance(value, str):
        return None
    try:
        if "-" in value:
            start_text, end_text = value.split("-", 1)
            start = ipaddress.ip_address(start_text.strip())
            end = ipaddress.ip_address(end_text.strip())
            if not isinstance(start, ipaddress.IPv4Address):
                return None
            if not isinstance(end, ipaddress.IPv4Address) or start > end:
                return None
            return start, end
        network = ipaddress.ip_network(value.strip(), strict=False)
    except (TypeError, ValueError):
        return None
    if not isinstance(network, ipaddress.IPv4Network):
        return None
    return network.network_address, network.broadcast_address


def _strict_ipv4_network(value: Any) -> ipaddress.IPv4Network | None:
    """Return a canonical IPv4 network or ``None`` for an invalid CIDR."""
    try:
        network = ipaddress.ip_network(value, strict=True)
    except (TypeError, ValueError):
        return None
    return network if isinstance(network, ipaddress.IPv4Network) else None


def _ranges_overlap(first: AddressRange, second: AddressRange) -> bool:
    """Return whether two inclusive address ranges overlap."""
    return first[0] <= second[1] and second[0] <= first[1]


def _network_range(network: ipaddress.IPv4Network) -> AddressRange:
    """Return inclusive endpoints for an IPv4 network."""
    return network.network_address, network.broadcast_address


def _network_from_entry(entry: Any) -> ipaddress.IPv4Network | None:
    """Return an IPv4 network declared by a network-spec entry."""
    if not isinstance(entry, dict):
        return None
    try:
        network = ipaddress.ip_network(
            f"{entry.get('subnet', '')}/{entry.get('netmask_bits', '')}",
            strict=False,
        )
    except (TypeError, ValueError):
        return None
    return network if isinstance(network, ipaddress.IPv4Network) else None


def _network_context(
    input_project_dir: str,
) -> tuple[list[ipaddress.IPv4Network], list[AddressRange], dict[str, set[str]]]:
    """Load physical networks, DHCP pools, and fixed OIM addresses."""
    data = load_project_yaml(input_project_dir, "network_spec.yml")
    physical_networks: list[ipaddress.IPv4Network] = []
    dhcp_ranges: list[AddressRange] = []
    fixed_addresses: dict[str, set[str]] = {
        "primary_oim_admin_ip": set(),
        "primary_oim_bmc_ip": set(),
    }
    if not isinstance(data, dict) or not isinstance(data.get("Networks"), list):
        return physical_networks, dhcp_ranges, fixed_addresses

    for network_item in data["Networks"]:
        if not isinstance(network_item, dict):
            continue
        for network_type in ("admin_network", "ib_network"):
            network_entry = network_item.get(network_type)
            network = _network_from_entry(network_entry)
            if network and network not in physical_networks:
                physical_networks.append(network)

        admin_entry = network_item.get("admin_network")
        if not isinstance(admin_entry, dict):
            continue
        for field in fixed_addresses:
            value = admin_entry.get(field)
            try:
                address = ipaddress.ip_address(value)
            except (TypeError, ValueError):
                continue
            if isinstance(address, ipaddress.IPv4Address):
                fixed_addresses[field].add(str(address))

        primary_range = parse_ipv4_range_or_cidr(
            admin_entry.get("dynamic_range")
        )
        if primary_range:
            dhcp_ranges.append(primary_range)
        additional_subnets = admin_entry.get("additional_subnets", [])
        if not isinstance(additional_subnets, list):
            continue
        for additional in additional_subnets:
            network = _network_from_entry(additional)
            if network and network not in physical_networks:
                physical_networks.append(network)
            if isinstance(additional, dict):
                additional_range = parse_ipv4_range_or_cidr(
                    additional.get("dynamic_range")
                )
                if additional_range:
                    dhcp_ranges.append(additional_range)
    return physical_networks, dhcp_ranges, fixed_addresses


def _duplicate_cluster_names(
    config_data: dict[str, Any], errors: list[str], logger: Logger | None
) -> None:
    """Reject repeated cluster names within either cluster list."""
    for section in ("slurm_cluster", "service_k8s_cluster"):
        entries = config_data.get(section, [])
        if not isinstance(entries, list):
            continue
        names = [
            entry.get("cluster_name", "").strip()
            for entry in entries
            if isinstance(entry, dict)
            and isinstance(entry.get("cluster_name"), str)
            and entry.get("cluster_name", "").strip()
        ]
        duplicates = sorted(
            name for name, count in Counter(names).items() if count > 1
        )
        if duplicates:
            record_error(
                errors,
                logger,
                msg.omnia_duplicate_cluster_names_msg(section, duplicates),
            )


def _mapping_addresses(
    rows: list[dict[str, str]],
) -> dict[str, set[str]]:
    """Return valid mapped IPv4 addresses grouped by CSV field."""
    addresses: dict[str, set[str]] = {
        "ADMIN_IP": set(),
        "BMC_IP": set(),
        "IB_IP": set(),
    }
    for row in rows:
        for field in addresses:
            value = row.get(field, "")
            try:
                address = ipaddress.ip_address(value)
            except (TypeError, ValueError):
                continue
            if isinstance(address, ipaddress.IPv4Address):
                addresses[field].add(str(address))
    return addresses


def _validate_k8s_networks(
    clusters: list[dict[str, Any]],
    input_project_dir: str,
    mapping_rows: list[dict[str, str]],
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate K8s CIDRs, overlaps, and external-pool reservations."""
    physical_networks, dhcp_ranges, fixed_addresses = _network_context(
        input_project_dir
    )
    mapped_addresses = _mapping_addresses(mapping_rows)
    for cluster in clusters:
        cluster_name = str(cluster.get("cluster_name", ""))
        service_network = _strict_ipv4_network(
            cluster.get("k8s_service_addresses")
        )
        pod_network = _strict_ipv4_network(
            cluster.get("k8s_pod_network_cidr")
        )
        external_range = parse_ipv4_range_or_cidr(
            cluster.get("pod_external_ip_range")
        )
        parsed_ranges: dict[str, AddressRange] = {}
        for field, parsed in (
            ("k8s_service_addresses", service_network),
            ("k8s_pod_network_cidr", pod_network),
            ("pod_external_ip_range", external_range),
        ):
            if parsed is None:
                record_error(
                    errors,
                    logger,
                    msg.omnia_k8s_network_invalid_msg(cluster_name, field),
                )
            elif isinstance(parsed, ipaddress.IPv4Network):
                parsed_ranges[field] = _network_range(parsed)
            else:
                parsed_ranges[field] = parsed

        fields = list(parsed_ranges)
        for index, first_field in enumerate(fields):
            for second_field in fields[index + 1 :]:
                if _ranges_overlap(
                    parsed_ranges[first_field], parsed_ranges[second_field]
                ):
                    record_error(
                        errors,
                        logger,
                        msg.omnia_k8s_network_overlap_msg(
                            cluster_name, first_field, second_field
                        ),
                    )

        for field, network in (
            ("k8s_service_addresses", service_network),
            ("k8s_pod_network_cidr", pod_network),
        ):
            overlapping = sorted(
                str(physical)
                for physical in physical_networks
                if network and network.overlaps(physical)
            )
            if overlapping:
                record_error(
                    errors,
                    logger,
                    msg.omnia_k8s_physical_network_overlap_msg(
                        cluster_name, field, overlapping
                    ),
                )

        if not external_range:
            continue
        for field, addresses in fixed_addresses.items():
            conflicts = sorted(
                address
                for address in addresses
                if external_range[0]
                <= ipaddress.ip_address(address)
                <= external_range[1]
            )
            if conflicts:
                record_error(
                    errors,
                    logger,
                    msg.omnia_external_pool_address_conflict_msg(
                        cluster_name, field, conflicts
                    ),
                )
        for field, addresses in mapped_addresses.items():
            conflicts = sorted(
                address
                for address in addresses
                if external_range[0]
                <= ipaddress.ip_address(address)
                <= external_range[1]
            )
            if conflicts:
                record_error(
                    errors,
                    logger,
                    msg.omnia_external_pool_address_conflict_msg(
                        cluster_name, field, conflicts
                    ),
                )
        overlapping_dhcp = [
            f"{address_range[0]}-{address_range[1]}"
            for address_range in dhcp_ranges
            if _ranges_overlap(external_range, address_range)
        ]
        if overlapping_dhcp:
            record_error(
                errors,
                logger,
                msg.omnia_external_pool_dhcp_overlap_msg(
                    cluster_name, overlapping_dhcp
                ),
            )


def _storage_references(
    section: str, clusters: list[dict[str, Any]]
) -> tuple[list[StorageReference], bool]:
    """Build selected-workload storage references and missing-name state."""
    references: list[StorageReference] = []
    missing_nfs = False
    for cluster in clusters:
        cluster_name = str(cluster.get("cluster_name", ""))
        nfs_name = cluster.get("nfs_storage_name")
        if not isinstance(nfs_name, str) or not nfs_name.strip():
            if section == "slurm_cluster" or cluster.get("deployment") is True:
                missing_nfs = True
            continue
        nfs_name = nfs_name.strip()
        references.append(
            (section, cluster_name, "nfs_storage_name", nfs_name)
        )
        if section != "slurm_cluster":
            continue
        vast_name = cluster.get("vast_storage_name")
        effective_vast = (
            vast_name.strip()
            if isinstance(vast_name, str) and vast_name.strip()
            else nfs_name
        )
        if effective_vast != nfs_name:
            references.append(
                (section, cluster_name, "vast_storage_name", effective_vast)
            )
    return references, missing_nfs


def _validate_storage(
    section: str,
    clusters: list[dict[str, Any]],
    input_project_dir: str,
    errors: list[str],
    logger: Logger | None,
    file_statuses: FileStatuses | None,
    auxiliary_errors: list[str],
) -> None:
    """Validate selected-workload storage names and OIM mount requirements."""
    references, missing_nfs = _storage_references(section, clusters)
    if missing_nfs:
        record_error(
            errors, logger, msg.cluster_storage_name_required_msg(section)
        )
    if not references:
        return

    storage_path = os.path.realpath(
        os.path.join(input_project_dir, "storage_config.yml")
    )
    file_errors: list[str] = []
    storage_data = load_project_yaml(input_project_dir, "storage_config.yml")
    if not os.path.isfile(storage_path):
        _mark_file_status(file_statuses, storage_path, False)
        record_error(
            file_errors,
            logger,
            msg.storage_required_msg(
                sorted({reference[3] for reference in references})
            ),
        )
        errors.extend(file_errors)
        auxiliary_errors.extend(file_errors)
        return
    if not isinstance(storage_data, dict) or not isinstance(
        storage_data.get("mounts"), list
    ):
        _mark_file_status(file_statuses, storage_path, False)
        record_error(
            file_errors, logger, msg.omnia_storage_config_invalid_msg()
        )
        errors.extend(file_errors)
        auxiliary_errors.extend(file_errors)
        return

    mounts = storage_data["mounts"]
    for section_name, cluster_name, field, storage_name in references:
        matches = [
            mount
            for mount in mounts
            if isinstance(mount, dict) and mount.get("name") == storage_name
        ]
        if len(matches) != 1:
            record_error(
                file_errors,
                logger,
                msg.omnia_storage_reference_count_msg(
                    section_name,
                    cluster_name,
                    field,
                    storage_name,
                    len(matches),
                ),
            )
            continue
        if matches[0].get("mount_on_oim") is not True:
            record_error(
                file_errors,
                logger,
                msg.omnia_storage_mount_on_oim_msg(
                    section_name, cluster_name, field, storage_name
                ),
            )
    _mark_file_status(
        file_statuses, storage_path, not file_errors
    )
    errors.extend(file_errors)
    auxiliary_errors.extend(file_errors)


def _validate_hardware_defaults(
    clusters: list[dict[str, Any]],
    mapping_rows: list[dict[str, str]],
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate homogeneous-mode defaults against mapped Slurm compute groups."""
    compute_groups = {
        row.get("GROUP_NAME", "")
        for row in mapping_rows
        if row.get("FUNCTIONAL_GROUP_NAME", "").startswith("slurm_node_")
        and row.get("GROUP_NAME", "")
    }
    for cluster in clusters:
        defaults = cluster.get("node_hardware_defaults", {})
        if not isinstance(defaults, dict) or not defaults:
            continue
        cluster_name = str(cluster.get("cluster_name", ""))
        mode = cluster.get("node_discovery_mode", "heterogeneous")
        if mode != "homogeneous":
            record_error(
                errors,
                logger,
                msg.omnia_hardware_defaults_mode_msg(cluster_name, str(mode)),
            )
        unknown_groups = sorted(set(defaults) - compute_groups)
        if unknown_groups:
            record_error(
                errors,
                logger,
                msg.omnia_hardware_defaults_groups_msg(
                    cluster_name, unknown_groups
                ),
            )


def _load_slurm_helpers() -> tuple[Any, Any] | None:
    """Load canonical Slurm parsing and type-validation helpers."""
    try:
        # pylint: disable-next=import-outside-toplevel
        from ansible.module_utils.slurm.slurm_conf_utils import (
            parse_slurm_conf,
            validate_config_types,
        )
    except ImportError:
        try:
            # pylint: disable-next=import-outside-toplevel
            from slurm.slurm_conf_utils import (
                parse_slurm_conf,
                validate_config_types,
            )
        except ImportError:
            return None
    return parse_slurm_conf, validate_config_types


def _fallback_duplicate_keys(path: str) -> list[str]:
    """Conservatively detect duplicate scalar keys without the Slurm module."""
    repeatable_keys = {
        "BlockName",
        "DownNodes",
        "Feature",
        "NodeName",
        "NodeSet",
        "PartitionName",
        "SwitchName",
    }
    seen: set[str] = set()
    duplicates: set[str] = set()
    with open(path, "r", encoding="utf-8") as config_file:
        for raw_line in config_file:
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            first_item = line.split()[0]
            key, separator, _value = first_item.partition("=")
            if not separator:
                raise ValueError
            if key in seen and key not in repeatable_keys:
                duplicates.add(key)
            seen.add(key)
    return sorted(duplicates)


def _validate_slurm_config_sources(
    clusters: list[dict[str, Any]],
    errors: list[str],
    logger: Logger | None,
    file_statuses: FileStatuses | None,
    auxiliary_errors: list[str],
) -> None:
    """Validate custom Slurm paths, keys, value types, and duplicates."""
    helpers = _load_slurm_helpers()
    parser, type_validator = helpers if helpers else (None, None)
    file_errors: list[str] = []
    inline_errors: list[str] = []
    for cluster in clusters:
        cluster_name = str(cluster.get("cluster_name", ""))
        skip_merge = cluster.get("skip_merge") is True
        config_sources = cluster.get("config_sources", {})
        if not isinstance(config_sources, dict):
            continue
        for config_name, source in config_sources.items():
            source_errors: list[str] = []
            parsed_config: dict[str, Any] | None = None
            path: str | None = None
            if isinstance(source, str):
                path = os.path.realpath(source)
                if not os.path.isfile(path):
                    record_error(
                        source_errors,
                        logger,
                        msg.omnia_slurm_config_file_missing_msg(
                            cluster_name, str(config_name), source
                        ),
                    )
                else:
                    try:
                        if parser:
                            parsed_config, duplicate_keys = parser(
                                path, str(config_name), False
                            )
                            duplicate_keys = sorted(set(duplicate_keys))
                        else:
                            duplicate_keys = _fallback_duplicate_keys(path)
                    except (
                        OSError,
                        UnicodeError,
                        ValueError,
                        IndexError,
                        AttributeError,
                    ):
                        record_error(
                            source_errors,
                            logger,
                            msg.omnia_slurm_config_file_invalid_msg(
                                cluster_name, str(config_name), source
                            ),
                        )
                    else:
                        if duplicate_keys:
                            record_error(
                                source_errors,
                                logger,
                                msg.omnia_slurm_config_duplicate_keys_msg(
                                    cluster_name,
                                    str(config_name),
                                    source,
                                    duplicate_keys,
                                ),
                            )
            else:
                parsed_config = source

            if (
                parsed_config
                and type_validator is not None
                and (path is None or not skip_merge)
            ):
                validation_result = type_validator(
                    parsed_config, str(config_name), None
                )
                invalid_keys = sorted(
                    set(validation_result.get("invalid_keys", []))
                )
                if invalid_keys:
                    record_error(
                        source_errors,
                        logger,
                        msg.omnia_slurm_config_invalid_keys_msg(
                            cluster_name,
                            str(config_name),
                            invalid_keys,
                        ),
                    )
                type_errors = [
                    str(item.get("error_msg", item))
                    if isinstance(item, dict)
                    else str(item)
                    for item in validation_result.get("type_errors", [])
                ]
                if type_errors:
                    record_error(
                        source_errors,
                        logger,
                        msg.omnia_slurm_config_type_errors_msg(
                            cluster_name,
                            str(config_name),
                            type_errors,
                        ),
                    )

            if path is not None:
                _mark_file_status(file_statuses, path, not source_errors)
                file_errors.extend(source_errors)
            else:
                inline_errors.extend(source_errors)
    errors.extend(file_errors)
    errors.extend(inline_errors)
    auxiliary_errors.extend(file_errors)


def _read_yaml_file(path: str) -> tuple[Any, bool]:
    """Read YAML and report whether it is Ansible Vault encrypted."""
    with open(path, "r", encoding="utf-8") as yaml_file:
        first_line = yaml_file.readline()
        if first_line.strip().startswith(VAULT_HEADER):
            return None, True
        yaml_file.seek(0)
        return yaml.safe_load(yaml_file), False


def _read_vault_yaml(path: str, vault_key_path: str) -> Any:
    """Decrypt an Ansible Vault file read-only and parse its YAML in memory."""
    try:
        result = subprocess.run(
            [
                "ansible-vault",
                "view",
                path,
                "--vault-password-file",
                vault_key_path,
            ],
            check=False,
            capture_output=True,
            encoding="utf-8",
            timeout=30,
        )
    except (OSError, UnicodeError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        return yaml.safe_load(result.stdout)
    except yaml.YAMLError:
        return None


def _csi_issue(
    errors: list[str],
    logger: Logger | None,
    cluster_name: str,
    file_kind: str,
    path: str,
    issue: str,
) -> None:
    """Record a PowerScale CSI content-contract error."""
    record_error(
        errors,
        logger,
        msg.omnia_powerscale_csi_content_msg(
            cluster_name, file_kind, path, issue
        ),
    )


def _validate_powerscale_secret(
    cluster_name: str,
    path: str,
    input_project_dir: str,
    errors: list[str],
    logger: Logger | None,
    file_statuses: FileStatuses | None,
) -> None:
    """Validate the non-secret structure required by PowerScale secret.yaml."""
    try:
        data, encrypted = _read_yaml_file(path)
    except (OSError, UnicodeError, yaml.YAMLError):
        _csi_issue(
            errors, logger, cluster_name, "secret", path, "yaml_mapping"
        )
        return
    if encrypted:
        vault_key_path = os.path.realpath(
            os.path.join(input_project_dir, ".csi_powerscale_secret_vault")
        )
        if not os.path.isfile(vault_key_path):
            _mark_file_status(file_statuses, vault_key_path, False)
            _csi_issue(
                errors,
                logger,
                cluster_name,
                "secret",
                path,
                "vault_key",
            )
            return
        data = _read_vault_yaml(path, vault_key_path)
        if data is None:
            _csi_issue(
                errors,
                logger,
                cluster_name,
                "secret",
                path,
                "vault_content",
            )
            return
    if not isinstance(data, dict):
        _csi_issue(
            errors, logger, cluster_name, "secret", path, "yaml_mapping"
        )
        return
    clusters = data.get("isilonClusters")
    if not isinstance(clusters, list) or not clusters:
        _csi_issue(
            errors, logger, cluster_name, "secret", path, "isilon_clusters"
        )
        return

    default_count = 0
    for entry in clusters:
        if not isinstance(entry, dict):
            _csi_issue(
                errors, logger, cluster_name, "secret", path, "cluster_mapping"
            )
            continue
        for field in ("clusterName", "endpoint"):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                _csi_issue(
                    errors,
                    logger,
                    cluster_name,
                    "secret",
                    path,
                    f"required_{field}",
                )
        for field in ("username", "password"):
            if not isinstance(entry.get(field), str):
                _csi_issue(
                    errors,
                    logger,
                    cluster_name,
                    "secret",
                    path,
                    f"required_{field}",
                )
        is_default = entry.get("isDefault")
        if not isinstance(is_default, bool):
            _csi_issue(
                errors, logger, cluster_name, "secret", path, "is_default"
            )
        elif is_default:
            default_count += 1
        endpoint_port = entry.get("endpointPort")
        if endpoint_port is not None and (
            isinstance(endpoint_port, bool)
            or not isinstance(endpoint_port, int)
            or not 1 <= endpoint_port <= 65535
        ):
            _csi_issue(
                errors, logger, cluster_name, "secret", path, "endpoint_port"
            )
        skip_validation = entry.get("skipCertificateValidation")
        if skip_validation is not None and not isinstance(skip_validation, bool):
            _csi_issue(
                errors,
                logger,
                cluster_name,
                "secret",
                path,
                "secret_skip_certificate_validation",
            )
        isi_path = entry.get("isiPath")
        if isi_path is not None and (
            not isinstance(isi_path, str) or not isi_path.startswith("/")
        ):
            _csi_issue(
                errors, logger, cluster_name, "secret", path, "isi_path"
            )
        permissions = entry.get("isiVolumePathPermissions")
        if permissions is not None and (
            not isinstance(permissions, str)
            or len(permissions) not in (3, 4)
            or any(character not in "01234567" for character in permissions)
        ):
            _csi_issue(
                errors,
                logger,
                cluster_name,
                "secret",
                path,
                "isi_volume_permissions",
            )
    if default_count != 1:
        _csi_issue(
            errors, logger, cluster_name, "secret", path, "default_cluster"
        )


def _nested_value(data: Any, *keys: str) -> Any:
    """Safely obtain a value from nested mappings."""
    value = data
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _validate_powerscale_values(
    cluster_name: str,
    path: str,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate PowerScale values consumed by Omnia and the CSI chart."""
    try:
        data, encrypted = _read_yaml_file(path)
    except (OSError, UnicodeError, yaml.YAMLError):
        _csi_issue(
            errors, logger, cluster_name, "values", path, "yaml_mapping"
        )
        return
    if encrypted or not isinstance(data, dict):
        _csi_issue(
            errors, logger, cluster_name, "values", path, "yaml_mapping"
        )
        return

    controller_count = _nested_value(data, "controller", "controllerCount")
    checks = {
        "controller_count": isinstance(controller_count, int)
        and not isinstance(controller_count, bool)
        and controller_count == 1,
        "replication_disabled": _nested_value(
            data, "controller", "replication", "enabled"
        )
        is False,
        "resizer_boolean": isinstance(
            _nested_value(data, "controller", "resizer", "enabled"), bool
        ),
        "snapshot_enabled": _nested_value(
            data, "controller", "snapshot", "enabled"
        )
        is True,
        "endpoint_port": isinstance(data.get("endpointPort"), int)
        and not isinstance(data.get("endpointPort"), bool)
        and 1 <= data["endpointPort"] <= 65535,
        "skip_certificate_validation": isinstance(
            data.get("skipCertificateValidation"), bool
        ),
        "isi_auth_type": data.get("isiAuthType") in (0, 1)
        and not isinstance(data.get("isiAuthType"), bool),
        "isi_access_zone": isinstance(data.get("isiAccessZone"), str)
        and bool(data.get("isiAccessZone", "").strip()),
        "isi_path": isinstance(data.get("isiPath"), str)
        and data.get("isiPath", "").startswith("/"),
        "isi_volume_permissions": isinstance(
            data.get("isiVolumePathPermissions"), str
        )
        and len(data.get("isiVolumePathPermissions", "")) in (3, 4)
        and all(
            character in "01234567"
            for character in data.get("isiVolumePathPermissions", "")
        ),
    }
    for issue, is_valid in checks.items():
        if not is_valid:
            _csi_issue(
                errors, logger, cluster_name, "values", path, issue
            )


def _validate_powerscale_csi(
    clusters: list[dict[str, Any]],
    input_project_dir: str,
    errors: list[str],
    logger: Logger | None,
    file_statuses: FileStatuses | None,
    auxiliary_errors: list[str],
) -> None:
    """Validate CSI activation and the configured input files."""
    for cluster in clusters:
        if cluster.get("enable_powerscale_csi") is not True:
            continue
        cluster_name = str(cluster.get("cluster_name", ""))
        if cluster.get("deployment") is not True:
            record_error(
                errors,
                logger,
                msg.omnia_powerscale_csi_not_deployed_msg(cluster_name),
            )
            continue
        configured_files = (
            (
                "secret",
                cluster.get("csi_powerscale_driver_secret_file_path"),
            ),
            (
                "values",
                cluster.get("csi_powerscale_driver_values_file_path"),
            ),
        )
        for file_kind, configured_path in configured_files:
            file_errors: list[str] = []
            path = (
                os.path.realpath(configured_path)
                if isinstance(configured_path, str) and configured_path
                else ""
            )
            if not path or not os.path.isfile(path):
                if path:
                    _mark_file_status(file_statuses, path, False)
                record_error(
                    file_errors,
                    logger,
                    msg.omnia_powerscale_csi_file_missing_msg(
                        cluster_name, file_kind, str(configured_path or "")
                    ),
                )
                errors.extend(file_errors)
                auxiliary_errors.extend(file_errors)
                continue
            if file_kind == "secret":
                _validate_powerscale_secret(
                    cluster_name,
                    path,
                    input_project_dir,
                    file_errors,
                    logger,
                    file_statuses,
                )
            else:
                _validate_powerscale_values(
                    cluster_name, path, file_errors, logger
                )
            _mark_file_status(
                file_statuses, path, not file_errors
            )
            errors.extend(file_errors)
            auxiliary_errors.extend(file_errors)


def _validate_kubernetes(
    config_data: dict[str, Any],
    input_project_dir: str,
    mapping_rows: list[dict[str, str]],
    errors: list[str],
    logger: Logger | None,
    file_statuses: FileStatuses | None,
    auxiliary_errors: list[str],
) -> None:
    """Run Kubernetes checks when its functional groups are selected."""
    clusters = config_data.get("service_k8s_cluster")
    if not isinstance(clusters, list) or not clusters:
        record_error(
            errors,
            logger,
            msg.omnia_selected_section_required_msg("service_k8s_cluster"),
        )
        return
    valid_clusters = [cluster for cluster in clusters if isinstance(cluster, dict)]
    deployed_clusters = [
        cluster
        for cluster in valid_clusters
        if cluster.get("deployment") is True
    ]
    deployment_count = sum(
        cluster.get("deployment") is True for cluster in valid_clusters
    )
    if deployment_count != 1:
        record_error(
            errors,
            logger,
            msg.omnia_k8s_deployment_count_msg(deployment_count),
        )
    _validate_k8s_networks(
        deployed_clusters, input_project_dir, mapping_rows, errors, logger
    )
    _validate_storage(
        "service_k8s_cluster",
        deployed_clusters,
        input_project_dir,
        errors,
        logger,
        file_statuses,
        auxiliary_errors,
    )
    _validate_powerscale_csi(
        valid_clusters,
        input_project_dir,
        errors,
        logger,
        file_statuses,
        auxiliary_errors,
    )


def _validate_slurm(
    config_data: dict[str, Any],
    input_project_dir: str,
    mapping_rows: list[dict[str, str]],
    errors: list[str],
    logger: Logger | None,
    file_statuses: FileStatuses | None,
    auxiliary_errors: list[str],
) -> None:
    """Run Slurm checks when Slurm or login groups are selected."""
    clusters = config_data.get("slurm_cluster")
    if not isinstance(clusters, list) or not clusters:
        record_error(
            errors,
            logger,
            msg.omnia_selected_section_required_msg("slurm_cluster"),
        )
        return
    valid_clusters = [cluster for cluster in clusters if isinstance(cluster, dict)]
    _validate_storage(
        "slurm_cluster",
        valid_clusters,
        input_project_dir,
        errors,
        logger,
        file_statuses,
        auxiliary_errors,
    )
    _validate_hardware_defaults(
        valid_clusters, mapping_rows, errors, logger
    )
    _validate_slurm_config_sources(
        valid_clusters,
        errors,
        logger,
        file_statuses,
        auxiliary_errors,
    )


def validate(
    config_data: Any,
    input_project_dir: str,
    logger: Logger | None = None,
    file_statuses: FileStatuses | None = None,
    auxiliary_errors: list[str] | None = None,
) -> list[str]:
    """Run current, PXE-applicable L2 validation for ``omnia_config.yml``."""
    errors: list[str] = []
    if not isinstance(config_data, dict) or not config_data:
        record_error(errors, logger, msg.OMNIA_CONFIG_EMPTY_MSG)
        return errors

    mapping_rows = load_pxe_mapping_rows(input_project_dir)
    workloads = selected_workloads(mapping_rows)
    collected_auxiliary_errors = (
        auxiliary_errors if auxiliary_errors is not None else []
    )
    _duplicate_cluster_names(config_data, errors, logger)
    if "kubernetes" in workloads:
        _validate_kubernetes(
            config_data,
            input_project_dir,
            mapping_rows,
            errors,
            logger,
            file_statuses,
            collected_auxiliary_errors,
        )
    if "slurm" in workloads:
        _validate_slurm(
            config_data,
            input_project_dir,
            mapping_rows,
            errors,
            logger,
            file_statuses,
            collected_auxiliary_errors,
        )
    return errors
