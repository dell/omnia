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
Orchestrator — Module-Specific Variables

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
DOMAIN_NAME = "orchestrator"

# Environment variable names on the target host
ENV_OMNIA_DATA_PATH = "OMNIA_DATA_PATH"
ENV_OMNIA_PROJECT_NAME = "OMNIA_PROJECT_NAME"

# Domain config files (inside the domain input directory)
ORCHESTRATOR_CONFIG_FILE = "orchestrator_config.yml"
OMNIA_CONFIG_FILE = "omnia_config.yml"
NETWORK_SPEC_FILE = "network_spec.yml"
SECURITY_CONFIG_FILE = "security_config.yml"
STORAGE_CONFIG_FILE = "storage_config.yml"
HA_CONFIG_FILE = "high_availability_config.yml"

# Playbook entry point
PLAYBOOK_ENTRY_POINT = "orchestrator.yml"
PLAYBOOK_WORKDIR = "src/orchestrator/playbooks"

# Valid playbook tags (mapped to sub-playbooks)
PLAYBOOK_TAGS: List[str] = [
    "prepare",
    "validate",
    "credentials",
    "deploy_openchami",
    "provision_kubernetes",
    "provision_slurm",
    "provision_os",
    "provision_custom",
    "cleanup",
    "upgrade",
    "rollback",
]

# =============================================================================
# Domain-specific paths
# =============================================================================
SHARED_PATH = "/opt/omnia/orchestrator"
INPUT_PATH_TEMPLATE = "/opt/omnia/orchestrator/input/{project}"
OUTPUT_PATH_TEMPLATE = "/opt/omnia/orchestrator/output/{project}"
REPO_MANAGER_OUTPUT_TEMPLATE = (
    "/opt/omnia/repo_manager/output/{project}/repo_status.yml"
)

# Credentials
CREDENTIALS_FILE_NAME = "omnia_config_credentials.yml"
CREDENTIALS_KEY_NAME = ".omnia_config_credentials_key"

# =============================================================================
# OpenCHAMI containers (fabrica-based architecture via Quadlet)
# =============================================================================
OPENCHAMI_CONTAINERS: List[str] = [
    "smd",
    "boot-service",
    "metadata-service",
    "postgres",
    "tokensmith",
    "step-ca",
    "haproxy",
    "coresmd-coredns",
    "coresmd-coredhcp",
]

# Systemd target managed by orchestrator (fabrica Quadlet)
SYSTEMD_SERVICES: List[str] = [
    "openchami.target",
]

# Firewall ports (from deploy_openchami vars)
FIREWALL_PORTS: List[str] = [
    "8443/tcp",
    "8081/tcp",
    "5432/tcp",
    "27778/tcp",
    "27779/tcp",
]

# =============================================================================
# Shell commands — all commands MUST be in this dict.
# Use .format() with named placeholders to fill in runtime values.
# =============================================================================
CMDS: Dict[str, str] = {
    # --- Podman ---
    "podman_ps": (
        "podman ps --format '{{{{.Names}}}}\\t{{{{.Status}}}}'"
        " --filter name={container}"
    ),
    "podman_ps_check": (
        "podman ps --format '{{{{.Names}}}}'"
        " --filter name=^{container}$ 2>/dev/null"
    ),
    "podman_ps_all": (
        "podman ps -a --format '{{{{.Names}}}}\\t{{{{.Status}}}}'"
        " --filter name={container}"
    ),
    "podman_inspect": (
        "podman inspect --format '{{{{.State.Status}}}}'"
        " {container} 2>/dev/null"
    ),

    # --- Files ---
    "file_exists": "test -f {path} && echo exists",
    "dir_exists": "test -d {path} && echo exists",
    "cat_file": "cat {path} 2>/dev/null",
    "file_stat": (
        "stat -c '%A %U:%G %s %n' {path} 2>/dev/null"
    ),
    "ls_files": "ls -1 {path} 2>/dev/null",

    # --- Ansible / Playbook ---
    "ansible_playbook": (
        "cd {workdir} && ansible-playbook {playbook}"
        " --tags {tag} -v 2>&1"
    ),

    # --- System ---
    "hostname_cmd": "hostname 2>/dev/null",
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

    # --- Network ---
    "ping_check": "ping -c 1 -W 2 {host} 2>/dev/null",
    "curl_check": (
        "curl -sk --connect-timeout 5 https://{host}:{port} 2>/dev/null"
    ),

    # --- YAML ---
    "yaml_parse": (
        "python3 -c \"import yaml; yaml.safe_load(open('{path}'))\""
        " 2>&1"
    ),

    # --- Git ---
    "git_remote_url": "git -C {path} remote get-url origin 2>/dev/null",
    "git_branch": "git -C {path} branch --show-current 2>/dev/null",

    # --- Kubernetes ---
    "kubectl_get_nodes": "kubectl get nodes -o wide 2>/dev/null",
    "kubectl_get_pods": (
        "kubectl get pods -A -o wide 2>/dev/null"
    ),

    # --- Slurm ---
    "sinfo": "sinfo -N -l 2>/dev/null",
    "scontrol_show_nodes": "scontrol show nodes 2>/dev/null",
}
