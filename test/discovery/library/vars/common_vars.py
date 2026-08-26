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
ENV_OMNIA_PROJECT_NAME = "OMNIA_PROJECT_NAME"

# Domain config file (inside the domain input directory)
DISCOVERY_CONFIG_FILE = "discovery_config.yml"
NETWORK_SPEC_FILE = "network_spec.yml"

# Playbook entry point (relative to the domain source)
PLAYBOOK_ENTRY_POINT = "discovery.yml"
PLAYBOOK_WORKDIR = "src/discovery/playbooks"

# Valid playbook tags
PLAYBOOK_TAGS: List[str] = [
    "validate",
    "discover",
]

# =============================================================================
# Domain-specific paths
# =============================================================================
SHARED_PATH = "/opt/omnia/discovery"
INPUT_PATH_TEMPLATE = "/opt/omnia/discovery/input/{project}"
OUTPUT_PATH_TEMPLATE = "/opt/omnia/discovery/output/{project}"

# Credentials
CREDENTIALS_FILE_NAME = "omnia_config_credentials.yml"
CREDENTIALS_KEY_NAME = ".omnia_config_credentials_key"

# Output file patterns
PXE_MAPPING_PATTERN = "bmc_pxe_mapping_file*.csv"
PXE_MAPPING_SYMLINK = "bmc_pxe_mapping_file.csv"
DISCOVERY_REPORT_PATTERN = "bmc_discovery_report*.csv"

# =============================================================================
# Shell commands — all commands MUST be in this dict.
# Use .format() with named placeholders to fill in runtime values.
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
    "find_csv": "find {path} -name '{pattern}' -type f 2>/dev/null",

    # --- Ansible / Playbook ---
    "ansible_playbook": (
        "cd {workdir} && ansible-playbook {playbook}"
        " -e '{extra_vars}' -v 2>&1"
    ),

    # --- System ---
    "hostname_cmd": "hostname 2>/dev/null",
    "hostname_ip": "hostname -I 2>/dev/null",
    "rpm_check": "rpm -q {package} 2>/dev/null",
    "which_cmd": "which {binary} 2>/dev/null",

    # --- YAML validation ---
    "yaml_parse": (
        "python3 -c \"import yaml; yaml.safe_load(open('{path}'))\""
        " 2>&1"
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
