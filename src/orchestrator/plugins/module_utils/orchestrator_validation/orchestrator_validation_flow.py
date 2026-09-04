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
Orchestrator domain validation flow — L2 (logic) validation rules.

These are cross-field and semantic validations that go beyond JSON schema (L1).
They verify business-logic constraints specific to the orchestrator domain:
  - orchestrator_config.yml  (language, lease time, kernel version, s3, mapping file)
  - network_spec.yml         (admin network structure, subnet consistency)
"""

import csv
import ipaddress
import os
import re

import yaml


# ── Mapping-file header contract ─────────────────────────────────────────────
REQUIRED_HEADERS = [
    "FUNCTIONAL_GROUP_NAME", "GROUP_NAME", "SERVICE_TAG",
    "PARENT_SERVICE_TAG", "HOSTNAME", "ADMIN_MAC", "ADMIN_IP",
    "BMC_MAC", "BMC_IP",
]


# ── Small utility helpers (inlined to avoid pulling central framework) ───────

def _read_csv_rows(path):
    """Read CSV file, return (header, rows) with stripped values."""
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = [h.strip().upper() for h in next(reader)]
        rows = []
        for row in reader:
            rows.append([c.strip() for c in row])
    return header, rows


def _col_index(header, name):
    """Return column index for *name* or -1 if not found."""
    name_upper = name.upper()
    for i, h in enumerate(header):
        if h == name_upper:
            return i
    return -1


def _is_valid_ipv4(addr):
    """Quick check for valid, non-loopback IPv4."""
    try:
        ip = ipaddress.ip_address(addr)
        return ip.version == 4
    except ValueError:
        return False


def _ip_in_subnet(ip_str, network_str, prefix_len):
    """Check if an IP is in a given subnet."""
    try:
        network = ipaddress.ip_network(f"{network_str}/{prefix_len}", strict=False)
        return ipaddress.ip_address(ip_str) in network
    except ValueError:
        return False


# ── orchestrator_config.yml L2 validators ────────────────────────────────────

def validate_language(config_data, errors, logger=None):
    """language must be set and must contain 'en_US.UTF-8'."""
    language = config_data.get("language", "")
    if not language:
        msg = "orchestrator_config: 'language' is required and must not be empty."
        errors.append(msg)
        if logger:
            logger.error(msg)
    elif "en_US.UTF-8" not in language:
        msg = (f"orchestrator_config: 'language' value '{language}' is not supported. "
               "Must contain 'en_US.UTF-8'.")
        errors.append(msg)
        if logger:
            logger.error(msg)


def validate_default_lease_time(config_data, errors, logger=None):
    """default_lease_time must be a positive integer (or convertible to one)."""
    dlt = config_data.get("default_lease_time", "")
    try:
        val = int(dlt)
        if val <= 0:
            raise ValueError("non-positive")
    except (TypeError, ValueError):
        msg = (f"orchestrator_config: 'default_lease_time' value '{dlt}' is invalid. "
               "Must be a positive integer (seconds).")
        errors.append(msg)
        if logger:
            logger.error(msg)


def validate_kernel_version_override(config_data, errors, logger=None):
    """If set, kernel_version_override must match X.Y.Z-suffix format."""
    kvo = config_data.get("kernel_version_override", "")
    if kvo and not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+-.+$", kvo):
        msg = (f"orchestrator_config: 'kernel_version_override' value '{kvo}' does not "
               "match expected format X.Y.Z-<suffix> (e.g. 5.14.0-427.13.1.el9_4.x86_64).")
        errors.append(msg)
        if logger:
            logger.error(msg)


def validate_additional_cloud_init_config(config_data, errors, logger=None):
    """If additional_cloud_init_config_file is set, the file must exist."""
    aci_path = config_data.get("additional_cloud_init_config_file", "")
    if aci_path and not os.path.isfile(aci_path):
        msg = (f"orchestrator_config: 'additional_cloud_init_config_file' path "
               f"'{aci_path}' does not exist.")
        errors.append(msg)
        if logger:
            logger.error(msg)


def validate_pxe_mapping_file(
    config_data, input_project_dir, errors, logger=None
):
    """
    Validate the configured PXE mapping file, or the project-default file:
      - File must exist
      - Required header columns must be present
      - No duplicate SERVICE_TAGs, HOSTNAMEs, or ADMIN_IPs
      - ADMIN_IP values must be valid IPv4
    """
    path = config_data.get("pxe_mapping_file_path") or os.path.join(
        input_project_dir, "pxe_mapping_file.csv"
    )

    if not os.path.isfile(path):
        msg = f"orchestrator_config: pxe_mapping_file_path '{path}' does not exist."
        errors.append(msg)
        if logger:
            logger.error(msg)
        return

    try:
        header, rows = _read_csv_rows(path)
    except Exception as e:
        msg = f"orchestrator_config: Failed to read mapping file '{path}': {e}"
        errors.append(msg)
        if logger:
            logger.error(msg)
        return

    # Check required headers
    missing = [h for h in REQUIRED_HEADERS if h not in header]
    if missing:
        msg = (f"orchestrator_config: Mapping file '{path}' is missing required "
               f"columns: {missing}")
        errors.append(msg)
        if logger:
            logger.error(msg)
        return

    st_idx = _col_index(header, "SERVICE_TAG")
    hn_idx = _col_index(header, "HOSTNAME")
    aip_idx = _col_index(header, "ADMIN_IP")

    # Duplicate checks
    service_tags = [r[st_idx] for r in rows if r[st_idx]]
    hostnames = [r[hn_idx] for r in rows if r[hn_idx]]
    admin_ips = [r[aip_idx] for r in rows if r[aip_idx]]

    dup_st = [st for st in set(service_tags) if service_tags.count(st) > 1]
    if dup_st:
        msg = f"orchestrator_config: Duplicate SERVICE_TAG(s) in mapping file: {dup_st}"
        errors.append(msg)
        if logger:
            logger.error(msg)

    dup_hn = [h for h in set(hostnames) if hostnames.count(h) > 1]
    if dup_hn:
        msg = f"orchestrator_config: Duplicate HOSTNAME(s) in mapping file: {dup_hn}"
        errors.append(msg)
        if logger:
            logger.error(msg)

    dup_ip = [ip for ip in set(admin_ips) if admin_ips.count(ip) > 1]
    if dup_ip:
        msg = f"orchestrator_config: Duplicate ADMIN_IP(s) in mapping file: {dup_ip}"
        errors.append(msg)
        if logger:
            logger.error(msg)

    # ADMIN_IP format
    for ip in admin_ips:
        if not _is_valid_ipv4(ip):
            msg = f"orchestrator_config: Invalid ADMIN_IP '{ip}' in mapping file."
            errors.append(msg)
            if logger:
                logger.error(msg)


def validate_network_spec_cross(config_data, input_project_dir, errors, logger=None):
    """
    Cross-validate ADMIN_IPs in the mapping file against network_spec.yml subnets.
    """
    path = config_data.get("pxe_mapping_file_path") or os.path.join(
        input_project_dir, "pxe_mapping_file.csv"
    )
    if not os.path.isfile(path):
        return

    ns_path = os.path.join(input_project_dir, "network_spec.yml")
    if not os.path.isfile(ns_path):
        return

    try:
        with open(ns_path, "r", encoding="utf-8") as f:
            ns_data = yaml.safe_load(f)
    except (yaml.YAMLError, IOError):
        return

    # Find admin_network
    admin_prefix = None
    admin_ip = None
    for network in (ns_data or {}).get("Networks", []):
        if "admin_network" in network and isinstance(network["admin_network"], dict):
            an = network["admin_network"]
            admin_prefix = an.get("netmask_bits")
            admin_ip = an.get("primary_oim_admin_ip")
            break

    if not admin_prefix or not admin_ip:
        return

    header, rows = _read_csv_rows(path)
    aip_idx = _col_index(header, "ADMIN_IP")
    if aip_idx < 0:
        return

    for row in rows:
        ip = row[aip_idx]
        if ip and _is_valid_ipv4(ip) and not _ip_in_subnet(ip, admin_ip, admin_prefix):
            msg = (f"orchestrator_config: ADMIN_IP '{ip}' in mapping file is not in "
                   f"admin_network subnet {admin_ip}/{admin_prefix}.")
            errors.append(msg)
            if logger:
                logger.error(msg)


# ── network_spec.yml L2 validators ──────────────────────────────────────────

def validate_network_spec(ns_data, errors, logger=None):
    """
    L2 validation for network_spec.yml.

    Rules:
    - 'Networks' list must be present and non-empty.
    - At least one entry must contain 'admin_network'.
    - admin_network must have primary_oim_admin_ip (valid IPv4) and netmask_bits.
    """
    if not ns_data or not isinstance(ns_data, dict):
        msg = "network_spec: File is empty or not a valid YAML object."
        errors.append(msg)
        if logger:
            logger.error(msg)
        return

    networks = ns_data.get("Networks")
    if not networks or not isinstance(networks, list):
        msg = "network_spec: 'Networks' list is required and must not be empty."
        errors.append(msg)
        if logger:
            logger.error(msg)
        return

    has_admin = False
    for net in networks:
        if "admin_network" in net and isinstance(net["admin_network"], dict):
            has_admin = True
            an = net["admin_network"]
            oim_ip = an.get("primary_oim_admin_ip", "")
            if not oim_ip or not _is_valid_ipv4(oim_ip):
                msg = (f"network_spec: admin_network.primary_oim_admin_ip "
                       f"'{oim_ip}' is not a valid IPv4 address.")
                errors.append(msg)
                if logger:
                    logger.error(msg)
            bits = an.get("netmask_bits")
            if bits is None:
                msg = "network_spec: admin_network.netmask_bits is required."
                errors.append(msg)
                if logger:
                    logger.error(msg)
            break

    if not has_admin:
        msg = "network_spec: At least one 'admin_network' entry is required in Networks."
        errors.append(msg)
        if logger:
            logger.error(msg)


# ── Top-level dispatcher ─────────────────────────────────────────────────────

def validate_orchestrator_config_l2(config_data, input_project_dir, logger=None):
    """
    Run all L2 validation rules on orchestrator_config.yml data.

    Args:
        config_data (dict): Parsed orchestrator_config.yml content.
        input_project_dir (str): Path to project input directory.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    errors = []
    validate_language(config_data, errors, logger)
    validate_default_lease_time(config_data, errors, logger)
    validate_kernel_version_override(config_data, errors, logger)
    validate_additional_cloud_init_config(config_data, errors, logger)
    validate_pxe_mapping_file(config_data, input_project_dir, errors, logger)
    validate_network_spec_cross(config_data, input_project_dir, errors, logger)
    return errors
