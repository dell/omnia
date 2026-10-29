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
Discovery — Module-Specific Variables

Common vars (ssh_opts, config names, timeouts) live in the
``omnia_auto`` package and are set via ``omnia_auto.configure()``
in conftest.py.

Only module-specific constants remain here.
"""

import os
import shlex
from typing import Dict, List

# Module root: test/<domain>/ directory (where conftest.py lives)
MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))

# From vars/ -> library/ -> test/ -> repo root
REPO_ROOT = os.path.dirname(MODULE_ROOT)

# Domain name used for remote path resolution
DOMAIN_NAME = "discovery"

# Environment variable names on the target host
ENV_OMNIA_DATA_PATH = "OMNIA_DATA_PATH"
ENV_DISCOVERY_DATA_PATH = "DISCOVERY_DATA_PATH"
ENV_OMNIA_PROJECT_NAME = "OMNIA_PROJECT_NAME"

# Domain config file (inside the domain input directory)
DISCOVERY_CONFIG_FILE = "discovery_config.yml"
NETWORK_SPEC_FILE = "network_spec.yml"

# Playbook entry point (relative to the domain source)
PLAYBOOK_ENTRY_POINT = "discovery.yml"
PLAYBOOK_WORKDIR = "src/discovery/playbooks"

# Valid playbook tags
PLAYBOOK_TAGS: List[str] = [
    "precheck",
    "validate",
    "credentials",
    "prepare",
    "execute",
    "cleanup",
]

# =============================================================================
# Domain-specific paths
# =============================================================================
# src/ paths — used when dataset is empty (default: use src/ directly)
SRC_INPUT_DIR = os.path.join(
    REPO_ROOT, "src", "discovery", "input",
)

# Shared path — derived from DISCOVERY_DATA_PATH env var when available;
# falls back to OMNIA_DATA_PATH/discovery, then /opt/omnia/discovery
SHARED_PATH = (
    os.environ.get(ENV_DISCOVERY_DATA_PATH)
    or os.path.join(
        os.environ.get(ENV_OMNIA_DATA_PATH, "/opt/omnia"),
        DOMAIN_NAME,
    )
).rstrip("/")

# Credentials
CREDENTIALS_FILE_NAME = "discovery_credentials.yml"
CREDENTIALS_KEY_NAME = ".discovery_credentials_key"

# Default functional group for devices without valid OME static groups
DEFAULT_FUNCTIONAL_GROUP = "slurm_node_rhel_10_0_aarch64"

# Output file patterns
PXE_MAPPING_PATTERN = "bmc_pxe_mapping_file*.csv"
PXE_MAPPING_SYMLINK = "bmc_pxe_mapping_file.csv"
DISCOVERY_REPORT_PATTERN = "bmc_discovery_report*.csv"

# =============================================================================
# Supported functional groups (Omnia 2.3)
# =============================================================================
# Supported OS types in functional group names
# Only RHEL is supported
SUPPORTED_OS_TYPES: List[str] = [
    "rhel",
]

# Supported architectures in functional group names
SUPPORTED_ARCHITECTURES: List[str] = [
    "x86_64",
    "aarch64",
]

# Dynamic functional group pattern (Omnia 2.3):
# <any_prefix>_rhel_<major>_<minor>_<arch>
#
# This is the MANDATORY format for all functional groups in Omnia 2.3.
# - The prefix can be ANY string (e.g., slurm_node, os, sujal, custom_group)
# - The OS MUST be "rhel"
# - The OS version (major_minor) is REQUIRED
# - The architecture (x86_64 or aarch64) is REQUIRED
#
# Valid examples:
#   slurm_control_node_rhel_10_2_x86_64   ✅
#   slurm_node_rhel_10_2_x86_64           ✅
#   os_rhel_10_2_x86_64                   ✅
#   sujal_rhel_10_0_x86_64                ✅  (custom prefix allowed)
#   my_custom_group_rhel_9_4_aarch64      ✅  (any prefix allowed)
#   login_node_rhel_10_0_x86_64           ✅
#
# Invalid examples:
#   slurm_node_rocky_9_4_aarch64          ❌ (only rhel supported)
#   slurm_node_ubuntu_22_04_x86_64        ❌ (only rhel supported)
#   slurm_node_x86_64                     ❌ (missing _rhel_<version>_)
#   slurm_node                            ❌ (missing _rhel_<version>_<arch>)
#
# Pattern regex: ^.+_rhel_\d+_\d+_(x86_64|aarch64)$
import re
FUNCTIONAL_GROUP_PATTERN = re.compile(
    r'^(.+)_rhel_(\d+)_(\d+)_(x86_64|aarch64)$'
)

# Combined list for backward compatibility (empty - all groups must be dynamic now)
SUPPORTED_FUNCTIONAL_GROUPS: List[str] = []


def is_supported_functional_group(group_name: str) -> bool:
    """Check if a functional group name is supported.

    In Omnia 2.3, ALL functional groups MUST follow the pattern:
        <any_prefix>_rhel_<major>_<minor>_<arch>

    The prefix can be ANY string. The mandatory part is:
        _rhel_<major>_<minor>_(x86_64|aarch64)

    Valid examples:
        slurm_control_node_rhel_10_2_x86_64   ✅
        slurm_node_rhel_10_2_x86_64           ✅
        os_rhel_10_2_x86_64                   ✅
        sujal_rhel_10_0_x86_64                ✅
        my_custom_group_rhel_9_4_aarch64      ✅

    Invalid examples:
        slurm_node_rocky_9_4_aarch64          ❌ (only rhel supported)
        slurm_node_ubuntu_22_04_x86_64        ❌ (only rhel supported)
        slurm_node_x86_64                     ❌ (missing _rhel_<version>_)

    Args:
        group_name: Functional group name to validate.

    Returns:
        True if the group is supported, False otherwise.
    """
    if not group_name:
        return False

    # Pattern: <any_prefix>_rhel_<major>_<minor>_<arch>
    if FUNCTIONAL_GROUP_PATTERN.match(group_name):
        return True

    return False


def parse_functional_group(group_name: str) -> Dict[str, str]:
    """Parse a functional group name into its components.

    Args:
        group_name: Functional group name to parse.

    Returns:
        Dict with keys: prefix, os_type, os_major, os_minor, arch, is_valid.
        Returns dict with is_valid=False if not a valid group.
    """
    result = {
        "prefix": "",
        "os_type": "",
        "os_major": "",
        "os_minor": "",
        "arch": "",
        "is_valid": False,
    }

    if not group_name:
        return result

    # Check pattern: <any_prefix>_rhel_<major>_<minor>_<arch>
    match = FUNCTIONAL_GROUP_PATTERN.match(group_name)
    if match:
        result["prefix"] = match.group(1)
        result["os_type"] = "rhel"
        result["os_major"] = match.group(2)
        result["os_minor"] = match.group(3)
        result["arch"] = match.group(4)
        result["is_valid"] = True

    return result

# Required columns for PXE mapping CSV (Orchestrator contract)
ORCHESTRATOR_REQUIRED_COLUMNS: List[str] = [
    "FUNCTIONAL_GROUP_NAME",
    "SERVICE_TAG",
    "HOSTNAME",
    "ADMIN_MAC",
    "ADMIN_IP",
    "BMC_IP",
    "GROUP_NAME",
]

# Optional columns that Orchestrator may use
ORCHESTRATOR_OPTIONAL_COLUMNS: List[str] = [
    "IB_IPV4",
    "IB_IPV6",
    "IB_NIC_NAME",
    "PARENT_SERVICE_TAG",
    "MODEL",
    "ARCHITECTURE",
]

# OME API configuration
OME_API_TIMEOUT: int = 30
OME_SESSION_ENDPOINT: str = "/api/SessionService/Sessions"
OME_GROUPS_ENDPOINT: str = "/api/GroupService/Groups"
OME_GROUP_DEVICES_ENDPOINT: str = "/api/GroupService/Groups({group_id})/Devices"

# =============================================================================
# Shell commands — all commands MUST be in this dict.
# Fill in runtime values with build_cmd(), which shell-quotes every value.
# Placeholders must NOT be wrapped in quotes inside the templates.
# =============================================================================
CMDS: Dict[str, str] = {
    # --- Files ---
    "file_exists": "test -f {path} && echo exists",
    "dir_exists": "test -d {path} && echo exists",
    "cat_file": "cat {path} 2>/dev/null",
    "file_stat": (
        "stat -c '%A %U:%G %s %n' {path} 2>/dev/null"
    ),
    "ls_files": "ls -1 {path} 2>/dev/null",
    "find_csv": "find {path} -name {pattern} -type f 2>/dev/null",

    # --- Ansible / Playbook ---
    "ansible_playbook": (
        "cd {workdir} && ansible-playbook {playbook}"
        " -e {extra_vars} -v 2>&1"
    ),

    # --- System ---
    "hostname_cmd": "hostname 2>/dev/null",
    "hostname_ip": "hostname -I 2>/dev/null",
    "rpm_check": "rpm -q {package} 2>/dev/null",
    "which_cmd": "which {binary} 2>/dev/null",

    # --- YAML validation ---
    "yaml_parse": (
        "python3 -c \"import sys, yaml; yaml.safe_load(open(sys.argv[1]))\""
        " {path} 2>&1"
    ),

    # --- CSV validation ---
    "csv_header": "head -1 {path} 2>/dev/null",
    "csv_line_count": "wc -l < {path} 2>/dev/null",

    # --- Network ---
    "ping_check": "ping -c 1 -W 2 {host} 2>/dev/null",
    "curl_check": (
        "curl -sk --connect-timeout 5 https://{host}:{port} 2>/dev/null"
    ),

    # --- Symlink ---
    "readlink": "readlink -f {path} 2>/dev/null",

    # --- Git ---
    "git_remote_url": "git -C {path} remote get-url origin 2>/dev/null",
    "git_branch": "git -C {path} branch --show-current 2>/dev/null",
}


def build_cmd(name: str, **values: object) -> str:
    """Build a shell command from CMDS with every value shell-quoted.

    Args:
        name: Key in CMDS.
        **values: Placeholder values; each is converted with shlex.quote().

    Returns:
        The command string, safe against shell metacharacters in values.

    Raises:
        ValueError: If name is not a key in CMDS.
    """
    if name not in CMDS:
        raise ValueError(f"Unknown command template: {name}")
    return CMDS[name].format(
        **{key: shlex.quote(str(val)) for key, val in values.items()}
    )
