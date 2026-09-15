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
"""L2 validation for the Orchestrator PXE mapping contract."""

from __future__ import annotations

import csv
import ipaddress
import json
import os
import re
from collections import Counter
from logging import Logger
from typing import Any

import yaml

from ..messages import orchestrator_messages as msg
from .network_spec_validator import is_valid_ipv4, network_from_config, record_error

CANONICAL_HEADERS = (
    "FUNCTIONAL_GROUP_NAME",
    "GROUP_NAME",
    "SERVICE_TAG",
    "PARENT_SERVICE_TAG",
    "HOSTNAME",
    "ADMIN_MAC",
    "ADMIN_IP",
    "BMC_MAC",
    "BMC_IP",
    "IB_NIC_NAME",
    "IB_IP",
)
REQUIRED_VALUE_FIELDS = (
    "FUNCTIONAL_GROUP_NAME",
    "GROUP_NAME",
    "HOSTNAME",
    "ADMIN_MAC",
    "ADMIN_IP",
)

MAC_PATTERN = re.compile(
    r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"
    r"|^(?:[0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}$"
)
HOSTNAME_PATTERN = re.compile(
    r"^[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)
GROUP_PATTERN = re.compile(
    r"^(?:grp(?:[0-9]|[1-9][0-9]|100)|"
    r"[Ss][Uu][A-Za-z]?(?:0*[1-9][0-9]?|100))$"
)
FUNCTIONAL_GROUP_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
TAG_PATTERN = re.compile(r"^[A-Za-z0-9]+$")
IB_NIC_NAME_PATTERN = re.compile(
    r"^(?:(?:InfiniBand\.PCIe\.Slot\.|InfiniBand\.Slot\.|"
    r"NIC\.InfiniBand\.)[0-9A-Fa-f]+-[0-9]+|"
    r"InfiniBand\.Single-[0-9]+)$"
)
ARCHITECTURE_PATTERN = re.compile(r"_(x86_64|aarch64)$")
OS_VERSION_SUFFIX_PATTERN = re.compile(
    r"_(?P<os>rhel|rocky|ubuntu|sles)(?P<version>(?:_[0-9]+)*)$"
)
DNS_HOSTNAME_PATTERN = re.compile(
    r"^nid(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2})$"
)
CATALOG_MANAGED_PREFIXES = (
    "service_kube_",
    "slurm_",
    "login_node_",
    "login_compiler_node_",
    "os_",
)


def resolve_mapping_path(
    config_data: dict[str, Any], input_project_dir: str
) -> str:
    """Resolve the configured PXE mapping path or its project default."""
    configured_path = config_data.get("pxe_mapping_file_path")
    candidate = configured_path or os.path.join(
        input_project_dir, "pxe_mapping_file.csv"
    )
    return os.path.realpath(candidate)


def read_mapping(
    path: str,
) -> tuple[list[str], list[str], list[tuple[int, list[str]]]]:
    """Read canonical headers and data rows, ignoring blanks and comments."""
    with open(path, "r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.reader(csv_file, strict=True)
        numbered_rows = enumerate(reader, start=1)
        raw_header = []
        for _row_number, candidate in numbered_rows:
            if (
                candidate
                and any(column.strip() for column in candidate)
                and not candidate[0].lstrip().startswith("#")
            ):
                raw_header = candidate
                break

        header = [column.strip().upper() for column in raw_header]
        rows = []
        for row_number, raw_row in numbered_rows:
            row = [column.strip() for column in raw_row]
            if not row or not any(row) or row[0].startswith("#"):
                continue
            rows.append((row_number, row))
    return raw_header, header, rows


def _duplicates(values: list[str]) -> list[str]:
    """Return sorted, non-empty values that occur more than once."""
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def _mapping_rows(
    header: list[str],
    rows: list[tuple[int, list[str]]],
    path: str,
    errors: list[str],
    logger: Logger | None,
) -> list[tuple[int, dict[str, str]]]:
    """Reject ragged rows and return rows addressable by normalized header."""
    mapped_rows = []
    for row_number, row in rows:
        if len(row) != len(header):
            record_error(
                errors,
                logger,
                msg.pxe_mapping_row_width_msg(
                    path, row_number, len(row), len(header)
                ),
            )
            continue
        mapped_rows.append((row_number, dict(zip(header, row))))
    return mapped_rows


def _validate_unique_values(
    rows: list[tuple[int, dict[str, str]]],
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate mapping identities and network addresses that must be unique."""
    for field in (
        "SERVICE_TAG",
        "HOSTNAME",
        "ADMIN_MAC",
        "ADMIN_IP",
        "IB_IP",
    ):
        values = [row.get(field, "") for _, row in rows]
        if field == "ADMIN_MAC":
            values = [value.lower().replace("-", ":") for value in values]
        duplicate_values = _duplicates(values)
        if duplicate_values:
            record_error(
                errors,
                logger,
                msg.pxe_mapping_duplicates_msg(field, duplicate_values),
            )


def _validate_required_values(
    row_number: int,
    row: dict[str, str],
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate fields required to identify and provision a mapped node."""
    for field in REQUIRED_VALUE_FIELDS:
        if not row.get(field, ""):
            record_error(
                errors,
                logger,
                msg.pxe_mapping_required_cell_msg(field, row_number),
            )


def _validate_optional_tags(
    row_number: int,
    row: dict[str, str],
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate non-empty service tags without requiring either tag."""
    for field in ("SERVICE_TAG", "PARENT_SERVICE_TAG"):
        value = row.get(field, "")
        if value and not TAG_PATTERN.fullmatch(value):
            record_error(
                errors,
                logger,
                msg.pxe_mapping_invalid_tag_msg(field, value, row_number),
            )


def _validate_addresses(
    row_number: int,
    row: dict[str, str],
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate required/optional PXE mapping MAC and IPv4 addresses."""
    for field in ("ADMIN_MAC", "BMC_MAC"):
        value = row.get(field, "")
        if value and not MAC_PATTERN.fullmatch(value):
            record_error(
                errors,
                logger,
                msg.pxe_mapping_invalid_mac_msg(field, value, row_number),
            )

    for field in ("ADMIN_IP", "BMC_IP", "IB_IP"):
        value = row.get(field, "")
        if value and not is_valid_ipv4(value):
            record_error(
                errors,
                logger,
                msg.pxe_mapping_invalid_ip_field_msg(
                    field, value, row_number
                ),
            )


def _validate_names(
    row_number: int,
    row: dict[str, str],
    dns_enabled: bool,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate host, logical-group, and functional-group naming contracts."""
    hostname = row.get("HOSTNAME", "")
    if hostname and not HOSTNAME_PATTERN.fullmatch(hostname):
        record_error(
            errors,
            logger,
            msg.pxe_mapping_invalid_hostname_msg(hostname, row_number),
        )
    elif dns_enabled and hostname and not DNS_HOSTNAME_PATTERN.fullmatch(hostname):
        record_error(
            errors,
            logger,
            msg.pxe_mapping_dns_hostname_msg(hostname, row_number),
        )

    group_name = row.get("GROUP_NAME", "")
    if group_name and not GROUP_PATTERN.fullmatch(group_name):
        record_error(
            errors,
            logger,
            msg.pxe_mapping_invalid_group_msg(group_name, row_number),
        )

    functional_group = row.get("FUNCTIONAL_GROUP_NAME", "")
    if functional_group and not FUNCTIONAL_GROUP_PATTERN.fullmatch(
        functional_group
    ):
        record_error(
            errors,
            logger,
            msg.pxe_mapping_invalid_functional_group_msg(
                functional_group, row_number
            ),
        )
    elif functional_group.lower().startswith("baseos_"):
        record_error(
            errors,
            logger,
            msg.pxe_mapping_unsupported_functional_group_msg(
                functional_group, row_number
            ),
        )
    elif functional_group and not ARCHITECTURE_PATTERN.search(functional_group):
        record_error(
            errors,
            logger,
            msg.pxe_mapping_functional_group_architecture_msg(
                functional_group, row_number
            ),
        )


def _validate_ib_pair(
    row_number: int,
    row: dict[str, str],
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Require the optional InfiniBand NIC name and IP as a pair."""
    if bool(row.get("IB_NIC_NAME", "")) != bool(row.get("IB_IP", "")):
        record_error(errors, logger, msg.pxe_mapping_ib_pair_msg(row_number))


def _validate_ib_nic_name(
    row_number: int,
    row: dict[str, str],
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate the InfiniBand device formats supported by cloud-init."""
    nic_name = row.get("IB_NIC_NAME", "")
    if nic_name and not IB_NIC_NAME_PATTERN.fullmatch(nic_name):
        record_error(
            errors,
            logger,
            msg.pxe_mapping_invalid_ib_nic_name_msg(nic_name, row_number),
        )


def _validate_group_assignments(
    rows: list[tuple[int, dict[str, str]]],
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Reject mixed logical groups except the supported service/Slurm pair."""
    group_assignments: dict[str, set[str]] = {}
    for _, row in rows:
        group_name = row.get("GROUP_NAME", "")
        functional_group = row.get("FUNCTIONAL_GROUP_NAME", "")
        if group_name and functional_group:
            group_assignments.setdefault(group_name, set()).add(
                functional_group
            )

    for group_name, functional_groups in sorted(group_assignments.items()):
        if len(functional_groups) <= 1:
            continue

        identities = [
            _functional_group_identity(functional_group)
            for functional_group in functional_groups
        ]
        normalized_roles = {
            identity[0] for identity in identities if identity is not None
        }
        supported_slurm_topology = all(
            identity is not None for identity in identities
        ) and normalized_roles == {"service_kube_node", "slurm_node"}
        if supported_slurm_topology:
            continue

        record_error(
            errors,
            logger,
            msg.pxe_mapping_conflicting_group_msg(
                group_name, sorted(functional_groups)
            ),
        )


def _functional_group_architecture(functional_group: str) -> str | None:
    """Return a supported architecture suffix from a functional-group name."""
    match = ARCHITECTURE_PATTERN.search(functional_group)
    return match.group(1) if match else None


def _functional_group_identity(
    functional_group: str,
) -> tuple[str, str | None, str] | None:
    """Return normalized role, optional OS/version, and architecture."""
    architecture = _functional_group_architecture(functional_group)
    if architecture is None:
        return None

    role = functional_group[: -(len(architecture) + 1)]
    os_version_match = OS_VERSION_SUFFIX_PATTERN.search(role)
    os_version = None
    if os_version_match:
        os_version = os_version_match.group(0).removeprefix("_")
        role = role[: os_version_match.start()]
    return role, os_version, architecture


def _validate_slurm_compiler_architecture(
    rows: list[tuple[int, dict[str, str]]],
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Ensure login compiler architectures can serve mapped Slurm workers."""
    slurm_architectures = {
        architecture
        for _, row in rows
        if row.get("FUNCTIONAL_GROUP_NAME", "").startswith("slurm_node_")
        if (
            architecture := _functional_group_architecture(
                row.get("FUNCTIONAL_GROUP_NAME", "")
            )
        )
    }
    compiler_architectures = {
        architecture
        for _, row in rows
        if row.get("FUNCTIONAL_GROUP_NAME", "").startswith(
            "login_compiler_node_"
        )
        if (
            architecture := _functional_group_architecture(
                row.get("FUNCTIONAL_GROUP_NAME", "")
            )
        )
    }
    incompatible = compiler_architectures - slurm_architectures
    if slurm_architectures and compiler_architectures and incompatible:
        record_error(
            errors,
            logger,
            msg.pxe_mapping_architecture_mismatch_msg(
                sorted(slurm_architectures), sorted(compiler_architectures)
            ),
        )


def _resolve_catalog_path(
    config_data: dict[str, Any], input_project_dir: str
) -> str:
    """Resolve the active catalog path using the production precedence."""
    del input_project_dir
    configured_path = config_data.get("catalog_file_path")
    environment_path = os.getenv("CATALOG_FILE_PATH", "")
    omnia_data_path = os.getenv("OMNIA_DATA_PATH", "") or "/opt/omnia"
    candidate = configured_path or environment_path or os.path.join(
        omnia_data_path, "catalog", "catalog_rhel.json"
    )
    return os.path.realpath(candidate)


def _load_catalog_functional_groups(
    catalog_path: str,
) -> tuple[set[str], str | None]:
    """Return functional-layer names and any catalog read error."""
    if not os.path.isfile(catalog_path):
        return set(), "file does not exist"
    try:
        with open(catalog_path, "r", encoding="utf-8") as catalog_file:
            data = json.load(catalog_file)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return set(), str(exc)

    if not isinstance(data, dict):
        return set(), "root must be a JSON object"
    catalog = data.get("catalog")
    if not isinstance(catalog, dict):
        return set(), "catalog must be a JSON object"
    layers = catalog.get("functionallayer")
    if not isinstance(layers, list):
        return set(), "catalog.functionallayer must be an array"
    functional_groups = {
        layer["name"].strip()
        for layer in layers
        if isinstance(layer, dict)
        and isinstance(layer.get("name"), str)
        and layer["name"].strip()
    }
    if not functional_groups:
        return set(), "catalog.functionallayer has no named entries"
    return functional_groups, None


def _catalog_matches(
    functional_group: str, catalog_functional_groups: set[str]
) -> bool:
    """Match role/architecture and any explicit mapping OS/version."""
    mapping_identity = _functional_group_identity(functional_group)
    if mapping_identity is None:
        return False

    mapping_role, mapping_os_version, mapping_architecture = mapping_identity
    for catalog_group in catalog_functional_groups:
        catalog_identity = _functional_group_identity(catalog_group)
        if catalog_identity is None:
            continue
        catalog_role, catalog_os_version, catalog_architecture = (
            catalog_identity
        )
        if (
            mapping_role != catalog_role
            or mapping_architecture != catalog_architecture
        ):
            continue
        if (
            mapping_os_version is None
            or mapping_os_version == catalog_os_version
        ):
            return True
    return False


def _validate_catalog_functional_groups(
    rows: list[tuple[int, dict[str, str]]],
    config_data: dict[str, Any],
    input_project_dir: str,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate mapping groups against the active data-driven catalog."""
    catalog_path = _resolve_catalog_path(config_data, input_project_dir)
    catalog_functional_groups, catalog_error = (
        _load_catalog_functional_groups(catalog_path)
    )
    if catalog_error:
        return
    if not catalog_functional_groups:
        return
    for row_number, row in rows:
        functional_group = row.get("FUNCTIONAL_GROUP_NAME", "")
        is_catalog_managed = functional_group.lower().startswith(
            CATALOG_MANAGED_PREFIXES
        )
        if is_catalog_managed and not _catalog_matches(
            functional_group, catalog_functional_groups
        ):
            record_error(
                errors,
                logger,
                msg.pxe_mapping_unknown_catalog_group_msg(
                    functional_group, row_number, catalog_path
                ),
            )


def _load_admin_networks(
    input_project_dir: str,
) -> list[ipaddress.IPv4Network]:
    """Load every primary and additional admin subnet from network_spec.yml."""
    network_spec_path = os.path.realpath(
        os.path.join(input_project_dir, "network_spec.yml")
    )
    if not os.path.isfile(network_spec_path):
        return []
    try:
        with open(network_spec_path, "r", encoding="utf-8") as network_file:
            network_data = yaml.safe_load(network_file)
    except (OSError, UnicodeError, yaml.YAMLError):
        return []
    if not isinstance(network_data, dict):
        return []

    admin_networks = []
    network_entries = network_data.get("Networks", [])
    if not isinstance(network_entries, list):
        return admin_networks
    for entry in network_entries:
        if not isinstance(entry, dict):
            continue
        admin_config = entry.get("admin_network")
        if not isinstance(admin_config, dict):
            continue
        primary_network = network_from_config(admin_config)
        if primary_network:
            admin_networks.append(primary_network)
        additional_subnets = admin_config.get("additional_subnets", [])
        if not isinstance(additional_subnets, list):
            continue
        for subnet in additional_subnets:
            if not isinstance(subnet, dict):
                continue
            additional_network = network_from_config(subnet)
            if additional_network:
                admin_networks.append(additional_network)
    return admin_networks


def _validate_admin_subnet_membership(
    rows: list[tuple[int, dict[str, str]]],
    input_project_dir: str,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Require every valid mapped ADMIN_IP to belong to an admin subnet."""
    admin_networks = _load_admin_networks(input_project_dir)
    if not admin_networks:
        return
    for _, row in rows:
        address = row.get("ADMIN_IP", "")
        if not is_valid_ipv4(address):
            continue
        parsed_address = ipaddress.ip_address(address)
        if not any(parsed_address in network for network in admin_networks):
            record_error(
                errors,
                logger,
                msg.mapping_ip_outside_subnets_msg(
                    address, [str(network) for network in admin_networks]
                ),
            )


def validate(
    config_data: dict[str, Any],
    input_project_dir: str,
    logger: Logger | None = None,
) -> list[str]:
    """Validate the resolved PXE mapping file and its cross-file contracts."""
    errors: list[str] = []
    path = resolve_mapping_path(config_data, input_project_dir)
    if not os.path.isfile(path):
        record_error(errors, logger, msg.pxe_mapping_not_found_msg(path))
        return errors

    try:
        raw_header, header, raw_rows = read_mapping(path)
    except (csv.Error, OSError, UnicodeError) as exc:
        record_error(
            errors,
            logger,
            msg.pxe_mapping_read_failed_msg(path, str(exc)),
        )
        return errors

    if not header:
        record_error(errors, logger, msg.pxe_mapping_empty_msg(path))
        return errors

    if raw_header != list(CANONICAL_HEADERS):
        record_error(
            errors,
            logger,
            msg.pxe_mapping_header_contract_msg(
                path, raw_header, list(CANONICAL_HEADERS)
            ),
        )
        return errors

    if not raw_rows:
        record_error(errors, logger, msg.pxe_mapping_empty_msg(path))
        return errors

    rows = _mapping_rows(header, raw_rows, path, errors, logger)
    for row_number, row in rows:
        _validate_required_values(row_number, row, errors, logger)
        _validate_optional_tags(row_number, row, errors, logger)
        _validate_addresses(row_number, row, errors, logger)
        _validate_names(
            row_number,
            row,
            config_data.get("dns_enabled") is True,
            errors,
            logger,
        )
        _validate_ib_pair(row_number, row, errors, logger)
        _validate_ib_nic_name(row_number, row, errors, logger)

    _validate_unique_values(rows, errors, logger)
    _validate_group_assignments(rows, errors, logger)
    _validate_slurm_compiler_architecture(rows, errors, logger)
    _validate_catalog_functional_groups(
        rows, config_data, input_project_dir, errors, logger
    )
    _validate_admin_subnet_membership(
        rows, input_project_dir, errors, logger
    )
    return errors
