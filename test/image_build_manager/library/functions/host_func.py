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
Image Build Manager — Module-specific host utilities (monorepo).

Reads module config and passes ALL params to omnia_auto's
``clone_repo()`` and ``sync_files()``.  No logic in the package —
only in this consumer.

Monorepo changes vs multi-repo:
- Input path resolved from target env vars (OMNIA_DATA_PATH, OMNIA_PROJECT_NAME)
- sync_project_to_remote() copies local project code to target clone_path
- No separate config.yml sync (env vars replace it)

Common functions are re-exported from omnia_auto so existing
callers keep working.
"""

import os
from typing import Dict, Any

import yaml

from omnia_auto import (
    load_test_config,
    load_test_credentials,
    is_local_execution,
    get_module_root,
    get_setting,
    sync_files,
    log,
)


# Re-export common functions so existing callers keep working
from omnia_auto import (                          # noqa: F401
    get_testinfra_host,
    encrypt_test_credentials,
    run_on_host,
)


# =============================================================================
# INTERNAL: resolve mode + SSH params from config
# =============================================================================

def _connection_params() -> dict:
    """Build mode/ip/user/password/ssh_opts from test_config + creds."""
    config = load_test_config()
    creds = load_test_credentials()
    local = is_local_execution()

    return {
        "mode": "local" if local else "ssh",
        "ip": config.get("oim_server_ip", "").strip() or None,
        "user": config.get("oim_ssh_user", "root"),
        "password": creds.get("oim_password") or None,
        "ssh_opts": get_setting(
            "ssh_opts",
            "-o StrictHostKeyChecking=no "
            "-o UserKnownHostsFile=/dev/null "
            "-o LogLevel=ERROR",
        ),
    }


# =============================================================================
# INTERNAL: read env var from target host
# =============================================================================

def _read_remote_env(host, var_name: str, default: str = "") -> str:
    """Read an environment variable from the target host via testinfra.

    Args:
        host: Testinfra host object.
        var_name: Environment variable name (e.g. ``OMNIA_DATA_PATH``).
        default: Fallback if the variable is unset or empty.

    Returns:
        The env var value, stripped, or *default*.
    """
    result = host.run(f"echo ${{{var_name}}}")
    value = result.stdout.strip() if result.rc == 0 else ""
    return value or default


def _resolve_remote_input_path(host) -> str:
    """Build the remote input directory from target env vars.

    Reads ``OMNIA_DATA_PATH`` and ``OMNIA_PROJECT_NAME`` from the target
    and assembles::

        <OMNIA_DATA_PATH>/image_build_manager/input/<OMNIA_PROJECT_NAME>/

    Falls back to ``/opt/omnia`` and ``project_default`` respectively.
    """
    data_path = _read_remote_env(host, "OMNIA_DATA_PATH", "/opt/omnia")
    project = _read_remote_env(host, "OMNIA_PROJECT_NAME", "project_default")
    remote_input = f"{data_path}/image_build_manager/input/{project}"
    log(f"Resolved remote input path: {remote_input}", "INFO")
    return remote_input


# =============================================================================
# MODULE-SPECIFIC CLONE / SYNC
# =============================================================================

def sync_project_to_remote(host) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """Sync the local omnia project tree to clone_path on target.

    Copies the complete project from the local monorepo to the remote
    ``clone_path``, using the same rsync/SSH checks as other sync
    functions.  This replaces git-clone when the code is already
    available locally.

    Source: ``<repo_root>/`` (the omnia monorepo root)
    Dest:   ``<clone_path>/`` on the target server
    """
    config = load_test_config()
    conn = _connection_params()

    # Repo root: test/image_build_manager/ -> test/ -> omnia/
    repo_root = os.path.dirname(os.path.dirname(get_module_root()))

    return sync_files(
        mode=conn["mode"],
        src=repo_root,
        dest=config["clone_path"],
        ip=conn["ip"],
        user=conn["user"],
        password=conn["password"],
        ssh_opts=conn["ssh_opts"],
    )


def sync_image_build_input(host) -> Dict[str, Any]:
    """Push image_build input files from local dataset to target.

    Reads ``OMNIA_DATA_PATH`` and ``OMNIA_PROJECT_NAME`` from the target
    server's environment to resolve the correct destination::

        <OMNIA_DATA_PATH>/image_build_manager/input/<OMNIA_PROJECT_NAME>/

    Source: datasets/<dataset>/input/
    """
    config = load_test_config()
    conn = _connection_params()

    local_input = os.path.join(
        get_module_root(), "datasets", config["dataset"], "input",
    )
    remote_input = _resolve_remote_input_path(host)

    return sync_files(
        mode=conn["mode"], src=local_input, dest=remote_input,
        ip=conn["ip"], user=conn["user"],
        password=conn["password"], ssh_opts=conn["ssh_opts"],
    )


def sync_repo_manager_output(host) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """Push repo_manager_output from dataset to target.

    Reads repo_manager_output_dir from image_build_config.yml in the
    dataset. Falls back to /opt/omnia/repo_manager/output/<project_name>/.
    """
    config = load_test_config()
    conn = _connection_params()
    dataset = config["dataset"]

    local_output = os.path.join(
        get_module_root(), "datasets", dataset, "repo_manager_output",
    )

    # Read repo_manager_output_dir from image_build_config.yml
    local_ibm_config = os.path.join(
        get_module_root(), "datasets", dataset, "input",
        "image_build_config.yml",
    )
    # Fallback: read project from target env or config
    project = config.get("project_name", "project_default")
    remote_output_dir = (
        f"/opt/omnia/repo_manager/output/{project}"
    )
    if os.path.isfile(local_ibm_config):
        try:
            with open(local_ibm_config, "r", encoding="utf-8") as fh:
                ibm_cfg = yaml.safe_load(fh) or {}
            configured_dir = ibm_cfg.get("repo_manager_output_dir", "")
            if configured_dir:
                remote_output_dir = configured_dir
        except (yaml.YAMLError, OSError):
            pass

    return sync_files(
        mode=conn["mode"], src=local_output, dest=remote_output_dir,
        ip=conn["ip"], user=conn["user"],
        password=conn["password"], ssh_opts=conn["ssh_opts"],
    )
