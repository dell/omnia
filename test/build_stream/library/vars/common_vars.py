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
import re
from typing import Dict, List

# =============================================================================
# DIRECTORY PATHS
# =============================================================================

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))

TEST_ROOT = os.path.dirname(MODULE_ROOT)
MONOREPO_ROOT = os.path.dirname(TEST_ROOT)
SRC_INPUT_DIR = os.path.join(
    MONOREPO_ROOT, "src", "build_stream", "input",
)

# =============================================================================
# DOMAIN IDENTITY
# =============================================================================

DOMAIN_NAME = "build_stream"

ENV_OMNIA_DATA_PATH = "OMNIA_DATA_PATH"
ENV_OMNIA_PROJECT_NAME = "OMNIA_PROJECT_NAME"
ENV_OMNIA_VENV_PATH = "OMNIA_VENV_PATH"

# =============================================================================
# PLAYBOOK CONFIGURATION
# =============================================================================

PLAYBOOK_ENTRY_POINT = "build_stream.yml"
PLAYBOOK_WORKDIR = "src/build_stream/playbooks"


# =============================================================================
# CONFIG VALIDATION
# =============================================================================

IPV4_PATTERN = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)

REQUIRED_CONFIG_FIELDS = [
    "dataset",
    "sync_build_stream_input",
    "report_path",
    "report_name",
]

# test_config.yml keys that must be unquoted true/false.
BOOLEAN_CONFIG_FIELDS = (
    "sync_build_stream_input",
    "nft_allow_pipeline_cancel",
    "nft_allow_service_restart",
    "nft_allow_active_stage_restart",
    "nft_allow_watcher_restart",
    "nft_allow_security_mutation",
)

REQUIRED_DATASET_FILES = ["input/build_stream_config.yml"]
REQUIRED_SRC_FILES = ["build_stream_config.yml"]

# =============================================================================
# BUILD STREAM API (BSM)
# =============================================================================

BSM_HEALTH_PATH = "/health"

# Keys read from build_stream_config.yml on the target host
BSM_HOST_IP_KEY = "build_stream_host_ip"
BSM_PORT_KEY = "build_stream_port"

# =============================================================================
# BUILDSTREAM CONTAINERS
# =============================================================================

BSM_CONTAINER_NAME = "omnia_build_stream"
POSTGRES_CONTAINER_NAME = "omnia_postgres"
# Postgres data directory under OMNIA_DATA_PATH (cleanup_build_stream
# postgres_cleanup_directory); deleted only with -e postgres_backup=false.
POSTGRES_DATA_DIR = "build_stream/postgres"
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


# =============================================================================
# SERVER CREDENTIALS (source of truth on target host)
# =============================================================================

BUILD_STREAM_CREDENTIALS_FILE = "build_stream_credentials.yml"
BUILD_STREAM_CREDENTIALS_KEY = ".build_stream_credentials_key"


# =============================================================================
# GITLAB CONFIGURATION
# =============================================================================

GITLAB_API_VERSION = "v4"
GITLAB_ROOT_TOKEN_FILE = "/root/.gitlab_root_token"
# Product contracts of build_stream.yml: the OIM -> GitLab SSH key
# (gitlab_passwordless_ssh ssh_key_path) and the GitLab CA on the GitLab host
# (hosted_gitlab gitlab_cert_dir/ca.crt).
GITLAB_SSH_KEY = "/root/.ssh/omnia_gitlab"
GITLAB_CA_CERT = "/root/gitlab-certs/ca.crt"
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
GITLAB_CI_CADENCE_FILE = ".gitlab-ci-cadence.yml"
GITLAB_CI_DEPLOY_CHILD_TEMPLATE = ".gitlab-ci-deploy-child-template.yml"
GITLAB_CI_CLEANUP_CHILD_TEMPLATE = ".gitlab-ci-cleanup-child-template.yml"


# Pipeline variables stored as GitLab CI/CD project variables
GITLAB_PIPELINE_VARIABLES: List[str] = [
    "GITLAB_API_TOKEN",
    "BSM_API_URL",
    "BSM_API_CERT",
]


# =============================================================================
# BUILD STREAM CONFIG FILE PATH
# =============================================================================

BUILD_STREAM_CONFIG_FILE = "build_stream_config.yml"

# =============================================================================
# BUILDSTREAM CLEANUP DIRECTORIES (from cleanup_build_stream role vars)
# =============================================================================

QUADLET_DIR = "/etc/containers/systemd"
PLAYBOOK_WATCHER_SERVICE_NAME = "playbook-watcher.service"
# Directories under OMNIA_DATA_PATH that build_stream.yml --tags prepare creates
# and --tags cleanup removes (deploy_bsm: build_stream_log_dir,
# build_stream_ssl_dir, build_stream_root_dir,
# build_stream_watcher_playbook_queue_base; cleanup_build_stream:
# build_stream_cleanup_directory).
BUILDSTREAM_SHARED_DIRECTORIES = (
    "build_stream/log",
    "build_stream/ssl",
    "build_stream/build_stream_root",
    "build_stream/playbook_queue",
)
# Prepare also creates the queue subdirectories (build_stream_queue_subdirs),
# the JWT keys directory (build_stream_jwt_keys_dir) and the Postgres data
# directory (postgres role: postgres_data_dir).
BUILDSTREAM_RUNTIME_DIRECTORIES = BUILDSTREAM_SHARED_DIRECTORIES + (
    "build_stream/build_stream_root/api/.auth/keys",
    "build_stream/playbook_queue/requests",
    "build_stream/playbook_queue/results",
    "build_stream/playbook_queue/processing",
    "build_stream/playbook_queue/archive",
    "build_stream/playbook_queue/archive/requests",
    "build_stream/playbook_queue/archive/results",
    f"{POSTGRES_DATA_DIR}/data",
)
# Cleanup removes the shared directories plus the extra log, output and legacy
# marker directories (cleanup_build_stream role: build_stream_cleanup_directory)
# and the host log directory it removes last (build_stream_host_log_directory).
# Postgres data is covered by its own flag-based check.
BUILDSTREAM_CLEANUP_DIRECTORIES = BUILDSTREAM_SHARED_DIRECTORIES + (
    "build_stream/logs",
    "build_stream/output",
    "log/build_stream",
    "build_stream/build_stream_inv",
    "build_stream/build_stream_enabled",
)
BUILDSTREAM_HOST_LOG_DIRECTORY = "/var/log/omnia/build_stream"
# Application file under the BuildStream data path that cleanup preserves.
BUILDSTREAM_WATCHER_SOURCE = "playbook-watcher/playbook_watcher_service.py"
PLAYBOOK_WATCHER_SERVICE_FILE = (
    f"/etc/systemd/system/{PLAYBOOK_WATCHER_SERVICE_NAME}"
)

# Credential files removed during cleanup
BUILDSTREAM_CREDENTIAL_FILES: List[str] = [
    "build_stream_credentials.yml",
    ".build_stream_credentials_key",
]

# =============================================================================
# BUILD PIPELINE STAGES (2.3 domain-segregated)
# =============================================================================


# =============================================================================
# STAGE AND JOB STATES (from build_stream_db)
# =============================================================================


# =============================================================================
# IMAGE GROUP STATES
# =============================================================================


# =============================================================================
# PIPELINE TRIGGER VARIABLES
# =============================================================================


# Catalog file path in GitLab repo (2.3)
CATALOG_FILE_PATH = "catalog_rhel.json"


# =============================================================================
# POLLING CONFIGURATION
# =============================================================================


# =============================================================================
# REGISTRY AND S3 CONFIGURATION
# =============================================================================

REGISTRY_PORT: int = 5000
S3_BOOT_IMAGES_BUCKET = "s3://boot-images/"

# =============================================================================
# PREPARE BASE (./omnia.sh --prepare-base: BuildStream prerequisites)
# =============================================================================

OMNIA_SH_WORKDIR = "src/main"
OMNIA_SH_FILE = "omnia.sh"
OMNIA_SH_PREPARE_BASE_ARGS = "--prepare-base"
PREPARE_BASE_DOMAINS: List[str] = [
    "repo_manager",
    "image_build_manager",
    "orchestrator",
]
PREPARE_BASE_REQUIRED_ENV_VARS: List[str] = [
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    ENV_OMNIA_VENV_PATH,
]
VENV_ACTIVATE_FILE = "bin/activate"
# omnia.sh --prepare-base runs until it finishes (no timeout).

# Credential store (file, vault key) each base domain playbook reads; a
# missing store makes omnia.sh prompt, which blocks an unattended run.
PREPARE_BASE_CREDENTIAL_FILES: Dict[str, List[str]] = {
    "repo_manager": [
        "repo_manager_config_credentials.yml",
        ".repo_manager_config_credentials_key",
    ],
    "image_build_manager": [
        "image_build_credentials.yml",
        ".image_build_credentials_key",
    ],
    "orchestrator": [
        "orchestrator_credentials.yml",
        ".orchestrator_credentials_key",
    ],
}

# Per-exec -> verify hand-off (exec and verify are separate pytest processes).
RUN_STATE_DIR = os.path.join(MODULE_ROOT, "reports", "state")
RUN_STATE_FILE = "{scenario}.json"
RUN_STATE_MODE = 0o600

# Base domain state verified after --prepare-base.
# repo_manager: Pulp
RM_PULP_CONTAINER = "pulp"
RM_PULP_SERVICE = "pulp.service"
RM_PULP_QUADLET = "/etc/containers/systemd/pulp.container"

# image_build_manager: MinIO and the image registry
IBM_CONTAINERS: List[str] = ["minio-server", "registry"]
IBM_SERVICES: List[str] = ["minio.service", "registry.service"]
IBM_PORTS: List[int] = [9000, 9001, 5000]

# orchestrator: OpenCHAMI, from the product's component specification
# (src/orchestrator/roles/cleanup/components/openchami/vars/component_spec.yml).
# One-shot units stay "active (exited)" after prepare.
ORCH_OPENCHAMI_UNITS: List[str] = [
    "openchami.target",
    "acme-deploy.service",
    "acme-register.service",
    "boot-service.service",
    "coresmd-coredhcp.service",
    "coresmd-coredns.service",
    "haproxy.service",
    "metadata-service.service",
    "openchami-cert-trust.service",
    "postgres.service",
    "smd-init.service",
    "smd.service",
    "step-ca.service",
    "tokensmith.service",
]
ORCH_OPENCHAMI_TIMER = "openchami-cert-renewal.timer"
ORCH_OPENCHAMI_CONTAINERS: List[str] = [
    "boot-service",
    "coresmd-coredhcp",
    "coresmd-coredns",
    "haproxy",
    "metadata-service",
    "postgres",
    "smd",
    "step-ca",
    "tokensmith",
]
ORCH_OPENCHAMI_VOLUMES: List[str] = [
    "boot-service-data",
    "metadata-service-data",
    "postgres-data",
    "haproxy-certs",
]
# OpenLDAP is deployed only when orchestrator_state.yml sets openldap_support.
ORCH_STATE_FILE = "output/{project}/orchestrator_state.yml"
ORCH_OPENLDAP_FLAG = "openldap_support"
ORCH_OPENLDAP_CONTAINER = "omnia_auth"
ORCH_OPENLDAP_SERVICE = "omnia_auth.service"
ORCH_OPENLDAP_QUADLET = "/etc/containers/systemd/omnia_auth.container"

# =============================================================================
# PRECHECK (build_stream.yml --tags precheck, role precheck_build_stream)
# =============================================================================

ENV_SYSTEM_HOSTNAME = "SYSTEM_HOSTNAME"
ENV_SYSTEM_DOMAIN_NAME = "SYSTEM_DOMAIN_NAME"
ENV_SYSTEM_ADMIN_IPV4 = "SYSTEM_ADMIN_NIC_IPV4"
PRECHECK_REQUIRED_ENV_VARS: List[str] = [
    ENV_SYSTEM_HOSTNAME,
    ENV_SYSTEM_DOMAIN_NAME,
    ENV_SYSTEM_ADMIN_IPV4,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
]
# Containers and credential stores the product precheck requires
# (src/build_stream/roles/precheck_build_stream/vars/main.yml).
PRECHECK_REQUIRED_CONTAINERS: List[str] = ["pulp", "minio-server", "registry"]
PRECHECK_REQUIRED_CREDENTIALS: Dict[str, str] = {
    "repo_manager": "repo_manager_config_credentials.yml",
    "image_build_manager": "image_build_credentials.yml",
}
NFS_NO_ROOT_SQUASH = "no_root_squash"
# Domain input files build_stream.yml --tags execute uploads to GitLab
# (src/build_stream/roles/hosted_gitlab/vars/main.yml gitlab_input_files);
# a missing file is skipped silently by the upload, so precheck requires all.
GITLAB_INPUT_REPO_DIR = "input"
GITLAB_UPLOADED_INPUT_FILES: Dict[str, List[str]] = {
    "repo_manager": [
        "repo_manager_config.yml",
        "repo_manager_endpoint_config.yml",
    ],
    "image_build_manager": [
        "image_build_config.yml",
        "package_groups.yml",
    ],
    "orchestrator": [
        "omnia_config.yml",
        "orchestrator_config.yml",
        "network_spec.yml",
        "security_config.yml",
        "storage_config.yml",
        "additional_cloud_init.yml",
        "pxe_mapping_file.csv",
        "set_pxe_boot_config.yml",
    ],
}

# =============================================================================
# PREPARE (build_stream.yml --tags prepare: Postgres, BSM, playbook-watcher)
# =============================================================================

PREPARE_QUADLETS: List[str] = [
    "/etc/containers/systemd/omnia_build_stream.container",
    "/etc/containers/systemd/omnia_postgres.container",
]
PREPARE_SERVICES: List[str] = [
    "omnia_postgres.service",
    "omnia_build_stream.service",
    "playbook-watcher.service",
]
BUILD_STREAM_STATUS_FILE = "build_stream_status.yml"
BUILD_STREAM_STATUS_PREPARED = "prepared"
BUILD_STREAM_STATUS_KEYS: List[str] = [
    "overall_status",
    "build_stream_host",
    "build_stream_port",
    "gitlab_host",
    "gitlab_url",
    "bsm_api_url",
]

# build_stream.yml tag runs (seconds).
TAG_PLAYBOOK_TIMEOUTS: Dict[str, int] = {
    "precheck": 900,
    "prepare": 3600,
    "execute": 3600,
    "cleanup": 1800,
}

# Result keys left out when a single-check result is rendered as fields.
RESULT_HIDDEN_KEYS = frozenset({"success", "error", "details"})
# List keys whose items are failures (printed with a cross, one per line).
RESULT_FAILED_ITEM_PREFIXES = ("still_", "missing", "failed", "not_")

# =============================================================================
# SHELL COMMANDS — all commands MUST be in this dict.
# =============================================================================
CMDS: Dict[str, str] = {
    "podman_volume_names": "podman volume ls --format '{{.Name}}' 2>/dev/null",
    # --- Files ---
    "path_exists": "test -e {path}",
    "file_exists": "test -f {path} && echo exists",
    "dir_exists": "test -d {path} && echo exists",
    "cat_file": "cat {path} 2>/dev/null",

    # --- Podman ---
    "podman_ps_all": (
        "podman ps -a --format '{{{{.Names}}}} {{{{.Status}}}}'"
        " --filter name=^{container}$ 2>/dev/null"
    ),

    # --- SystemD ---
    "systemctl_is_active": "systemctl is-active {service} 2>/dev/null",
    "systemctl_is_enabled": "systemctl is-enabled {service} 2>/dev/null",

    # --- Database ---
    "psql_list_tables": (
        "podman exec {container} psql -U {user} -d {db}"
        " -t -c \"SELECT tablename FROM pg_tables"
        " WHERE schemaname='public'\" 2>/dev/null"
    ),

    # --- SSH to GitLab (key and pinned host key set up by gitlab_passwordless_ssh) ---
    "ssh_to_gitlab_key": (
        "ssh -i {key} -o BatchMode=yes -o StrictHostKeyChecking=yes"
        " -o ConnectTimeout=10 {gitlab_user}@{gitlab_host} {cmd} 2>/dev/null"
    ),

    # --- System ---
    "nproc_cmd": "nproc 2>/dev/null",
    "free_cmd": "free -g 2>/dev/null",
    "df_cmd": "df -BG / 2>/dev/null",
    "rpm_check": "rpm -q {package} 2>/dev/null",

    # --- GitLab config ---
    "grep_gitlab_rb": "grep {pattern} {path} 2>/dev/null",

    # --- Playbook paths ---

    # --- OpenSSL ---
    "openssl_verify_cert": (
        "openssl x509 -in {cert_path} -noout -dates 2>/dev/null"
    ),

    # --- Venv ---
    "venv_ansible_playbook": (
        "test -f {venv_path}/bin/ansible-playbook && echo exists"
    ),

    # --- Cleanup verification ---
    # Run on the GitLab server through ssh_to_gitlab (no single quotes).
    "gitlab_container_names": 'podman ps -a --format "{{.Names}}" 2>/dev/null || true',
    "gitlab_ctl_status": "gitlab-ctl status 2>/dev/null",
    "gitlab_path_state": "test -e {path} && echo exists || echo absent",
    "ss_port_check": (
        "ss -tlnp 2>/dev/null | grep ':{port}' || true"
    ),
    "quadlet_files": "find {dir} -maxdepth 1 -type f -name {pattern} 2>/dev/null",
    "service_units": (
        "systemctl list-units --type=service --all --no-legend --plain {pattern} 2>/dev/null"
    ),
    "python_caches": (
        "find -P {path} \\( -type d \\( -name __pycache__ -o -name pycache \\)"
        " -o -type f \\( -name '*.pyc' -o -name '*.pyo' \\) \\) -print 2>/dev/null"
    ),

    # --- GitLab Pipeline API ---

    # --- Cadence validation artifacts ---

    # --- Database (psql via podman) ---

    # --- BSM API ---

    # --- Registry ---
    "regctl_repo_ls": (
        "regctl repo ls --limit 500 {registry_url} 2>/dev/null"
    ),

    # --- S3 ---

    # --- Vault decrypt ---
    "vault_decrypt_creds": (
        "set -a && . {env_file} && set +a && "
        "\"${{OMNIA_VENV_PATH:+$OMNIA_VENV_PATH/bin/}}ansible-vault\" decrypt "
        "--vault-password-file {key_path} --output - {creds_path} 2>/dev/null"
    ),

    # --- Prepare base ---
    "omnia_sh": "cd {workdir} && ./omnia.sh {arguments}",
    "podman_container_state": (
        "podman inspect --format '{{{{.State.Running}}}} "
        "{{{{if .State.Health}}}}{{{{.State.Health.Status}}}}{{{{end}}}}'"
        " {container} 2>/dev/null"
    ),
    "podman_volume_exists": "podman volume exists {volume}",
    "port_listening": "ss -Htln 'sport = :'{port}",

    # --- Precheck ---
    "hostname_short": "hostname -s 2>/dev/null",
    "hostname_domain": "hostname -d 2>/dev/null",
    "local_ipv4": "ip -o -4 address show scope global",
    "realpath": "realpath -e {path}",
    "nfs_exports": "exportfs -s 2>/dev/null",
    "path_fstype": "findmnt -n -o FSTYPE -T {path}",

    # --- Registry catalog ---
}
