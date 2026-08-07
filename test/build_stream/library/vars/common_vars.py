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
        "podman exec -e PGPASSWORD=Dell1234 {container} psql -U poster1 -d {db}"
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
