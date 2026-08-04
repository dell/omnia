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
Repo Manager — Module-Specific Variables

Common vars (ssh_opts, config names, timeouts) live in the
``omnia_auto`` package and are set via ``omnia_auto.configure()``
in conftest.py.

Only module-specific constants remain here.

Reference: src/repo_manager/vars/default.yml
           src/repo_manager/vars/cleanup_pulp_vars.yml
           src/repo_manager/vars/credential_vars.yml
           src/repo_manager/roles/deploy_pulp/vars/main.yml
"""

import os

# =============================================================================
# DIRECTORY PATHS
# =============================================================================

# Module root: test/ directory (where conftest.py lives)
MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))

# Repository root
REPO_ROOT = os.path.dirname(MODULE_ROOT)

# =============================================================================
# DOMAIN IDENTITY
# =============================================================================

DOMAIN_NAME = "repo_manager"

ENV_OMNIA_DATA_PATH = "OMNIA_DATA_PATH"
ENV_OMNIA_PROJECT_NAME = "OMNIA_PROJECT_NAME"

# =============================================================================
# INPUT FILE NAMES
# =============================================================================

# Domain config files (inside the domain input directory)
CONFIG_FILE = "repo_manager_config.yml"
CREDENTIALS_FILE_NAME = "repo_manager_config_credentials.yml"
CREDENTIALS_KEY_NAME = ".repo_manager_config_credentials_key"
ENDPOINT_CONFIG_FILE = "repo_manager_endpoint_config.yml"
SOFTWARE_CONFIG_FILE = "software_config.json"

# =============================================================================
# PLAYBOOK CONFIGURATION (module-specific)
# =============================================================================

PLAYBOOK_ENTRY_POINT = "repo_manager.yml"
PLAYBOOK_WORKDIR = "src/repo_manager/playbooks"

# Valid playbook tags — from src/repo_manager/playbooks/repo_manager.yml
PLAYBOOK_TAGS = [
    "validate",
    "deploy",
    "download",
    "status",
    "cleanup",
    "cleanup_pulp",
    "cleanup_repos",
    "upgrade",
    "rollback",
]

# =============================================================================
# OMNIA BASE DIRECTORIES — from vars/default.yml
# =============================================================================

OMNIA_BASE_DIR = "/opt/omnia"
SHARED_PATH = OMNIA_BASE_DIR
REPO_MANAGER_DATA_DIR = f"{OMNIA_BASE_DIR}/.data"
REPO_MANAGER_LOG_DIR = f"{OMNIA_BASE_DIR}/log/repo_manager"
REPO_MANAGER_OFFLINE_REPO_DIR = f"{OMNIA_BASE_DIR}/offline_repo"

# =============================================================================
# PULP SERVER CONFIGURATION — from vars/default.yml and deploy_pulp/vars/main.yml
# =============================================================================

PULP_CONTAINER = "pulp"
PULP_IMAGE = "docker.io/pulp/pulp:3.113"
PULP_PROTOCOL_HTTPS = True

# Port configuration — from deploy_pulp/vars/main.yml
PULP_PORT = 2225
PULP_PORT_HTTP = "2225:80"
PULP_PORT_HTTPS = "2225:2225"

LISTENING_PORTS = [2225]
SYSTEMD_SERVICES = ["pulp.service"]

# Pulp config directories — from vars/default.yml
PULP_CONFIG_BASE_DIR = f"{OMNIA_BASE_DIR}/pulp_config"
PULP_CONFIG_DIR = f"{PULP_CONFIG_BASE_DIR}/pulp"
PULP_CERTS_DIR = f"{PULP_CONFIG_DIR}/settings/certs"
PULP_SERVER_CRT = f"{PULP_CERTS_DIR}/pulp_webserver.crt"
PULP_SERVER_KEY = f"{PULP_CERTS_DIR}/pulp_webserver.key"
PULP_CRT_TRACK_FILE = f"{PULP_CONFIG_DIR}/pulp_crt_track.txt"
PULP_LOGS_DIR = f"{PULP_CONFIG_BASE_DIR}/log/pulp"
PULP_HA_DIR = f"{PULP_CONFIG_DIR}/pulp_ha"
PULP_CLI_CONFIG = f"{PULP_HA_DIR}/cli.toml"

# Quadlet/systemd path — from deploy_pulp/tasks/preflight_checks.yml
PULP_QUADLET_PATH = f"/etc/containers/systemd/{PULP_CONTAINER}.container"

# Pulp API endpoint — from deploy_pulp/vars/main.yml
PULP_STATUS_URL_HTTPS = "https://{{ip}}:{port}/pulp/api/v3/status/"
PULP_STATUS_URL_HTTP = "http://{{ip}}:{port}/pulp/api/v3/status/"

# Retry configuration — from deploy_pulp/vars/main.yml
ENDPOINT_RETRIES = 10
ENDPOINT_DELAY = 10
ENDPOINT_TIMEOUT = 60

# =============================================================================
# RHEL SUBSCRIPTION — from vars/default.yml
# =============================================================================

RHEL_REPO_CERTS_DIR = f"{OMNIA_BASE_DIR}/rhel_repo_certs"

# =============================================================================
# CLEANUP DIRECTORIES — from vars/cleanup_pulp_vars.yml
# =============================================================================

PULP_CLEANUP_DIRECTORIES = [
    PULP_CONFIG_BASE_DIR,
    RHEL_REPO_CERTS_DIR,
    REPO_MANAGER_OFFLINE_REPO_DIR,
    # ~/.config/pulp is handled separately (user home-relative)
]

OMNIA_TARGET_FILE = "/etc/systemd/system/omnia.target"

# =============================================================================
# CREDENTIAL CONFIGURATION — from vars/credential_vars.yml
# =============================================================================

CREDENTIAL_VAULT_PATH = (
    "{{input_dir}}/.repo_manager_config_credentials_key"
)

# =============================================================================
# OUTPUT PATHS
# =============================================================================

REPO_STATUS_PATH = (
    "{shared_path}/repo_manager/output/{project}/repo_status.yml"
)

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
    "podman_image_exists": (
        "podman image exists {image} 2>/dev/null"
    ),
    # --- Pulp ---
    "pulp_status": "/usr/local/bin/pulp status 2>/dev/null",
    "pulp_repo_list": "/usr/local/bin/pulp rpm repository list 2>/dev/null",
    "pulp_version": "/usr/local/bin/pulp --version 2>/dev/null",
    # --- Files ---
    "file_exists": "test -f {path} && echo exists",
    "dir_exists": "test -d {path} && echo exists",
    "cat_file": "cat {path} 2>/dev/null",
    "file_stat": (
        "stat -c '%A %U:%G %s %n' {path} 2>/dev/null"
    ),
    # --- System ---
    "hostname_cmd": "hostname 2>/dev/null",
    "hostname_fqdn": "hostname -f 2>/dev/null",
    "hostname_ip": "hostname -I 2>/dev/null",
    # --- Systemd ---
    "systemctl_is_active": (
        "systemctl is-active {service} 2>/dev/null"
    ),
    "systemctl_status": (
        "systemctl status {service} 2>/dev/null"
    ),
    # --- Ports ---
    "ss_listen_port": (
        "ss -tlnp 'sport = :{port}' 2>/dev/null"
    ),
    # --- Pulp API ---
    "curl_pulp_status_https": (
        "curl -sk https://localhost:{port}/pulp/api/v3/status/"
        " 2>/dev/null"
    ),
    "curl_pulp_status_http": (
        "curl -sk http://localhost:{port}/pulp/api/v3/status/"
        " 2>/dev/null"
    ),
    # --- Package / Binary ---
    "which_cmd": "which {binary} 2>/dev/null",
    "rpm_check": "rpm -q {package} 2>/dev/null",
    # --- Firewall ---
    "firewall_list_ports": (
        "firewall-cmd --list-ports 2>/dev/null"
    ),
    # --- Find ---
    "find_file_count": (
        "find {path} -type f 2>/dev/null | wc -l"
    ),
    # --- Ansible / Playbook ---
    "ansible_playbook": (
        "cd {workdir} && ansible-playbook {playbook}"
        " --tags {tag} -v 2>&1"
    ),
}
