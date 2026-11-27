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
Collect PXE configuration validator.

This module validates collect_pxe.yml for:
- IP address format validation for each functional group
- Valid functional group names

Functional group names follow Omnia's PXE-mapping naming convention, which
optionally inserts an OS name and version between the role and the
architecture (e.g. ``slurm_node_rhel_10_0_aarch64``), in addition to the
legacy bare form (``slurm_node_aarch64``). The OS name and version are not
fixed — new RHEL point releases, and other OS families, must keep validating
without code changes — so functional groups are matched by pattern instead of
a hardcoded set of exact strings. This mirrors the normalization regex used
by orchestrator's ``generate_functional_groups`` module.
"""
import ipaddress
import re
# Roles supported for log collection. "service_kube_control_plane_first"
# (the primary control-plane node) must be listed before
# "service_kube_control_plane" so the longer, more specific alternative is
# preferred.
FUNCTIONAL_GROUP_ROLES = (
    "service_kube_control_plane_first",
    "service_kube_control_plane",
    "service_kube_node",
    "slurm_control_node",
    "slurm_node",
    "login_node",
    "login_compiler_node",
)

SUPPORTED_ARCHITECTURES = ("x86_64", "aarch64")
SUPPORTED_OS_NAMES = ("rhel", "rocky", "ubuntu", "sles")

_ROLE_PATTERN = "|".join(FUNCTIONAL_GROUP_ROLES)
_ARCHITECTURE_PATTERN = "|".join(SUPPORTED_ARCHITECTURES)
_OS_NAME_PATTERN = "|".join(SUPPORTED_OS_NAMES)

# Optional "_<os>_<version segments>" suffix, e.g. "_rhel_10_0", inserted
# between the role and the architecture on versioned functional group names.
_OS_VERSION_SEGMENT = rf"(?:_(?:{_OS_NAME_PATTERN})(?:_[0-9]+)+)?"

FUNCTIONAL_GROUP_NAME_PATTERN = re.compile(
    rf"^(?:{_ROLE_PATTERN}){_OS_VERSION_SEGMENT}_(?:{_ARCHITECTURE_PATTERN})$"
)

FLEXIBLE_GROUP_NAME_PATTERN = re.compile(
    rf"^fg_(?P<label>[a-zA-Z0-9_-]+?){_OS_VERSION_SEGMENT}_(?:{_ARCHITECTURE_PATTERN})$"
)

# Representative legacy/base group names, used only for human-readable error
# messages (the actual validation is pattern-based; any OS/version variant of
# these is also accepted).
VALID_FUNCTIONAL_GROUPS = {
    f"{role}_{arch}"
    for role in FUNCTIONAL_GROUP_ROLES
    for arch in SUPPORTED_ARCHITECTURES
}


def extract_role_prefix(group_name):
    """Extract normalized role prefix from a functional group name.

    Returns:
    - Predefined role (e.g. slurm_node for slurm_node_rhel_10_0_aarch64)
    - Flexible role prefix (e.g. fg_webserver for fg_webserver_rhel_10_2_x86_64)
    """
    if not group_name:
        return ""
    if group_name.startswith("fg_"):
        match = FLEXIBLE_GROUP_NAME_PATTERN.match(group_name)
        if match:
            return f"fg_{match.group('label')}"
        if "_rhel_" in group_name:
            return group_name.split("_rhel_")[0]
        return group_name.rsplit("_", 1)[0]
    match = FUNCTIONAL_GROUP_NAME_PATTERN.match(group_name)
    if match:
        for role in FUNCTIONAL_GROUP_ROLES:
            if group_name.startswith(role):
                return role
    return group_name


def is_valid_functional_group(group_name):
    """Return True if group_name matches a supported role/OS-version/arch shape."""
    return bool(
        FUNCTIONAL_GROUP_NAME_PATTERN.match(group_name)
        or FLEXIBLE_GROUP_NAME_PATTERN.match(group_name)
    )


def _validate_ip_addresses(config_data, errors, logger=None):
    """
    Validate IP addresses in functional groups.

    Rules:
    - All IP addresses must be valid IPv4 format
    - Reserved IPs (127.0.0.1, 255.255.255.255) are not allowed
    """
    for group_name, ip_list in config_data.items():
        if not isinstance(ip_list, list):
            continue

        for ip_address in ip_list:
            if not isinstance(ip_address, str):
                error = f"collect_pxe_config: {group_name} contains non-string value: {ip_address}"
                errors.append(error)
                if logger:
                    logger.error(error)
                continue

            # Strict IPv4 address validation
            try:
                ipaddress.IPv4Address(ip_address.strip())
            except (ipaddress.AddressValueError, ValueError):
                error = (
                    f"collect_pxe_config: {group_name} contains invalid IP address: "
                    f"{ip_address}"
                )
                errors.append(error)
                if logger:
                    logger.error(error)
                continue

            # Check for reserved IPs
            reserved_ips = {"127.0.0.1", "255.255.255.255"}
            if ip_address.strip() in reserved_ips:
                error = (
                    f"collect_pxe_config: {group_name} contains reserved IP address: "
                    f"{ip_address}"
                )
                errors.append(error)
                if logger:
                    logger.error(error)


def _validate_functional_groups(config_data, errors, logger=None):
    """
    Validate functional group names.

    Rules:
    - All keys must be valid functional group names (predefined or flexible fg_*)
    """
    for group_name in config_data.keys():
        if not is_valid_functional_group(group_name):
            valid_groups = ", ".join(sorted(VALID_FUNCTIONAL_GROUPS))
            error = (
                f"collect_pxe_config: Invalid functional group '{group_name}'. "
                f"Expected <role>_<arch> (predefined) or fg_<label>_<os>_<version>_<arch> (flexible), "
                f"optionally with an OS/version segment before the architecture "
                f"(e.g. '{next(iter(sorted(VALID_FUNCTIONAL_GROUPS)))}' or "
                f"'slurm_node_rhel_10_0_aarch64' or 'fg_webserver_rhel_10_2_x86_64'). "
                f"Valid predefined roles: {valid_groups}. Flexible groups must start with 'fg_'."
            )
            errors.append(error)
            if logger:
                logger.error(error)


def validate(config_data, logger=None):
    """
    Run all L2 validation rules on collect_pxe.yml data.

    Args:
        config_data (dict): Parsed collect_pxe.yml content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    errors = []
    _validate_functional_groups(config_data, errors, logger)
    _validate_ip_addresses(config_data, errors, logger)
    return errors
