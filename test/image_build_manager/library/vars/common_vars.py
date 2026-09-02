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
Image Build Manager — Module-Specific Variables

Common vars (ssh_opts, config names, timeouts) live in the
``omnia_auto`` package and are set via ``omnia_auto.configure()``
in conftest.py.

Only module-specific constants remain here.
"""

import os
import re

# =============================================================================
# DIRECTORY PATHS
# =============================================================================

# Module root: test/ directory (where conftest.py lives)
MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))

# Parent of module root: test/
TEST_ROOT = os.path.dirname(MODULE_ROOT)

# Omnia monorepo root: omnia/
MONOREPO_ROOT = os.path.dirname(TEST_ROOT)

# src/ paths — used when dataset is empty (default: use src/ directly)
SRC_INPUT_DIR = os.path.join(
    MONOREPO_ROOT, "src", "image_build_manager", "input",
)
SRC_REPO_OUTPUT_DIR = os.path.join(
    MONOREPO_ROOT, "src", "image_build_manager", "samples",
    "repo_manager_output",
)

# =============================================================================
# DOMAIN IDENTITY
# =============================================================================

# Domain name used for remote path resolution
DOMAIN_NAME = "image_build_manager"

# Environment variable names on the target host
ENV_OMNIA_DATA_PATH = "OMNIA_DATA_PATH"
ENV_OMNIA_PROJECT_NAME = "OMNIA_PROJECT_NAME"

# =============================================================================
# INPUT FILE NAMES
# =============================================================================

# Domain config file (inside the domain input directory)
IBM_CONFIG_FILE = "image_build_config.yml"

# =============================================================================
# PLAYBOOK CONFIGURATION (module-specific)
# =============================================================================

# Playbook entry point (relative to playbooks/)
PLAYBOOK_ENTRY_POINT = "image_build_manager.yml"
PLAYBOOK_WORKDIR = "src/image_build_manager/playbooks"

# Valid playbook tags
PLAYBOOK_TAGS = [
    "precheck",
    "validate",
    "prepare",
    "build",
    "cleanup",
    "cleanup_images",
    "upgrade",
    "rollback",
]

# =============================================================================
# SHARED PATH DEFAULTS (runtime output on target host)
# =============================================================================
# Derived from OMNIA_DATA_PATH env var when available; falls back for dev boxes.

SHARED_PATH = os.environ.get(
    ENV_OMNIA_DATA_PATH, "/opt/omnia"
) + "/image_build_manager"

# =============================================================================
# CONTAINER NAMES
# =============================================================================

MINIO_CONTAINER = "minio-server"
REGISTRY_CONTAINER = "registry"

# =============================================================================
# S3 / REGISTRY CONSTANTS
# =============================================================================

REGISTRY_PORT = 5000

S3_EXPECTED_BUCKETS = [
    "s3://boot-images",
    "s3://efi",
]

S3CMD_CONFIG_PATH = "/root/.s3cfg"
CREDENTIALS_FILE_NAME = "image_build_credentials.yml"
CREDENTIALS_KEY_NAME = ".image_build_credentials_key"

# Firewall ports opened by prepare (if firewalld managed)
FIREWALL_PORTS = ["9000/tcp", "9001/tcp", "5000/tcp"]

# Listening ports to verify after prepare (container port bindings)
LISTENING_PORTS = [9000, 9001, 5000]

# Systemd services created by prepare
SYSTEMD_SERVICES = ["minio.service", "registry.service"]

# Build status output path template
BUILD_STATUS_PATH = (
    "{shared_path}/output/{project}/build_status.yml"
)

# Build log directory template (on target host)
BUILD_LOG_PATH = (
    "{shared_path}/log/{project}/"
)

# Playbook command template (for HOW TO FIX messages)
PLAYBOOK_CMD = (
    "cd {clone_path}/src/image_build_manager/playbooks && "
    "ansible-playbook image_build_manager.yml"
)

# Image artifact types in S3 (per functional group)
IMAGE_TYPES = ["initramfs", "vmlinuz", "rhel"]

# Image type display names for S3 verification output
IMAGE_TYPE_DISPLAY = {
    "initramfs": "initramfs",
    "vmlinuz": "vmlinuz",
    "rhel": "rootfs",
}

# Functional group packages filename
FG_PACKAGES_FILENAME = "functional_group_packages.yml"

# Package groups config filename (config-mode fallback)
PACKAGE_GROUPS_FILENAME = "package_groups.yml"

# Catalog file env var (catalog mode — on target host)
ENV_CATALOG_FILE_PATH = "CATALOG_FILE_PATH"

# =============================================================================
# SQUASHFS / IMAGE VERIFICATION PATHS
# =============================================================================

# Base prefixes for collision-safe image verification workspaces.
# A unique token is appended for every verifier invocation.
IMAGE_VERIFY_TEMP_IMAGE = "/tmp/ibm_test_image"  # nosec B108
IMAGE_VERIFY_TEMP_MOUNT = "/tmp/ibm_test_mount"  # nosec B108

# Package required for squashfs image verification
SQUASHFS_PACKAGE = "squashfs-tools"

# S3 bucket for boot images
S3_BOOT_IMAGES_BUCKET = "s3://boot-images"

# =============================================================================
# CONFIG VALIDATION CONSTANTS
# =============================================================================

# IPv4 address regex pattern
IPV4_PATTERN = re.compile(
    r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}'
    r'(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$'
)

# Required fields in test_config.yml
REQUIRED_CONFIG_FIELDS = [
    "report_path",
    "report_name",
]

# Required files inside a dataset directory (when dataset is set)
REQUIRED_DATASET_FILES = [
    "input/image_build_config.yml",
]

# Required files in src/ (when dataset is empty — default mode)
REQUIRED_SRC_FILES = [
    "image_build_config.yml",
]

# =============================================================================
# CENTRALIZED SHELL COMMANDS
# =============================================================================
# All shell commands used by verification functions.
# Use .format() with named placeholders to fill in runtime values.

CMDS = {
    # --- Podman ---
    "podman_ps": (
        "podman ps --format '{{{{.Names}}}}\t{{{{.Status}}}}'"
        " --filter name={container}"
    ),
    "podman_ps_check": (
        "podman ps --format '{{{{.Names}}}}'"
        " --filter name=^{container}$ 2>/dev/null"
    ),
    "podman_ps_all": (
        "podman ps -a --format '{{{{.Names}}}}\t{{{{.Status}}}}'"
        " --filter name={container}"
    ),
    "podman_inspect": (
        "podman inspect --format '{{{{.State.Status}}}}'"
        " {container} 2>/dev/null"
    ),
    # --- S3 / s3cmd ---
    "s3cmd_ls": "s3cmd ls 2>/dev/null",
    "s3cmd_ls_bucket": "s3cmd ls -Hr {bucket} 2>/dev/null",
    "s3cmd_cfg_check": "test -f {path} && echo exists",
    # --- Registry ---
    "curl_registry_catalog": (
        "curl -sk https://{registry}:{port}/v2/_catalog 2>/dev/null"
    ),
    "curl_registry_tags": (
        "curl -sk https://{registry}:{port}/v2/{repo}/tags/list"
        " 2>/dev/null"
    ),
    # --- Files ---
    "file_exists": "test -f {path} && echo exists",
    "dir_exists": "test -d {path} && echo exists",
    "cat_file": "cat {path} 2>/dev/null",
    "file_stat": (
        "stat -c '%A %U:%G %s %n' {path} 2>/dev/null"
    ),
    # --- Ansible / Playbook ---
    "ansible_playbook": (
        "cd {workdir} && ansible-playbook {playbook}"
        " --tags {tag} -v 2>&1"
    ),
    # --- System ---
    "hostname_short": "hostname -s 2>/dev/null",
    "hostname_domain": "hostname -d 2>/dev/null",
    "hostname_fqdn": "hostname -f 2>/dev/null",
    "hostname_ip": "hostname -I 2>/dev/null",
    "rpm_check": "rpm -q {package} 2>/dev/null",
    "which_cmd": "which {binary} 2>/dev/null",
    # --- Systemd ---
    "systemctl_is_active": (
        "systemctl is-active {service} 2>/dev/null"
    ),
    "systemctl_status": (
        "systemctl status {service} 2>/dev/null"
    ),
    # --- Firewall ---
    "firewall_list_ports": (
        "firewall-cmd --list-ports 2>/dev/null"
    ),
    # --- Ports ---
    "ss_listen_port": (
        "ss -tlnp 'sport = :{port}' 2>/dev/null"
    ),
    # --- Registry (HTTP) ---
    "curl_registry_catalog_http": (
        "curl -sk http://localhost:{port}/v2/_catalog"
        " 2>/dev/null"
    ),
    # --- Git ---
    "git_remote_url": "git -C {path} remote get-url origin 2>/dev/null",
    "git_branch": "git -C {path} branch --show-current 2>/dev/null",
    "git_log_last": "git -C {path} log -1 --oneline 2>/dev/null",
    # --- Squashfs ---
    "unsquashfs_ls": (
        "unsquashfs -l {image_path} 2>/dev/null"
        " | grep -c '{pattern}'"
    ),
    "squashfs_check": "which unsquashfs 2>/dev/null",
    "squashfs_tools_check": (
        "which unsquashfs 2>/dev/null || "
        "rpm -q {package} 2>/dev/null"
    ),
    "squashfs_tools_install": (
        "dnf install -y {package} 2>&1"
    ),
    # --- Image mount / verify ---
    "umount": "umount {flags} {path} 2>/dev/null",
    "rm_file": "rm -f {path} 2>/dev/null",
    "rm_dir": "rm -rf {path} 2>/dev/null",
    "mkdir_p": "mkdir -p {path}",
    "mount_squashfs": (
        "mount -t squashfs -o ro {image} {mount} 2>/dev/null"
    ),
    "s3cmd_get": (
        "s3cmd get {s3_path} {dest} --force 2>/dev/null"
    ),
    "rpm_list_installed": (
        "rpm --root={root} -qa 2>/dev/null"
    ),
    # --- Registry (regctl) ---
    "regctl_repo_ls": (
        "regctl repo ls --limit 500 {registry} 2>/dev/null"
    ),
    "regctl_tag_ls": (
        "regctl tag ls {registry}/{repo} 2>/dev/null"
    ),
    # --- S3 (recursive list) ---
    "s3cmd_ls_recursive": (
        "s3cmd ls -Hr {bucket} 2>/dev/null"
    ),
    # --- Registry (curl, scheme-agnostic) ---
    "curl_registry_catalog_scheme": (
        "curl -sk {scheme}://localhost:{port}/v2/_catalog"
        " 2>/dev/null"
    ),
    # --- Connectivity / Precheck ---
    "echo_test": "echo connectivity_ok 2>/dev/null",
    "env_check": "echo ${env_var} 2>/dev/null",
    "source_env_file": (
        "test -f /etc/profile.d/omnia-env.sh && "
        "source /etc/profile.d/omnia-env.sh && "
        "echo ${env_var} 2>/dev/null"
    ),
    "cat_build_log": (
        "tail -n {lines} {log_path} 2>/dev/null"
    ),
    # --- Podman (container running check) ---
    "podman_ps_running": (
        "podman ps --format '{{{{.Names}}}} {{{{.Status}}}}'"
        " --filter name=^{container}$ 2>/dev/null"
    ),
    "podman_ps_all_status": (
        "podman ps -a --format '{{{{.Names}}}} {{{{.Status}}}}'"
        " --filter name=^{container}$ 2>/dev/null"
    ),
}
