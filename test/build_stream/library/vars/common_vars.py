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
Build Stream — Module-Specific Variables

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

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))

TEST_ROOT = os.path.dirname(MODULE_ROOT)
MONOREPO_ROOT = os.path.dirname(TEST_ROOT)

# =============================================================================
# DOMAIN IDENTITY
# =============================================================================

DOMAIN_NAME = "build_stream"

ENV_OMNIA_DATA_PATH = "OMNIA_DATA_PATH"
ENV_OMNIA_PROJECT_NAME = "OMNIA_PROJECT_NAME"

# =============================================================================
# PLAYBOOK CONFIGURATION
# =============================================================================

PLAYBOOK_ENTRY_POINT = "build_stream.yml"
PLAYBOOK_WORKDIR = "src/build_stream/playbooks"

PLAYBOOK_TAGS: List[str] = [
    "gitlab_install",
    "gitlab_cleanup",
]

# =============================================================================
# BUILD STREAM API (BSM)
# =============================================================================

BSM_HEALTH_PATH = "/health"
BSM_API_VERSION = "v1"
BSM_AUTH_TOKEN_PATH = "/api/v1/auth/token"

# Keys read from build_stream_config.yml on the target host
BSM_HOST_IP_KEY = "build_stream_host_ip"
BSM_PORT_KEY = "build_stream_port"

# =============================================================================
# BUILDSTREAM CONTAINERS
# =============================================================================

BSM_CONTAINER_NAME = "omnia_build_stream"
POSTGRES_CONTAINER_NAME = "omnia_postgres"
BSM_CONTAINERS: List[str] = [
    BSM_CONTAINER_NAME,
    POSTGRES_CONTAINER_NAME,
]

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

POSTGRES_DB_NAME = "build_stream_db"
POSTGRES_USER = "admin"

EXPECTED_TABLES: List[str] = [
    "alembic_version",
    "artifact_metadata",
    "audit_events",
    "idempotency_keys",
    "image_groups",
    "images",
    "job_stages",
    "jobs",
]

# =============================================================================
# PLAYBOOK PATHS REGISTRY (2.3 domain-segregated)
# =============================================================================

PLAYBOOK_PATHS_YML = "src/build_stream/app/playbook_paths.yml"

EXPECTED_PLAYBOOK_ENTRIES: List[str] = [
    "repo_manager.yml",
    "image_build_manager.yml",
]

# =============================================================================
# SHARED VENV (2.3 — no omnia_core container)
# =============================================================================

OMNIA_VENV_PATH_DEFAULT = "/opt/omnia/venv"

# =============================================================================
# NFS / PLAYBOOK WATCHER
# =============================================================================

NFS_QUEUE_DIR_DEFAULT = "/opt/omnia/build_stream_root/queue"
NFS_ARTIFACT_BASE_DEFAULT = "/opt/omnia/build_stream_root"

# =============================================================================
# GITLAB CONFIGURATION
# =============================================================================

GITLAB_API_VERSION = "v4"
GITLAB_ROOT_TOKEN_FILE = "/root/.gitlab_root_token"

GITLAB_RUNNER_CONTAINER = "gitlab-runner"

GITLAB_SERVICES: List[str] = [
    "puma",
    "sidekiq",
    "nginx",
    "postgresql",
    "redis",
    "gitaly",
    "gitlab-workhorse",
    "logrotate",
]

GITLAB_RUNNER_SERVICES: List[Dict[str, str]] = [
    {"name": "gitlab-runner.service", "description": "GitLab Runner Container"},
    {"name": "gitlab-runsvdir.service", "description": "GitLab Runit supervision"},
]

GITLAB_RB_PATH = "/etc/gitlab/gitlab.rb"

GITLAB_SUCCESS_HTTP_CODES: List[int] = [200, 302]

GITLAB_VISIBILITY_LEVELS: Dict[str, str] = {
    "private": "0",
    "internal": "10",
    "public": "20",
}

GITLAB_INSTALLED_PACKAGES: List[str] = [
    "gitlab-ce",
]

GITLAB_CLEANUP_DIRECTORIES: List[str] = [
    "/etc/gitlab",
    "/var/opt/gitlab",
    "/var/log/gitlab",
    "/opt/gitlab",
]

GITLAB_RUNNER_QUADLET_DIR = "/etc/containers/systemd"
GITLAB_RUNNER_QUADLET_FILE = "gitlab-runner.container"

GITLAB_CI_PIPELINE_FILE = ".gitlab-ci.yml"

# 2.3 pipeline files
GITLAB_CI_BUILD_FILE = ".gitlab-ci-build.yml"
GITLAB_CI_DEPLOY_FILE = ".gitlab-ci-deploy.yml"
GITLAB_CI_CLEANUP_FILE = ".gitlab-ci-cleanup.yml"
GITLAB_CI_DEPLOY_CHILD_TEMPLATE = ".gitlab-ci-deploy-child-template.yml"
GITLAB_CI_CLEANUP_CHILD_TEMPLATE = ".gitlab-ci-cleanup-child-template.yml"

GITLAB_CI_ALL_FILES: List[str] = [
    GITLAB_CI_PIPELINE_FILE,
    GITLAB_CI_BUILD_FILE,
    GITLAB_CI_DEPLOY_FILE,
    GITLAB_CI_CLEANUP_FILE,
    GITLAB_CI_DEPLOY_CHILD_TEMPLATE,
    GITLAB_CI_CLEANUP_CHILD_TEMPLATE,
]

# Pipeline variables stored as GitLab CI/CD project variables
GITLAB_PIPELINE_VARIABLES: List[str] = [
    "GITLAB_API_TOKEN",
    "BSM_API_URL",
    "BSM_API_CERT",
]

GITLAB_RAILS_CMD_PROJECT_ID = (
    'gitlab-rails runner "puts Project.find_by(name: '
    '\\\"{project_name}\\\")&.id" 2>/dev/null'
)
GITLAB_RAILS_CMD_PROJECT_VISIBILITY = (
    'gitlab-rails runner "puts Project.find_by(name: '
    '\\\"{project_name}\\\")&.visibility_level" 2>/dev/null'
)
GITLAB_RAILS_CMD_PROJECT_DEFAULT_BRANCH = (
    'gitlab-rails runner "puts Project.find_by(name: '
    '\\\"{project_name}\\\")&.default_branch" 2>/dev/null'
)

# =============================================================================
# BUILD STREAM CONFIG FILE PATH
# =============================================================================

BUILD_STREAM_CONFIG_FILE = "build_stream_config.yml"

# =============================================================================
# SHELL COMMANDS — all commands MUST be in this dict.
# =============================================================================
CMDS: Dict[str, str] = {
    # --- Files ---
    "file_exists": "test -f {path} && echo exists",
    "dir_exists": "test -d {path} && echo exists",
    "cat_file": "cat {path} 2>/dev/null",
    "file_stat": "stat -c '%A %U:%G %s %n' {path} 2>/dev/null",

    # --- Podman ---
    "podman_ps_check": (
        "podman ps --format '{{{{.Names}}}} {{{{.Status}}}}'"
        " --filter name=^{container}$ 2>/dev/null"
    ),
    "podman_ps_all": (
        "podman ps -a --format '{{{{.Names}}}} {{{{.Status}}}}'"
        " --filter name=^{container}$ 2>/dev/null"
    ),

    # --- SystemD ---
    "systemctl_is_active": "systemctl is-active {service} 2>/dev/null",

    # --- Database ---
    "psql_list_tables": (
        "podman exec {container} psql -U {user} -d {db}"
        " -t -c \"SELECT tablename FROM pg_tables"
        " WHERE schemaname='public'\" 2>/dev/null"
    ),

    # --- Curl / API ---
    "curl_health": (
        "curl -sk -o /dev/null -w '%{{http_code}}'"
        " https://{host}:{port}{path} 2>/dev/null"
    ),
    "curl_health_body": (
        "curl -sk https://{host}:{port}{path} 2>/dev/null"
    ),
    "curl_gitlab_url": (
        "curl -k -s -o /dev/null -w '%{{http_code}}'"
        " 'https://{host}:{port}/' 2>/dev/null"
    ),

    # --- SSH to GitLab ---
    "ssh_to_gitlab": (
        "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10"
        " -o BatchMode=yes"
        " root@{gitlab_host} '{cmd}' 2>/dev/null"
    ),
    "sshpass_to_gitlab": (
        "sshpass -p '{password}'"
        " ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10"
        " root@{gitlab_host} '{cmd}' 2>/dev/null"
    ),

    # --- GitLab rails commands ---
    "gitlab_rails_project_id": GITLAB_RAILS_CMD_PROJECT_ID,
    "gitlab_rails_project_visibility": GITLAB_RAILS_CMD_PROJECT_VISIBILITY,
    "gitlab_rails_project_default_branch": GITLAB_RAILS_CMD_PROJECT_DEFAULT_BRANCH,

    # --- GitLab API ---
    "gitlab_api_file_exists": (
        "curl -sk --header 'PRIVATE-TOKEN: {token}'"
        " '{api_url}/projects/{project_id}/repository/files/"
        "{file_path}/raw?ref={branch}'"
        " -o /dev/null -w '%{{http_code}}' 2>/dev/null"
    ),
    "gitlab_api_list_variables": (
        "curl -sk --header 'PRIVATE-TOKEN: {token}'"
        " '{api_url}/projects/{project_id}/variables' 2>/dev/null"
    ),
    "gitlab_api_tree": (
        "curl -sk --header 'PRIVATE-TOKEN: {token}'"
        " '{api_url}/projects/{project_id}/repository/tree"
        "?path={dir_path}&ref={branch}' 2>/dev/null"
    ),

    # --- System ---
    "hostname_cmd": "hostname 2>/dev/null",
    "nproc_cmd": "nproc 2>/dev/null",
    "free_cmd": "free -g 2>/dev/null",
    "df_cmd": "df -BG / 2>/dev/null",
    "rpm_check": "rpm -q {package} 2>/dev/null",

    # --- GitLab config ---
    "grep_gitlab_rb": "grep {pattern} {path} 2>/dev/null",

    # --- Playbook paths ---
    "yaml_parse_playbook_paths": (
        "python3 -c \""
        "import yaml; data=yaml.safe_load(open('{path}'));"
        "print(list(data.get('playbook_paths',{{}}).keys()))"
        "\" 2>/dev/null"
    ),

    # --- OpenSSL ---
    "openssl_verify_cert": (
        "openssl x509 -in {cert_path} -noout -dates 2>/dev/null"
    ),

    # --- Venv ---
    "venv_ansible_playbook": (
        "test -f {venv_path}/bin/ansible-playbook && echo exists"
    ),
}
