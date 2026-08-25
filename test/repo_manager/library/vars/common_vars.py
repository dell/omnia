# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Test constants, paths and commands.
"""

from omnia_auto import load_test_config


# --- Playbook paths ---
PLAYBOOK_ENTRY_POINT = "repo_manager.yml"
PLAYBOOK_WORKDIR = "src/repo_manager/playbooks"


def _get_input_path() -> str:
    """Return the repo_manager input path for the configured project."""
    config = load_test_config()
    project = config.get("project_name", "project_default")
    return f"/opt/omnia/repo_manager/input/{project}"


def _get_output_path() -> str:
    """Return the repo_manager output path for the configured project."""
    config = load_test_config()
    project = config.get("project_name", "project_default")
    return f"/opt/omnia/repo_manager/output/{project}"


def _get_base_path() -> str:
    """Return the repo_manager base data path."""
    return "/opt/omnia/repo_manager"


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
PULP_CERTS_DIR = "/opt/omnia/repo_manager/pulp_config/settings/certs"
PULP_SYSTEMD_UNIT = "/etc/containers/systemd/pulp.container"
PULP_YUM_REPO_FILE = "/etc/yum.repos.d/pulp.repo"

# --- Commands ---
CMDS = {
    "file_exists": "test -f {path} && echo 'exists' || echo 'missing'",
    "dir_exists": "test -d {path} && echo 'exists' || echo 'missing'",
    "container_running": "podman container exists {name} && podman inspect --format='{{{{.State.Status}}}}' {name} || echo 'missing'",
    "pulp_status": "/usr/local/bin/pulp status",
    "pulp_version": "/usr/local/bin/pulp --version",
    "curl_endpoint": "curl -k -s -o /dev/null -w '%{{http_code}}' https://{ip}:{port}/pulp/api/v3/status/ || echo '000'",
    "list_repos": "/usr/local/bin/pulp rpm repository list --format json",
    "symlink_exists": "test -L {path} && echo 'exists' || echo 'missing'",
}
