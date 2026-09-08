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
"""L2 semantic and cross-file validation for Orchestrator configuration."""

from __future__ import annotations

import csv
import ipaddress
import os
import re
from collections import Counter
from logging import Logger
from typing import Any

import yaml

from ..messages import orchestrator_messages as msg
from .network_spec_validator import is_valid_ipv4, network_from_config, record_error


REQUIRED_HEADERS = [
    "FUNCTIONAL_GROUP_NAME",
    "GROUP_NAME",
    "SERVICE_TAG",
    "PARENT_SERVICE_TAG",
    "HOSTNAME",
    "ADMIN_MAC",
    "ADMIN_IP",
    "BMC_MAC",
    "BMC_IP",
]


def _read_csv_rows(path: str) -> tuple[list[str], list[list[str]]]:
    """Read stripped CSV headers and rows from a normalized local path."""
    with open(path, "r", encoding="utf-8", newline="") as csv_file:
        reader = csv.reader(csv_file)
        header = [column.strip().upper() for column in next(reader, [])]
        rows = [[column.strip() for column in row] for row in reader]
    return header, rows


def _column_values(rows: list[list[str]], index: int) -> list[str]:
    """Return non-empty values from a possibly ragged CSV column."""
    return [row[index] for row in rows if index < len(row) and row[index]]


def _duplicates(values: list[str]) -> list[str]:
    """Return sorted values that occur more than once."""
    return sorted(value for value, count in Counter(values).items() if count > 1)


def _resolve_pxe_mapping_path(
    config_data: dict[str, Any], input_project_dir: str
) -> str:
    """Resolve a PXE mapping override or the project-default mapping path."""
    configured_path = config_data.get("pxe_mapping_file_path")
    candidate = configured_path or os.path.join(
        input_project_dir, "pxe_mapping_file.csv"
    )
    return os.path.realpath(candidate)


def _validate_language(
    config_data: dict[str, Any], errors: list[str], logger: Logger | None
) -> None:
    """Validate the supported provisioning language."""
    language = config_data.get("language", "")
    if not language:
        record_error(errors, logger, msg.LANGUAGE_REQUIRED_MSG)
    elif "en_US.UTF-8" not in language:
        record_error(errors, logger, msg.language_unsupported_msg(language))


def _validate_default_lease_time(
    config_data: dict[str, Any], errors: list[str], logger: Logger | None
) -> None:
    """Validate that the DHCP lease time is a positive integer."""
    lease_time = config_data.get("default_lease_time", "")
    try:
        if int(lease_time) <= 0:
            raise ValueError("non-positive lease time")
    except (TypeError, ValueError):
        record_error(errors, logger, msg.lease_time_invalid_msg(lease_time))


def _validate_kernel_version_override(
    config_data: dict[str, Any], errors: list[str], logger: Logger | None
) -> None:
    """Validate the optional kernel-version override format."""
    kernel_version = config_data.get("kernel_version_override", "")
    if kernel_version and not re.match(
        r"^[0-9]+\.[0-9]+\.[0-9]+-.+$", str(kernel_version)
    ):
        record_error(
            errors, logger, msg.kernel_version_format_msg(kernel_version)
        )


def _validate_s3_config(
    config_data: dict[str, Any], errors: list[str], logger: Logger | None
) -> None:
    """Preserve validation of legacy S3 provider and endpoint fields."""
    provider = config_data.get("s3_storage_provider", "minio")
    endpoint = config_data.get("s3_endpoint", "")
    if provider in ("powerscale", "external") and (
        not isinstance(endpoint, str) or not endpoint.strip()
    ):
        record_error(errors, logger, msg.s3_endpoint_required_msg(provider))
    if provider == "minio" and endpoint and logger:
        logger.warning(msg.s3_endpoint_ignored_msg())


def _validate_additional_cloud_init_config(
    config_data: dict[str, Any], errors: list[str], logger: Logger | None
) -> None:
    """Validate that a configured additional cloud-init file exists."""
    cloud_init_path = config_data.get("additional_cloud_init_config_file", "")
    if cloud_init_path and not os.path.isfile(os.path.realpath(cloud_init_path)):
        record_error(
            errors,
            logger,
            msg.cloud_init_file_missing_msg(str(cloud_init_path)),
        )


def _validate_pxe_mapping_file(
    config_data: dict[str, Any],
    input_project_dir: str,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate PXE mapping existence, columns, uniqueness, and ADMIN_IPs."""
    path = _resolve_pxe_mapping_path(config_data, input_project_dir)
    if not os.path.isfile(path):
        record_error(errors, logger, msg.pxe_mapping_not_found_msg(path))
        return

    try:
        header, rows = _read_csv_rows(path)
    except (csv.Error, OSError, UnicodeError) as exc:
        record_error(
            errors,
            logger,
            msg.pxe_mapping_read_failed_msg(path, str(exc)),
        )
        return

    missing = [column for column in REQUIRED_HEADERS if column not in header]
    if missing:
        record_error(
            errors,
            logger,
            msg.pxe_mapping_missing_columns_msg(path, missing),
        )
        return

    fields = {
        "SERVICE_TAG": _column_values(rows, header.index("SERVICE_TAG")),
        "HOSTNAME": _column_values(rows, header.index("HOSTNAME")),
        "ADMIN_IP": _column_values(rows, header.index("ADMIN_IP")),
    }
    for field, values in fields.items():
        duplicate_values = _duplicates(values)
        if duplicate_values:
            record_error(
                errors,
                logger,
                msg.pxe_mapping_duplicates_msg(field, duplicate_values),
            )

    for address in fields["ADMIN_IP"]:
        if not is_valid_ipv4(address):
            record_error(errors, logger, msg.pxe_mapping_invalid_ip_msg(address))


def _load_admin_networks(input_project_dir: str) -> list[ipaddress.IPv4Network]:
    """Load all valid primary and additional admin networks."""
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

    network_entries = network_data.get("Networks", [])
    if not isinstance(network_entries, list):
        return []
    for entry in network_entries:
        if not isinstance(entry, dict):
            continue
        admin_config = entry.get("admin_network")
        if not isinstance(admin_config, dict):
            continue
        networks = []
        primary_network = network_from_config(admin_config)
        if primary_network:
            networks.append(primary_network)
        additional_subnets = admin_config.get("additional_subnets", [])
        if isinstance(additional_subnets, list):
            networks.extend(
                network
                for subnet in additional_subnets
                if isinstance(subnet, dict)
                if (network := network_from_config(subnet)) is not None
            )
        return networks
    return []


def _validate_network_spec_cross(
    config_data: dict[str, Any],
    input_project_dir: str,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate mapping ADMIN_IP values against configured admin subnets."""
    path = _resolve_pxe_mapping_path(config_data, input_project_dir)
    if not os.path.isfile(path):
        return
    admin_networks = _load_admin_networks(input_project_dir)
    if not admin_networks:
        return
    try:
        header, rows = _read_csv_rows(path)
    except (csv.Error, OSError, UnicodeError):
        return
    if "ADMIN_IP" not in header:
        return

    for address in _column_values(rows, header.index("ADMIN_IP")):
        if not is_valid_ipv4(address):
            continue
        if not any(ipaddress.ip_address(address) in network for network in admin_networks):
            record_error(
                errors,
                logger,
                msg.mapping_ip_outside_subnets_msg(
                    address, [str(network) for network in admin_networks]
                ),
            )


def _referenced_storage_names(omnia_config: Any) -> set[str]:
    """Return storage names referenced by supported cluster definitions."""
    references: set[str] = set()
    if not isinstance(omnia_config, dict):
        return references
    for section in ("slurm_cluster", "service_k8s_cluster"):
        entries = omnia_config.get(section, [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for field in ("nfs_storage_name", "vast_storage_name"):
                value = entry.get(field)
                if isinstance(value, str) and value.strip():
                    references.add(value.strip())
    return references


def _load_omnia_config(input_project_dir: str) -> Any:
    """Load project-level Omnia configuration for storage references."""
    omnia_config_path = os.path.realpath(
        os.path.join(input_project_dir, "omnia_config.yml")
    )
    if not os.path.isfile(omnia_config_path):
        return None
    try:
        with open(omnia_config_path, "r", encoding="utf-8") as omnia_file:
            return yaml.safe_load(omnia_file)
    except (OSError, UnicodeError, yaml.YAMLError):
        return None


def validate_storage_references(
    input_project_dir: str,
    storage_data: Any,
    logger: Logger | None = None,
) -> list[str]:
    """Validate conditionally required storage and referenced mount names.

    Args:
        input_project_dir: Current project input directory.
        storage_data: Parsed ``storage_config.yml`` data, when available.
        logger: Optional validation logger.

    Returns:
        Storage-reference errors, or an empty list when valid or unused.
    """
    errors: list[str] = []
    storage_path = os.path.realpath(
        os.path.join(input_project_dir, "storage_config.yml")
    )
    references = _referenced_storage_names(_load_omnia_config(input_project_dir))
    if references and storage_data is None and not os.path.isfile(storage_path):
        record_error(errors, logger, msg.storage_required_msg(sorted(references)))
        return errors
    if not isinstance(storage_data, dict):
        return errors

    mounts = storage_data.get("mounts", [])
    if not isinstance(mounts, list):
        return errors
    mount_names = [
        mount["name"]
        for mount in mounts
        if isinstance(mount, dict) and isinstance(mount.get("name"), str)
    ]
    duplicate_names = _duplicates(mount_names)
    missing_names = sorted(references - set(mount_names))
    if duplicate_names:
        record_error(
            errors, logger, msg.duplicate_storage_names_msg(duplicate_names)
        )
    if missing_names:
        record_error(errors, logger, msg.missing_storage_names_msg(missing_names))
    return errors


def validate(
    config_data: dict[str, Any],
    input_project_dir: str,
    logger: Logger | None = None,
) -> list[str]:
    """Run all L2 Orchestrator configuration checks.

    Args:
        config_data: Parsed ``orchestrator_config.yml`` data.
        input_project_dir: Current project input directory used for defaults.
        logger: Optional validation logger.

    Returns:
        Validation error messages, or an empty list for valid input.
    """
    errors: list[str] = []
    _validate_language(config_data, errors, logger)
    _validate_default_lease_time(config_data, errors, logger)
    _validate_kernel_version_override(config_data, errors, logger)
    _validate_s3_config(config_data, errors, logger)
    _validate_additional_cloud_init_config(config_data, errors, logger)
    _validate_pxe_mapping_file(config_data, input_project_dir, errors, logger)
    _validate_network_spec_cross(config_data, input_project_dir, errors, logger)
    return errors
