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
import tempfile
# =============================================================================
# DIRECTORY PATHS
# =============================================================================

# Module root: test/ directory (where conftest.py lives)
MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))

# Repository root: omnia monorepo
# From vars/ -> library/ -> test/ -> repo root
REPO_ROOT = os.path.dirname(MODULE_ROOT)

# =============================================================================
# DOMAIN IDENTITY
# =============================================================================

# Domain name used for remote path resolution
DOMAIN_NAME = "build_stream"

# Environment variable names on the target host
ENV_OMNIA_DATA_PATH = "OMNIA_DATA_PATH"
ENV_OMNIA_PROJECT_NAME = "OMNIA_PROJECT_NAME"

# =============================================================================
# INPUT FILE NAMES
# =============================================================================

# Domain config file (inside the domain input directory)
BS_CONFIG_FILE = "build_stream_config.yml"

# =============================================================================
# PLAYBOOK CONFIGURATION (module-specific)
# =============================================================================

# Playbook entry point (relative to playbooks/)
PLAYBOOK_ENTRY_POINT = "build_stream.yml"
PLAYBOOK_WORKDIR = "src/build_stream/playbooks"

# Valid playbook tags
PLAYBOOK_TAGS = [
    "prepare",
    "build",
    "execute",
    "cleanup",
]

# =============================================================================
# SHARED PATH DEFAULTS (runtime output on target host)
# =============================================================================

SHARED_PATH = "/opt/omnia/build_stream"

# =============================================================================
# CONTAINER NAMES
# =============================================================================

BSM_CONTAINER = "omnia_build_stream"
POSTGRES_CONTAINER = "omnia_postgres"
GITLAB_CONTAINER = "gitlab"
GITLAB_RUNNER_CONTAINER = "gitlab-runner"

# =============================================================================
# SERVICE / PORT CONSTANTS
# =============================================================================

# Build Stream API port
BSM_API_PORT = 8010

# GitLab HTTP port
GITLAB_HTTP_PORT = 80
GITLAB_HTTPS_PORT = 443

# PostgreSQL port
POSTGRES_PORT = 5432

# Listening ports to verify after prepare (BSM API and PostgreSQL only)
# GitLab (port 80) is deployed in build phase, not prepare
LISTENING_PORTS = [8010, 5432]

# Systemd services created by prepare (if any)
SYSTEMD_SERVICES = []

# Build status output path template
BUILD_STATUS_PATH = (
    "{shared_path}/output/{project}/build_stream_status.yml"
)

# PostgreSQL database name
POSTGRES_DB = "build_stream_db"

# Expected PostgreSQL tables (actual schema from BSM database)
EXPECTED_POSTGRES_TABLES = [
    "jobs",
    "job_stages",
    "image_groups",
    "images",
    "alembic_version",
    "artifact_metadata",
    "audit_events",
    "idempotency_keys",
]

# =============================================================================
# API ENDPOINTS
# =============================================================================

BSM_HEALTH_ENDPOINT = "/health"

# =============================================================================
# PIPELINE STAGES (from GitLab CI/CD)
# =============================================================================

STAGE_PARSE_CATALOG = "parse-catalog"
STAGE_GENERATE_INPUT = "generate-input"
STAGE_CREATE_LOCAL_REPO = "create-local-repo"
STAGE_BUILD_IMAGE_X86_64 = "build-image-x86_64"
STAGE_BUILD_IMAGE_AARCH64 = "build-image-aarch64"
STAGE_VALIDATE_IMAGE = "validate-image"

BUILD_PIPELINE_CORE_STAGES = [
    "upload",
    STAGE_PARSE_CATALOG,
    STAGE_GENERATE_INPUT,
    STAGE_CREATE_LOCAL_REPO,
]

BUILD_IMAGE_STAGE_PREFIX = "build-image-"

BUILD_PIPELINE_STAGES = [
    "upload",
    STAGE_PARSE_CATALOG,
    STAGE_GENERATE_INPUT,
    STAGE_CREATE_LOCAL_REPO,
    STAGE_BUILD_IMAGE_X86_64,
    STAGE_BUILD_IMAGE_AARCH64,
]

DEPLOY_PIPELINE_STAGES = [
    "deploy",
    "restart",
    STAGE_VALIDATE_IMAGE,
]

CLEANUP_PIPELINE_STAGES = [
    "cleanup",
]

# =============================================================================
# IMAGE GROUP STATUSES
# =============================================================================

IMAGE_GROUP_STATUS_BUILT = "BUILT"
IMAGE_GROUP_STATUS_CLEANED = "CLEANED"

# =============================================================================
# REGISTRY AND S3 CONFIGURATION
# =============================================================================

REGISTRY_PORT = 5000
REGISTRY_CATALOG_PATH = "/v2/_catalog"
REGISTRY_IMAGE_PREFIX = "rhel-"

S3_BOOT_IMAGES_BUCKET = "s3://boot-images/"
S3_EFI_IMAGES_PREFIX = "s3://boot-images/efi-images/"
BOOT_IMAGE_ARTIFACTS_PER_ROLE = 3

# =============================================================================
# STRESS TEST CONFIGURATION
# =============================================================================

STRESS_BUILD_PIPELINE_COUNT = 50
STRESS_STOP_ON_FIRST_FAILURE = True

# =============================================================================
# JOB STATES (from build_stream_db.jobs)
# =============================================================================

JOB_STATE_PENDING = "PENDING"
JOB_STATE_IN_PROGRESS = "IN_PROGRESS"
JOB_STATE_COMPLETED = "COMPLETED"
JOB_STATE_FAILED = "FAILED"

# =============================================================================
# STAGE STATES (from build_stream_db.job_stages)
# =============================================================================

STAGE_STATE_PENDING = "PENDING"
STAGE_STATE_RUNNING = "RUNNING"
STAGE_STATE_COMPLETED = "COMPLETED"
STAGE_STATE_FAILED = "FAILED"

# =============================================================================
# POLLING CONFIGURATION
# =============================================================================

STAGE_POLL_INTERVAL = 30
STAGE_POLL_TIMEOUT = 10800  # 3 hours
PIPELINE_POLL_INTERVAL = 5
PIPELINE_POLL_TIMEOUT = 180  # 3 minutes
JOB_WAIT_TIMEOUT = 120
CLEANUP_WAIT_TIMEOUT = 300

# =============================================================================
# GITLAB API CONFIGURATION
# =============================================================================

GITLAB_API_VERSION = "v4"
GITLAB_ROOT_TOKEN_FILE = "/root/.gitlab_root_token"
CATALOG_FILE_PATH = "catalog_rhel.json"
CATALOG_DEFAULT_FILENAME = "catalog_rhel_x86_64_with_slurm_only.json"
PXE_MAPPING_FILE_PATH = "input/pxe_mapping_file.csv"
OMNIA_CATALOG_PATH = "/omnia/examples/catalog"

# =============================================================================
# OMNIA REPOSITORY AND CONFIGURATION PATHS
# =============================================================================

OMNIA_REPO_URL = "https://github.com/dell/omnia.git"
DEFAULT_CLONE_PATH = tempfile.NamedTemporaryFile(delete=False).name
SOURCE_CONFIG_BASE = "input/config"

# =============================================================================
# GITLAB CI/CD VARIABLE KEYS
# =============================================================================

PIPELINE_TYPE_KEY = "PIPELINE_TYPE"
PIPELINE_TYPE_BUILD = "build"
PIPELINE_TYPE_DEPLOY = "deploy"
PIPELINE_TYPE_CLEANUP = "cleanup"

# =============================================================================
# CONTAINER PATHS
# =============================================================================

INPUT_BASE_PATH = "/opt/omnia/input/project_default"
SOFTWARE_CONFIG_PATH = "/opt/omnia/input/project_default/software_config.json"
OMNIA_CORE_CONTAINER = "omnia_core"

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
    # --- Build Stream API ---
    "curl_health": (
        "curl -sk https://localhost:{port}{endpoint} 2>/dev/null"
    ),
    # --- PostgreSQL ---
    "psql_list_tables": (
        "podman exec -e PGPASSWORD={password} {container} psql -U poster1 -d {db}"
        " -t -c \"SELECT tablename FROM pg_tables"
        " WHERE schemaname='public';\" 2>/dev/null"
    ),
    # --- GitLab ---
    "curl_gitlab": (
        "curl -sk -o /dev/null -w '%{{http_code}}'"
        " http://localhost:{port}/ 2>/dev/null"
    ),
    # --- Files ---
    "file_exists": "test -f {path} && echo exists",
    "dir_exists": "test -d {path} && echo exists",
    "cat_file": "cat {path} 2>/dev/null",
    # --- Ansible / Playbook ---
    "ansible_playbook": (
        "cd {workdir} && ansible-playbook {playbook}"
        " --tags {tag} -v 2>&1"
    ),
    # --- System ---
    "hostname_cmd": "hostname 2>/dev/null",
    # --- Ports ---
    "ss_listen_port": (
        "ss -tlnp 'sport = :{port}' 2>/dev/null"
    ),
    # --- Git ---
    "git_remote_url": "git -C {path} remote get-url origin 2>/dev/null",
    "git_branch": "git -C {path} branch --show-current 2>/dev/null",
}
