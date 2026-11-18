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

# OIM log backup input file (optional)
BACKUP_OIM_LOGS_CONFIG_FILE = "backup_oim_logs_config.yml"

# Slurm config util input file (optional)
SLURM_CONFIG_UTIL_CONFIG_FILE = "slurm_config_util_config.yml"

# =============================================================================
# PLAYBOOK CONFIGURATION (module-specific)
#============================================================================

# Playbook entry points (relative to workdir)
PLAYBOOK_UTILS = "playbooks/utils.yml"
PLAYBOOK_COLLECT = "playbooks/collect.yml"
PLAYBOOK_INSTALL_OS = "playbooks/install_os.yml"
PLAYBOOK_BACKUP_OIM_LOGS = "playbooks/backup_oim_logs/backup_oim_logs.yml"
PLAYBOOK_SLURM_CONFIG_UTIL = "playbooks/slurm_config_util/slurm_config_util.yml"
PLAYBOOK_CLEANUP_SLURM_CONFIG_BACKUPS = "playbooks/slurm_config_util/cleanup_slurm_config_backups.yml"
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

# Valid playbook tags for backup_oim_logs.yml
BACKUP_OIM_LOGS_TAGS = [
    "setup",
    "bundle",
]

# Valid playbook tags for slurm_config_util.yml
SLURM_CONFIG_UTIL_TAGS = [
    "config_backup",
    "slurm_cleanup",
    "config_rollback",
]

# Directories present in every Slurm config backup
SLURM_CONFIG_BACKUP_DIRECTORIES = [
    "etc/slurm",
    "etc/munge",
    "etc/my.cnf.d",
]

# Valid playbook tags for utils.yml (main entry point)
UTILS_PLAYBOOK_TAGS = [
    "precheck",
    "setup",
    "collect",
    "install_os",
    "backup_oim_logs",
    "cleanup",
    "cleanup_logs",
    "cleanup_install_os",
    "cleanup_backup_oim_logs",
    "slurm_config_backup",
    "slurm_config_cleanup",
    "slurm_config_rollback",
    "cleanup_slurm_config_backups",
]

# Domains backed up by backup_oim_logs.yml when no config file selection is supplied
BACKUP_ALL_DOMAINS = [
    "repo_manager",
    "image_build_manager",
    "orchestrator",
    "discovery",
    "telemetry",
    "build_stream",
    "utils",
]

# OIM log backup bundle naming pattern
BACKUP_BUNDLE_PATTERN = r"omnia_oim_logs_\d{8}-\d{6}\.tar\.gz"

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

# Functional groups for log collection — representative legacy/base names,
# used for human-readable messages. Actual validation uses
# FUNCTIONAL_GROUP_NAME_PATTERN below, since Omnia's PXE-mapping naming
# convention optionally inserts an OS name and version between the role and
# the architecture (e.g. "slurm_node_rhel_10_0_aarch64"), and the set of OS
# names/versions is not fixed.
FUNCTIONAL_GROUPS = [
    "service_kube_control_plane_x86_64",
    "service_kube_node_x86_64",
    "slurm_control_node_x86_64",
    "slurm_node_x86_64",
    "slurm_node_aarch64",
    "login_node_x86_64",
    "login_compiler_node_x86_64",
    "login_compiler_node_aarch64",
]

# Roles supported for log collection, matched independently of OS name/version.
FUNCTIONAL_GROUP_ROLES = (
    "service_kube_control_plane_first",
    "service_kube_control_plane",
    "service_kube_node",
    "slurm_control_node",
    "slurm_node",
    "login_node",
    "login_compiler_node",
)

# Matches "<role>_<arch>" and Omnia's PXE-mapping convention of
# "<role>_<os>_<version segments>_<arch>" (e.g. "slurm_node_rhel_10_0_aarch64").
FUNCTIONAL_GROUP_NAME_PATTERN = re.compile(
    r"^(?:" + "|".join(FUNCTIONAL_GROUP_ROLES) + r")"
    r"(?:_(?:rhel|rocky|ubuntu|sles)(?:_[0-9]+)+)?"
    r"_(?:x86_64|aarch64)$"
)

# Same OS/version-agnostic matching, scoped to the K8s and Slurm/login role
# subsets respectively (used to detect which collect_pxe.yml sections are
# populated without hardcoding a single arch/OS variant).
K8S_FUNCTIONAL_GROUP_PATTERN = re.compile(
    r"^(?:service_kube_control_plane_first|service_kube_control_plane|service_kube_node)"
    r"(?:_(?:rhel|rocky|ubuntu|sles)(?:_[0-9]+)+)?"
    r"_(?:x86_64|aarch64)$"
)
SLURM_FUNCTIONAL_GROUP_PATTERN = re.compile(
    r"^(?:slurm_control_node|slurm_node|login_node|login_compiler_node)"
    r"(?:_(?:rhel|rocky|ubuntu|sles)(?:_[0-9]+)+)?"
    r"_(?:x86_64|aarch64)$"
)

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
# Note: data_path and project_name are optional - they fall back to env vars
REQUIRED_CONFIG_FIELDS = [
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

    # --- OCI Image Ingest ---
    "s3cmd_ls": "s3cmd ls {path} 2>/dev/null",
    "s3cmd_ls_bucket": "s3cmd ls s3://{bucket}/ 2>/dev/null",
    "s3cmd_info": "s3cmd info {path} 2>/dev/null",
    "regctl_version": "regctl version 2>/dev/null",
    "check_s3cfg": "test -f {path} && echo exists || echo missing",
    "vault_check_header": "head -1 {path} 2>/dev/null",
    "file_permissions": "stat -c '%a' {path} 2>/dev/null",
    "yaml_parse": (
        "python3 -c \"import yaml,sys; "
        "d=yaml.safe_load(open('{path}')); "
        "print(d)\" 2>/dev/null"
    ),
    "yaml_key_check": (
        "python3 -c \"import yaml; "
        "d=yaml.safe_load(open('{path}')); "
        "print(d.get('{key}', ''))\" 2>/dev/null"
    ),
    "grep_credential_scan": (
        "grep -rl '{pattern}' {path} 2>/dev/null || echo 'clean'"
    ),
    "unsquashfs_stat": "unsquashfs -s {path} 2>/dev/null",
    "sha256sum": "sha256sum {path} 2>/dev/null | awk '{{print $1}}'",
    "s3cmd_get_checksum": (
        "s3cmd info {path} 2>/dev/null | grep 'MD5\\|ETag' || echo ''"
    ),
    "find_build_status": (
        "find {path} -name 'build_status.yml' -type f 2>/dev/null | head -1"
    ),
    "check_lock_file": "test -f {path} && echo locked || echo unlocked",
    "list_s3_objects": "s3cmd ls -r s3://{bucket}/{prefix} 2>/dev/null",
}

# =============================================================================
# OCI IMAGE INGEST CONSTANTS
# =============================================================================

# OCI Image Ingest input files
OCI_IMAGE_INGEST_CONFIG_FILE = "oci_image_ingest_config.yml"
OCI_IMAGE_INGEST_CREDENTIALS_FILE = "oci_image_ingest_credentials.yml"

# OCI Image Ingest playbook
PLAYBOOK_OCI_IMAGE_INGEST = "playbooks/oci_image_ingest/ingest_oci_image.yml"

# OCI Image Ingest tag
OCI_IMAGE_INGEST_TAG = "oci_image_ingest"

# Supported values (this increment)
OCI_SUPPORTED_REGISTRY_TYPES = ["harbor"]
OCI_SUPPORTED_OPERATIONS = ["repo_to_bucket"]

# Architecture suffix to OCI platform mapping
OCI_ARCH_SUFFIX_MAP = {
    "_x86_64": "linux/amd64",
    "_aarch64": "linux/arm64",
}

# Build status fields
OCI_BUILD_STATUS_FILE = "build_status.yml"
OCI_IMAGE_BUILD_TYPE = "oci-image-ingest"
OCI_ACCEPTED_BUILD_TYPES = ["image-thrillhouse", "oci-image-ingest"]
# S3 bucket is read from build_status.yml s3_configurations.bucket at runtime
# No hardcoded bucket name — each environment configures its own

# Boot artifact patterns
OCI_VMLINUZ_PATTERN = r"vmlinuz-[\w.\-]+"
OCI_INITRAMFS_PATTERN = r"initramfs-[\w.\-]+\.img"
OCI_ROOTFS_FILE = "rootfs.squashfs"

# Rescue/debug kernel exclusion patterns
OCI_RESCUE_KERNEL_PATTERN = r".*rescue.*"
OCI_DEBUG_KERNEL_PATTERN = r".*\+debug$"

# Credential fields that must NOT appear in config
OCI_CREDENTIAL_FIELDS = ["username", "password", "token", "auth", "registry_username", "registry_password"]

# Prerequisite binaries
OCI_PREREQUISITE_BINARIES = ["regctl", "s3cmd", "mksquashfs"]
OCI_PREREQUISITE_FILES = [".s3cfg"]

# Working directory pattern
OCI_WORKDIR_PATTERN = "utils/workdir/{project}/oci-image-ingest"

# S3 path pattern
OCI_S3_PATH_PATTERN = "{bucket}/{functional_group}/{image_name}-ingest/{release}/"

# Release prefix safe character pattern
OCI_SAFE_CHAR_PATTERN = re.compile(r"[^A-Za-z0-9._-]")
