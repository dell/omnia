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

# Test root: test/ directory
TEST_ROOT = os.path.dirname(MODULE_ROOT)

# Repository root: omnia-bsm/
REPO_ROOT = os.path.dirname(TEST_ROOT)

# =============================================================================
# DOMAIN IDENTITY
# =============================================================================

DOMAIN_NAME = "main"
OMNIA_RELEASE = "2.3.0.0"

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
# Note: domain-specific log/ and input/ dirs are created by domain-init.sh,
# not by the base setup.  Only {data_path} and {data_path}/.data are
# created by create_base_dirs().
BASE_DIRS: List[str] = [
    "{data_path}",
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

# Domains prepared by --prepare-base (in order)
PREPARE_BASE_DOMAINS: List[str] = [
    "repo_manager",
    "image_build_manager",
    "orchestrator",
]

# Lifecycle phases for --prepare-base
PREPARE_BASE_PHASES: List[str] = [
    "validate",
    "credentials",
    "prepare",
]

# Domains that have domain-init.sh scripts
DOMAINS_WITH_INIT: List[str] = [
    "build_stream",
    "discovery",
    "image_build_manager",
    "orchestrator",
    "repo_manager",
    "telemetry",
    "utils",
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
    "--prepare-base",
    "--run", "-r",
    "--cleanup",
    "--check-deps",
    "--help", "-h",
]

VALID_CLI_OPTIONS: List[str] = [
    "--deps-only",
    "--force-deps",
    "--skip",
    "--dry-run",
    "--skip-catalog",
    "--skip-omnia-cli",
    "--tags", "-t",
    "--all",
]

# =============================================================================
# OMNIA-CLI COMMANDS
# =============================================================================

OMNIA_CLI_COMMANDS: List[str] = [
    "status",
    "check",
    "edit",
    "repo-manager",
    "image-build",
    "version",
    "help",
    "logs",
    "vault",
]

# Domains addressable via omnia-cli <domain>
OMNIA_CLI_DOMAINS: List[str] = [
    "repo-manager",
    "image-build",
    "orchestrator",
    "discovery",
    "telemetry",
    "build-stream",
    "utils",
]

# Generic tags shown in omnia.sh help (per domain)
OMNIA_SH_GENERIC_TAGS: List[str] = [
    "precheck",
    "validate",
    "prepare",
    "execute",
    "cleanup",
]

# Expected sections in omnia-cli help output
OMNIA_CLI_HELP_SECTIONS: List[str] = [
    "USAGE:",
    "COMMANDS:",
    "OPTIONS:",
    "ENVIRONMENT:",
    "EXAMPLES:",
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
        " --setup-venv --deps-only 2>&1"
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
    "omnia_sh_deps_only": (
        "cd {clone_path} && bash {omnia_sh}"
        " --setup-venv --deps-only 2>&1"
    ),
    "omnia_sh_unknown_option": (
        "cd {clone_path} && bash {omnia_sh}"
        " --bogus 2>&1"
    ),
    "omnia_sh_cleanup": (
        "cd {clone_path} && bash {omnia_sh}"
        " --cleanup 2>&1"
    ),
    "omnia_sh_cleanup_all": (
        "cd {clone_path} && bash {omnia_sh}"
        " --cleanup --all 2>&1"
    ),
    "omnia_sh_check_deps": (
        "cd {clone_path} && bash {omnia_sh}"
        " --check-deps 2>&1"
    ),
    "omnia_sh_init_domain": (
        "cd {clone_path} && bash {omnia_sh}"
        " --init {domain} 2>&1"
    ),
    "omnia_sh_init_force_deps": (
        "cd {clone_path} && bash {omnia_sh}"
        " --init --force-deps 2>&1"
    ),
    "omnia_sh_setup_skip_catalog": (
        "cd {clone_path} && bash {omnia_sh}"
        " --setup-venv --deps-only --skip-catalog 2>&1"
    ),
    "omnia_sh_setup_skip_omnia_cli": (
        "cd {clone_path} && bash {omnia_sh}"
        " --setup-venv --deps-only --skip-omnia-cli 2>&1"
    ),
    "omnia_sh_force_deps_invalid": (
        "cd {clone_path} && bash {omnia_sh}"
        " --force-deps 2>&1"
    ),
    # --- --skip / --dry-run ---
    "omnia_sh_skip_domain": (
        "cd {clone_path} && bash {omnia_sh}"
        " --init --skip {domain} 2>&1"
    ),
    "omnia_sh_skip_invalid_domain": (
        "cd {clone_path} && bash {omnia_sh}"
        " --init --skip nonexistent_domain_xyz 2>&1"
    ),
    "omnia_sh_skip_with_include": (
        "cd {clone_path} && bash {omnia_sh}"
        " --init telemetry --skip utils 2>&1"
    ),
    "omnia_sh_skip_without_init": (
        "cd {clone_path} && bash {omnia_sh}"
        " --skip telemetry 2>&1"
    ),
    "omnia_sh_skip_no_args": (
        "cd {clone_path} && bash {omnia_sh}"
        " --init --skip 2>&1"
    ),
    "omnia_sh_dry_run": (
        "cd {clone_path} && bash {omnia_sh}"
        " --init --dry-run 2>&1"
    ),
    "omnia_sh_dry_run_with_skip": (
        "cd {clone_path} && bash {omnia_sh}"
        " --init --dry-run --skip {domain} 2>&1"
    ),
    "omnia_sh_dry_run_without_init": (
        "cd {clone_path} && bash {omnia_sh}"
        " --dry-run 2>&1"
    ),
    # --- Execution: actual omnia.sh operations ---
    "omnia_sh_run_domain_tag": (
        "cd {clone_path} && bash {omnia_sh}"
        " --run {domain} --tags {tag} 2>&1"
    ),
    "omnia_sh_cleanup_yes": (
        "cd {clone_path} && echo yes"
        " | bash {omnia_sh} --cleanup 2>&1"
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
    "domain_output_dir_exists": (
        "test -d {data_path}/{domain}/output/{project}"
        " && echo exists"
    ),
    "domain_runtime_log_dir_exists": (
        "test -d {data_path}/{domain}/log/{project}"
        " && echo exists"
    ),
    # --- System ---
    "hostname_cmd": "hostname 2>/dev/null",
    "which_cmd": "which {binary} 2>/dev/null",
    # --- omnia-cli execution ---
    "omnia_cli_help": (
        "cd {clone_path} && bash {omnia_cli} help 2>&1"
    ),
    "omnia_cli_version": (
        "cd {clone_path} && bash {omnia_cli} version 2>&1"
    ),
    "omnia_cli_status": (
        "cd {clone_path} && bash {omnia_cli} status 2>&1"
    ),
    "omnia_cli_status_project": (
        "cd {clone_path} && bash {omnia_cli}"
        " status --project {project} 2>&1"
    ),
    "omnia_cli_check": (
        "cd {clone_path} && bash {omnia_cli} check 2>&1"
    ),
    "omnia_cli_repo_manager": (
        "cd {clone_path} && bash {omnia_cli}"
        " repo-manager 2>&1"
    ),
    "omnia_cli_image_build": (
        "cd {clone_path} && bash {omnia_cli}"
        " image-build 2>&1"
    ),
    "omnia_cli_domain": (
        "cd {clone_path} && bash {omnia_cli}"
        " {domain} 2>&1"
    ),
    "omnia_cli_help_domain": (
        "cd {clone_path} && bash {omnia_cli}"
        " help {domain} 2>&1"
    ),
    "omnia_cli_unknown": (
        "cd {clone_path} && bash {omnia_cli}"
        " nonexistent_cmd 2>&1"
    ),
    # --- omnia-cli logs ---
    "omnia_cli_logs_help": (
        "cd {clone_path} && bash {omnia_cli}"
        " logs --help 2>&1"
    ),
    "omnia_cli_logs_limit": (
        "cd {clone_path} && bash {omnia_cli}"
        " logs {domain} --limit {limit} 2>&1"
    ),
    "omnia_cli_logs_limit_invalid": (
        "cd {clone_path} && bash {omnia_cli}"
        " logs {domain} --limit {limit} 2>&1"
    ),
    "omnia_cli_logs_limit_short": (
        "cd {clone_path} && bash {omnia_cli}"
        " logs {domain} -l {limit} 2>&1"
    ),
    # --- omnia.sh tags validation ---
    "omnia_sh_run_tags": (
        "cd {clone_path} && bash {omnia_sh}"
        " --run {domain} --tags {tag} 2>&1"
    ),
    # --- env source validation ---
    "omnia_sh_validate_env_bad_ip": (
        "cd {clone_path} && bash -c '"
        "env_file=$(mktemp);"
        " sed \"s/^SYSTEM_ADMIN_NIC_IPV4=.*/SYSTEM_ADMIN_NIC_IPV4=/\""
        " {omnia_env} > $env_file;"
        " source {omnia_sh_dir}/omnia.sh --help >/dev/null 2>&1;"
        " bash -c \"set -a; . $env_file; set +a;"
        " if [ -z \\\"\\$SYSTEM_ADMIN_NIC_IPV4\\\" ]; then"
        " exit 1; fi\";"
        " rc=$?; rm -f $env_file; exit $rc"
        "' 2>&1"
    ),
    # --- --prepare-base ---
    "omnia_sh_prepare_base_dry_run": (
        "cd {clone_path} && bash {omnia_sh}"
        " --prepare-base --dry-run 2>&1"
    ),
    "omnia_sh_prepare_base_dry_run_skip": (
        "cd {clone_path} && bash {omnia_sh}"
        " --prepare-base --dry-run --skip {domain} 2>&1"
    ),
    "omnia_sh_prepare_base_skip_invalid": (
        "cd {clone_path} && bash {omnia_sh}"
        " --prepare-base --skip nonexistent_domain_xyz 2>&1"
    ),
    "omnia_sh_prepare_base_skip_all": (
        "cd {clone_path} && bash {omnia_sh}"
        " --prepare-base --skip"
        " repo_manager,image_build_manager,orchestrator 2>&1"
    ),
    "omnia_sh_prepare_base_help": (
        "cd {clone_path} && bash {omnia_sh} --help 2>&1"
    ),
    # --- omnia-cli remaining domains ---
    "omnia_cli_orchestrator": (
        "cd {clone_path} && bash {omnia_cli}"
        " orchestrator 2>&1"
    ),
    "omnia_cli_telemetry": (
        "cd {clone_path} && bash {omnia_cli}"
        " telemetry 2>&1"
    ),
    "omnia_cli_build_stream": (
        "cd {clone_path} && bash {omnia_cli}"
        " build-stream 2>&1"
    ),
}
