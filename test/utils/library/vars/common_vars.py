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
Utils Domain — Module-Specific Variables

Common vars (ssh_opts, config names, timeouts) live in the
``omnia_auto`` package and are set via ``omnia_auto.configure()``
in conftest.py.

Only module-specific constants remain here.
"""

import os
import re

# =============================================================================
# DIRECTORY PATHS
#============================================================================

# Module root: test/utils/ directory (where conftest.py lives)
MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))

# Parent of module root: test/
TEST_ROOT = os.path.dirname(MODULE_ROOT)

# Omnia monorepo root: omnia/
MONOREPO_ROOT = os.path.dirname(TEST_ROOT)

# src/ paths — used when dataset is empty (default: use src/ directly)
SRC_INPUT_DIR = os.path.join(
    MONOREPO_ROOT, "src", "utils", "input",
)

# =============================================================================
# DOMAIN IDENTITY
#============================================================================

# Domain name used for remote path resolution
DOMAIN_NAME = "utils"

# Environment variable names on the target host
ENV_OMNIA_DATA_PATH = "OMNIA_DATA_PATH"
ENV_OMNIA_PROJECT_NAME = "OMNIA_PROJECT_NAME"

# =============================================================================
# INPUT FILE NAMES
#============================================================================

# Log collector input file
COLLECT_PXE_FILE = "collect_pxe.yml"

# Install OS input files
INSTALL_OS_CONFIG_FILE = "install_os_config.yml"
INSTALL_OS_CREDENTIALS_FILE = "install_os_credentials.yml"

# =============================================================================
# PLAYBOOK CONFIGURATION (module-specific)
#============================================================================

# Playbook entry points (relative to workdir)
PLAYBOOK_COLLECT = "playbooks/collect.yml"
PLAYBOOK_INSTALL_OS = "playbooks/install_os.yml"
PLAYBOOK_WORKDIR = "src/utils"

# Valid playbook tags for collect.yml
COLLECT_PLAYBOOK_TAGS = [
    "setup",
    "prepare",
    "k8s",
    "slurm",
    "bundle",
]

# Valid playbook tags for install_os.yml
INSTALL_OS_TAGS = [
    "credentials",
    "build_iso",
    "deploy",
    "generate_ks",
]

# =============================================================================
# SHARED PATH DEFAULTS (runtime output on target host)
#============================================================================

SHARED_PATH = "/opt/omnia/utils"

# =============================================================================
# LOG COLLECTOR CONSTANTS
#============================================================================

# Output bundle naming pattern
LOG_BUNDLE_PATTERN = r"omnia_logs_\d{8}T\d{6}\.tar\.gz"

# Metadata file name
METADATA_FILE = "metadata.json"

# Functional groups for log collection
FUNCTIONAL_GROUPS = [
    "service_kube_control_plane_x86_64",
    "service_kube_node_x86_64",
    "slurm_control_node_x86_64",
    "slurm_node_x86_64",
    "slurm_node_aarch64",
    "login_node_x86_64",
    "login_compiler_node_aarch64",
]

# Install OS constants
INSTALL_OS_OUTPUT_DIR = "/opt/omnia/utils/output"
INSTALL_OS_STATUS_FILE = "install_os_status.yml"
CUSTOM_ISO_PATTERN = r".*-omnia\.iso"
KICKSTART_FILE = "kickstart.ks"

# =============================================================================
# CONFIG VALIDATION CONSTANTS
#============================================================================

# IPv4 address regex pattern
IPV4_PATTERN = re.compile(
    r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}'
    r'(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$'
)

# Required fields in test_config.yml
REQUIRED_CONFIG_FIELDS = [
    "project_name",
    "clone_path",
    "report_path",
    "report_name",
]

# Required files inside a dataset directory (when dataset is set)
REQUIRED_DATASET_FILES = [
    "input/collect_pxe.yml",
    "input/install_os_config.yml",
]

# Required files in src/ (when dataset is empty — default mode)
REQUIRED_SRC_FILES = [
    "collect_pxe.yml",
    "install_os_config.yml",
]

# =============================================================================
# CENTRALIZED SHELL COMMANDS
#============================================================================
# All shell commands used by verification functions.
# Use .format() with named placeholders to fill in runtime values.

CMDS = {
    # --- Files ---
    "file_exists": "test -f {path} && echo exists",
    "dir_exists": "test -d {path} && echo exists",
    "cat_file": "cat {path} 2>/dev/null",
    "file_stat": (
        "stat -c '%A %U:%G %s %n' {path} 2>/dev/null"
    ),
    "ls_dir": "ls -la {path} 2>/dev/null",
    "find_files": "find {path} -type f -name '{pattern}' 2>/dev/null",

    # --- Ansible / Playbook ---
    "ansible_playbook": (
        "cd {workdir} && ansible-playbook {playbook}"
        " --tags {tag} -v 2>&1"
    ),
    "ansible_playbook_inventory": (
        "cd {workdir} && ansible-playbook {playbook}"
        " -i {inventory} --tags {tag} -v 2>&1"
    ),

    # --- System ---
    "hostname_short": "hostname -s 2>/dev/null",
    "hostname_domain": "hostname -d 2>/dev/null",
    "hostname_fqdn": "hostname -f 2>/dev/null",
    "hostname_ip": "hostname -I 2>/dev/null",
    "rpm_check": "rpm -q {package} 2>/dev/null",
    "which_cmd": "which {binary} 2>/dev/null",

    # --- Connectivity / Precheck ---
    "echo_test": "echo connectivity_ok 2>/dev/null",
    "env_check": "echo ${env_var} 2>/dev/null",
    "source_env_file": (
        "test -f /etc/profile.d/omnia-env.sh && "
        "source /etc/profile.d/omnia-env.sh && "
        "echo ${env_var} 2>/dev/null"
    ),

    # --- SSH ---
    "ssh_test": "ssh -o BatchMode=yes -o ConnectTimeout=5 {user}@{host} echo ok 2>/dev/null",

    # --- Log Collector ---
    "tar_list": "tar -tzf {path} 2>/dev/null",
    "tar_extract_file": "tar -xzf {archive} -O {file} 2>/dev/null",
    "json_parse": "cat {path} | python3 -c \"import sys,json; d=json.load(sys.stdin); print(d.get('{key}', ''))\" 2>/dev/null",

    # --- Git ---
    "git_remote_url": "git -C {path} remote get-url origin 2>/dev/null",
    "git_branch": "git -C {path} branch --show-current 2>/dev/null",
    "git_log_last": "git -C {path} log -1 --oneline 2>/dev/null",

    # --- iDRAC / Redfish ---
    "curl_redfish": (
        "curl -sk -u {user}:{password} "
        "https://{host}/redfish/v1/Systems/System.Embedded.1 2>/dev/null"
    ),

    # --- Journal logs ---
    "journalctl_since": (
        "journalctl -u {service} --since '{since}' --no-pager 2>/dev/null"
    ),
}
