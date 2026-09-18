# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Test constants, paths and commands.
"""

import os
import re
from typing import List


# --- Dataset and source paths ---
MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))
TEST_ROOT = os.path.dirname(MODULE_ROOT)
MONOREPO_ROOT = os.path.dirname(TEST_ROOT)
SRC_INPUT_DIR = os.path.join(MONOREPO_ROOT, "src", "repo_manager", "input")
DATASETS_DIR = os.path.join(MODULE_ROOT, "datasets")

DATASET_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
REQUIRED_DATASET_INPUT_FILES: List[str] = [
    "repo_manager_config.yml",
    "repo_manager_endpoint_config.yml",
]


# --- Playbook paths ---
PLAYBOOK_ENTRY_POINT = "repo_manager.yml"
PLAYBOOK_WORKDIR = "src/repo_manager/playbooks"


def _get_project_name() -> str:
    """Return the project name from the Omnia environment."""
    return os.environ.get("OMNIA_PROJECT_NAME", "project_default")


def _get_base_path() -> str:
    """Return the effective Repo Manager data root."""
    domain_path = os.environ.get("REPO_MANAGER_DATA_PATH", "")
    if domain_path:
        return domain_path.rstrip("/")
    data_path = os.environ.get("OMNIA_DATA_PATH", "")
    if data_path:
        return f"{data_path.rstrip('/')}/repo_manager"
    return "/opt/omnia/repo_manager"


def _get_input_path() -> str:
    """Return the repo_manager input path for the configured project."""
    return f"{_get_base_path()}/input/{_get_project_name()}"


def _get_output_path() -> str:
    """Return the repo_manager output path for the configured project."""
    return f"{_get_base_path()}/output/{_get_project_name()}"


def _get_pulp_certs_dir() -> str:
    """Return the Pulp certificates directory path."""
    return f"{_get_base_path()}/pulp_config/settings/certs"


def _get_log_path() -> str:
    """Return the repo_manager log path."""
    return f"{_get_base_path()}/log"


def _get_catalog_path() -> str:
    """Return the catalog file path selected for this validation run."""
    configured_path = os.environ.get("CATALOG_FILE_PATH", "").strip()
    if configured_path:
        return configured_path
    data_path = os.environ.get("OMNIA_DATA_PATH", "/opt/omnia")
    return f"{data_path.rstrip('/')}/catalog/catalog_rhel.json"


# --- Input/Output file names ---
INPUT_FILES = {
    "repo_manager_config": "repo_manager_config.yml",
    "repo_manager_endpoint_config": "repo_manager_endpoint_config.yml",
    "repo_manager_credentials": "repo_manager_config_credentials.yml",
}

OUTPUT_FILES = {
    "repo_status": "repo_status.yml",
    "status_csv": "status.csv",
}

# --- Pulp configuration ---
PULP_CONTAINER_NAME = "pulp"
PULP_PORT = "2225"
PULP_CLI_SYMLINK = "/usr/local/bin/pulp"
PULP_CERTS_DIR = None  # Set dynamically using shared_path
PULP_SYSTEMD_UNIT = "/etc/containers/systemd/pulp.container"
PULP_YUM_REPO_FILE = "/etc/yum.repos.d/pulp.repo"

# --- User registry configuration ---
USER_REGISTRY_TIMEOUT = 5  # Socket timeout in seconds for registry reachability checks

# --- Commands ---
CMDS = {
    "file_exists": "test -f {path} && echo 'exists' || echo 'missing'",
    "dir_exists": "test -d {path} && echo 'exists' || echo 'missing'",
    "container_running": (
        "podman container exists {name} && podman inspect "
        "--format='{{{{.State.Status}}}}' {name} || echo 'missing'"
    ),
    "pulp_status": "/usr/local/bin/pulp status",
    "pulp_version": "/usr/local/bin/pulp --version",
    "curl_endpoint": (
        "curl -k -s -o /dev/null -w '%{{http_code}}' "
        "https://{ip}:{port}/pulp/api/v3/status/ || echo '000'"
    ),
    "list_repos": "/usr/local/bin/pulp rpm repository list --format json",
    "symlink_exists": "test -L {path} && echo 'exists' || echo 'missing'",
}
