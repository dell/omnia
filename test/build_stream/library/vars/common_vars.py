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
    "buildstream_install",
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

NFS_QUEUE_DIR_DEFAULT = "/opt/omnia/playbook_queue"
NFS_ARTIFACT_BASE_DEFAULT = "/opt/omnia/build_stream_root"

# =============================================================================
# TLS CERTIFICATE PATHS
# =============================================================================

BSM_TLS_CERT_PATH = "/opt/omnia/build_stream_ssl/ssl/bs_cert.pem"
BSM_TLS_KEY_PATH = "/opt/omnia/build_stream_ssl/ssl/bs_key.pem"

# =============================================================================
# SERVER CREDENTIALS (source of truth on target host)
# =============================================================================

BUILD_STREAM_CREDENTIALS_FILE = "build_stream_credentials.yml"
BUILD_STREAM_CREDENTIALS_KEY = ".build_stream_credentials_key"

# Required fields that must be present in build_stream_credentials.yml
BUILD_STREAM_REQUIRED_CREDS: List[str] = [
    "gitlab_root_password",
    "gitlab_ssh_password",
]

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
# BUILDSTREAM CLEANUP DIRECTORIES (from cleanup_build_stream role vars)
# =============================================================================

QUADLET_DIR = "/etc/containers/systemd"
OMNIA_TARGET_PATH = "/etc/systemd/system/omnia.target"
PLAYBOOK_WATCHER_SERVICE_FILE = "/etc/systemd/system/playbook_watcher.service"
PLAYBOOK_WATCHER_SERVICE_NAME = "playbook_watcher.service"

# Directories removed during build_stream cleanup
BUILDSTREAM_CLEANUP_DIRECTORIES: List[str] = [
    "/opt/omnia/build_stream/log",
    "/opt/omnia/build_stream/playbook_queue",
    "/opt/omnia/build_stream_ssl",
    "/opt/omnia/build_stream_root",
    "/opt/omnia/build_stream_inv",
    "/opt/omnia/build_stream_enabled",
    "/opt/omnia/build_stream",
]

# Credential files removed during cleanup
BUILDSTREAM_CREDENTIAL_FILES: List[str] = [
    "build_stream_credentials.yml",
    ".build_stream_credentials_key",
]

BUILDSTREAM_OAUTH_CREDENTIAL_FILES: List[str] = [
    "build_stream_oauth_credentials.yml",
    ".build_stream_oauth_credentials_key",
]

# =============================================================================
# BUILD PIPELINE STAGES (2.3 domain-segregated)
# =============================================================================

# Stage names match the BSM StageType enum in
# src/build_stream/app/core/jobs/value_objects.py
STAGE_CREATE_LOCAL_REPO = "create-local-repository"
STAGE_BUILD_IMAGE = "build-image"
STAGE_VALIDATE = "validate"
STAGE_RESTART = "restart"
STAGE_UPLOAD = "upload"
STAGE_DEPLOY = "deploy"

BUILD_PIPELINE_STAGES: List[str] = [
    STAGE_CREATE_LOCAL_REPO,
    STAGE_BUILD_IMAGE,
]

# Stages that belong to the BUILD pipeline only
# (excludes deploy-pipeline stages: deploy, restart, validate)
BUILD_PIPELINE_ONLY_STAGES: List[str] = [
    STAGE_UPLOAD,
    STAGE_CREATE_LOCAL_REPO,
    STAGE_BUILD_IMAGE,
]

# GitLab CI/CD stage names (from .gitlab-ci-build.yml)
# These are the stages in the child build pipeline, not BSM database stages.
GITLAB_CI_BUILD_STAGES: List[str] = [
    "initialization",
    "copy-input-files",
    "configure-local-repository",
    "build-images",
    "summary",
]

# =============================================================================
# STAGE AND JOB STATES (from build_stream_db)
# =============================================================================

STAGE_STATE_PENDING = "PENDING"
STAGE_STATE_RUNNING = "RUNNING"
STAGE_STATE_COMPLETED = "COMPLETED"
STAGE_STATE_FAILED = "FAILED"

JOB_STATE_PENDING = "PENDING"
JOB_STATE_IN_PROGRESS = "IN_PROGRESS"
JOB_STATE_COMPLETED = "COMPLETED"
JOB_STATE_FAILED = "FAILED"

# =============================================================================
# IMAGE GROUP STATES
# =============================================================================

IMAGE_GROUP_STATUS_BUILT = "BUILT"
IMAGE_GROUP_STATUS_CLEANED = "CLEANED"

# =============================================================================
# PIPELINE TRIGGER VARIABLES
# =============================================================================

PIPELINE_TYPE_KEY = "PIPELINE_TYPE"
PIPELINE_TYPE_BUILD = "build"
PIPELINE_TYPE_DEPLOY = "deploy"
PIPELINE_TYPE_CLEANUP = "cleanup"

# Catalog file path in GitLab repo (2.3)
CATALOG_FILE_PATH = "catalog_rhel.json"
CATALOG_DEFAULT_FILENAME = "catalog_rhel_x86_64_with_slurm_only.json"

# =============================================================================
# POLLING CONFIGURATION
# =============================================================================

STAGE_POLL_INTERVAL: int = 30
STAGE_POLL_TIMEOUT: int = 10800   # 3 hours
PIPELINE_POLL_INTERVAL: int = 5
PIPELINE_POLL_TIMEOUT: int = 180  # 3 minutes
JOB_WAIT_TIMEOUT: int = 120

# =============================================================================
# REGISTRY AND S3 CONFIGURATION
# =============================================================================

REGISTRY_PORT: int = 5000
REGISTRY_IMAGE_PREFIX = "rhel-"
S3_BOOT_IMAGES_BUCKET = "s3://boot-images/"
S3_EFI_IMAGES_PREFIX = "s3://boot-images/efi-images/"
BOOT_IMAGE_ARTIFACTS_PER_ROLE: int = 3

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

    # --- Cleanup verification ---
    "podman_container_exists": (
        "podman ps -a --format '{{{{.Names}}}}'"
        " --filter name=^{container}$ 2>/dev/null"
    ),
    "systemctl_is_enabled": (
        "systemctl is-enabled {service} 2>/dev/null"
    ),
    "ss_port_check": (
        "ss -tlnp 2>/dev/null | grep ':{port}' || true"
    ),
    "podman_volume_ls": (
        "podman volume ls --format '{{{{.Name}}}}' 2>/dev/null"
        " | grep {pattern} || true"
    ),
    "find_quadlet_files": (
        "find {dir} -name '{pattern}*' -type f 2>/dev/null || true"
    ),
    "systemctl_list_units": (
        "systemctl list-units --type=service --all"
        " --no-legend 2>/dev/null"
        " | grep {pattern} || true"
    ),

    # --- GitLab Pipeline API ---
    "gitlab_api_list_pipelines": (
        "curl -sk --header 'PRIVATE-TOKEN: {token}'"
        " '{api_url}/projects/{project_id}/pipelines"
        "?per_page={per_page}' 2>/dev/null"
    ),
    "gitlab_api_pipeline_status": (
        "curl -sk --header 'PRIVATE-TOKEN: {token}'"
        " '{api_url}/projects/{project_id}/pipelines/{pipeline_id}'"
        " 2>/dev/null"
    ),
    "gitlab_api_pipeline_jobs": (
        "curl -sk --header 'PRIVATE-TOKEN: {token}'"
        " '{api_url}/projects/{project_id}/pipelines/{pipeline_id}/jobs'"
        " 2>/dev/null"
    ),
    "gitlab_api_pipeline_bridges": (
        "curl -sk --header 'PRIVATE-TOKEN: {token}'"
        " '{api_url}/projects/{project_id}/pipelines/{pipeline_id}/bridges'"
        " 2>/dev/null"
    ),
    "gitlab_api_cancel_pipeline": (
        "curl -sk -X POST --header 'PRIVATE-TOKEN: {token}'"
        " '{api_url}/projects/{project_id}/pipelines/{pipeline_id}/cancel'"
        " 2>/dev/null"
    ),
    "gitlab_api_trigger_pipeline": (
        "curl -sk -X POST --header 'PRIVATE-TOKEN: {token}'"
        " --header 'Content-Type: application/json'"
        " -d '{json_data}'"
        " '{api_url}/projects/{project_id}/pipeline'"
        " 2>/dev/null"
    ),
    "gitlab_api_update_file": (
        "curl -sk -X PUT --header 'PRIVATE-TOKEN: {token}'"
        " --header 'Content-Type: application/json'"
        " -d '{json_data}'"
        " '{api_url}/projects/{project_id}/repository/files/{file_path}'"
        " 2>/dev/null"
    ),
    "gitlab_api_get_file": (
        "curl -sk --header 'PRIVATE-TOKEN: {token}'"
        " '{api_url}/projects/{project_id}/repository/files/"
        "{file_path}?ref={branch}' 2>/dev/null"
    ),

    # --- Database (psql via podman) ---
    "psql_query": (
        "podman exec {container} psql -U {user} -d {db}"
        " -t -c \"{sql}\" 2>/dev/null"
    ),

    # --- BSM API ---
    "bsm_api_auth_token": (
        "curl -sk -X POST 'https://{host}:{port}/api/v1/auth/token'"
        " -H 'Content-Type: application/x-www-form-urlencoded'"
        " -d 'grant_type=client_credentials"
        "&client_id={client_id}&client_secret={client_secret}'"
        " 2>/dev/null"
    ),
    "bsm_api_get_job": (
        "curl -sk -H 'Authorization: Bearer {token}'"
        " 'https://{host}:{port}/api/v1/jobs/{job_id}' 2>/dev/null"
    ),
    "bsm_api_catalog_roles": (
        "curl -sk -H 'Authorization: Bearer {token}'"
        " 'https://{host}:{port}/api/v1/jobs/{job_id}/catalog/roles'"
        " 2>/dev/null"
    ),

    # --- Registry ---
    "regctl_repo_ls": (
        "regctl repo ls --limit 500 {registry_url} 2>/dev/null"
    ),

    # --- S3 ---
    "s3cmd_ls_recursive": (
        "s3cmd ls -r {bucket} 2>/dev/null"
    ),
    "s3cmd_ls_bucket": (
        "s3cmd ls {bucket} 2>/dev/null"
    ),

    # --- Vault decrypt ---
    "vault_decrypt_creds": (
        "ansible-vault decrypt --vault-password-file {key_path} "
        "--output - {creds_path} 2>/dev/null"
    ),

    # --- Registry catalog ---
    "curl_registry_catalog": (
        "curl -sk https://localhost:{port}/v2/_catalog 2>/dev/null"
        " || curl -sk http://localhost:{port}/v2/_catalog 2>/dev/null"
    ),
}
