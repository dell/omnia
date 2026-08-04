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
Omnia Main — Module-Specific Variables

Constants, paths, and centralized shell commands for the omnia.sh and
omnia-cli FVT automation.

Common vars (ssh_opts, config names, timeouts) live in the
``omnia_auto`` package and are set via ``omnia_auto.configure()``
in conftest.py.

Only module-specific constants remain here.
"""

import os
from typing import Dict, List

# =============================================================================
# DIRECTORY PATHS
# =============================================================================

# Module root: test/main/ directory (where conftest.py lives)
MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))

# Repository root: omnia-bsm/
REPO_ROOT = os.path.dirname(MODULE_ROOT)

# =============================================================================
# DOMAIN IDENTITY
# =============================================================================

DOMAIN_NAME = "main"

# Omnia script relative path (from clone_path)
OMNIA_SH_PATH = "src/main/omnia.sh"
OMNIA_ENV_PATH = "src/main/omnia.env"
OMNIA_CLI_PATH = "src/main/omnia-cli"

# =============================================================================
# SYSTEM PATHS (runtime on target host)
# =============================================================================

# System-wide environment file (installed by omnia.sh -s)
SYSTEM_ENV_DIR = "/etc/omnia"
SYSTEM_ENV_FILE = "/etc/omnia/omnia.env"
PROFILE_DROP_IN = "/etc/profile.d/omnia-env.sh"

# Default data path (may be overridden by env)
DEFAULT_DATA_PATH = "/opt/omnia"
DEFAULT_VENV_PATH = "/opt/omnia/venv"
DEFAULT_PROJECT_NAME = "project_default"

# Base directories created by omnia.sh --setup-venv
BASE_DIRS: List[str] = [
    "{data_path}",
    "{data_path}/log",
    "{data_path}/input",
    "{data_path}/.data",
]

# =============================================================================
# KNOWN DOMAINS
# =============================================================================

KNOWN_DOMAINS: List[str] = [
    "build_stream",
    "discovery",
    "image_build_manager",
    "orchestrator",
    "repo_manager",
    "telemetry",
    "utils",
]

# Domains that have domain-init.sh scripts
DOMAINS_WITH_INIT: List[str] = [
    "image_build_manager",
    "repo_manager",
]

# =============================================================================
# ENVIRONMENT VARIABLES
# =============================================================================

# Required env vars (must be set before running omnia.sh -s)
REQUIRED_ENV_VARS: List[str] = [
    "SYSTEM_ADMIN_NIC_IPV4",
]

# Optional env vars with defaults
OPTIONAL_ENV_VARS: Dict[str, str] = {
    "OMNIA_DATA_PATH": "/opt/omnia",
    "OMNIA_PROJECT_NAME": "project_default",
    "OMNIA_VENV_PATH": "/opt/omnia/venv",
    "SYSTEM_HOSTNAME": "oim",
    "SYSTEM_DOMAIN_NAME": "omnia.cluster",
}

# =============================================================================
# CLI COMMANDS AND OPTIONS
# =============================================================================

VALID_CLI_COMMANDS: List[str] = [
    "--setup-venv", "-s",
    "--init", "-i",
    "--run", "-r",
    "--validate",
    "--help", "-h",
]

VALID_CLI_OPTIONS: List[str] = [
    "--skip-init",
    "--tags", "-t",
]

# =============================================================================
# CENTRALIZED SHELL COMMANDS
# =============================================================================
# All shell commands used by verification functions.
# Use .format() with named placeholders to fill in runtime values.

CMDS: Dict[str, str] = {
    # --- omnia.sh execution ---
    "omnia_sh_help": (
        "cd {clone_path} && bash {omnia_sh} --help 2>&1"
    ),
    "omnia_sh_no_args": (
        "cd {clone_path} && bash {omnia_sh} 2>&1"
    ),
    "omnia_sh_setup_venv": (
        "cd {clone_path} && bash {omnia_sh}"
        " --setup-venv --skip-init 2>&1"
    ),
    "omnia_sh_setup_full": (
        "cd {clone_path} && bash {omnia_sh}"
        " --setup-venv 2>&1"
    ),
    "omnia_sh_init": (
        "cd {clone_path} && bash {omnia_sh} --init 2>&1"
    ),
    "omnia_sh_run_invalid": (
        "cd {clone_path} && bash {omnia_sh}"
        " --run {domain} 2>&1"
    ),
    "omnia_sh_run_no_domain": (
        "cd {clone_path} && bash {omnia_sh} --run 2>&1"
    ),
    "omnia_sh_validate_no_domain": (
        "cd {clone_path} && bash {omnia_sh}"
        " --validate 2>&1"
    ),
    "omnia_sh_unknown_option": (
        "cd {clone_path} && bash {omnia_sh}"
        " --bogus 2>&1"
    ),
    # --- Files ---
    "file_exists": "test -f {path} && echo exists",
    "dir_exists": "test -d {path} && echo exists",
    "cat_file": "cat {path} 2>/dev/null",
    "file_stat": (
        "stat -c '%A %U:%G %s %n' {path} 2>/dev/null"
    ),
    # --- Environment ---
    "env_var_check": "echo ${{{var_name}}}",
    "source_and_check": (
        "set -a && . {env_file} && set +a"
        " && echo ${{{var_name}}}"
    ),
    "source_profile_and_check": (
        ". {profile_file} && echo ${{{var_name}}}"
    ),
    # --- Venv ---
    "venv_python_version": (
        "{venv_path}/bin/python --version 2>&1"
    ),
    "venv_ansible_version": (
        "{venv_path}/bin/ansible --version 2>&1"
    ),
    "venv_pip_list": (
        "{venv_path}/bin/pip list --format=columns 2>&1"
    ),
    "venv_galaxy_list": (
        "{venv_path}/bin/ansible-galaxy collection list 2>&1"
    ),
    # --- Domain init ---
    "domain_log_dir_exists": (
        "test -d /var/log/omnia/{domain} && echo exists"
    ),
    "domain_input_dir_exists": (
        "test -d {data_path}/{domain}/input/{project}"
        " && echo exists"
    ),
    "domain_input_file_count": (
        "find {data_path}/{domain}/input/{project}"
        " -type f 2>/dev/null | wc -l"
    ),
    # --- System ---
    "hostname_cmd": "hostname 2>/dev/null",
    "which_cmd": "which {binary} 2>/dev/null",
}
