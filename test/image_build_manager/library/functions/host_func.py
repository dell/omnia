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

import base64
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
    connection_params,
    read_remote_env,
    ensure_remote_dir,
    resolve_domain_input_path,
    get_testinfra_host,
    encrypt_test_credentials,
    run_on_host,
)

# Declare public API — re-exports for consumer convenience
__all__ = [
    "load_test_config",
    "load_test_credentials",
    "is_local_execution",
    "get_module_root",
    "get_setting",
    "sync_files",
    "log",
    "connection_params",
    "read_remote_env",
    "ensure_remote_dir",
    "resolve_domain_input_path",
    "get_testinfra_host",
    "encrypt_test_credentials",
    "run_on_host",
    "sync_project_to_remote",
    "sync_image_build_input",
    "sync_repo_manager_output",
    "sync_build_credentials",
]

from ..vars.common_vars import (
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    IBM_CONFIG_FILE,
    CREDENTIALS_FILE_NAME,
    SRC_INPUT_DIR,
    SRC_REPO_OUTPUT_DIR,
)


# =============================================================================
# NOTE: connection_params, read_remote_env, ensure_remote_dir, and
#       resolve_domain_input_path are now in the omnia-auto pip package.
#       They are imported above and used directly.
# =============================================================================


# =============================================================================
# MODULE-SPECIFIC SYNC
# =============================================================================

def sync_project_to_remote(_host) -> Dict[str, Any]:
    """Sync the local omnia project tree to clone_path on target.

    Copies the complete project from the local monorepo to the remote
    ``clone_path``, using the same rsync/SSH checks as other sync
    functions.  This replaces git-clone when the code is already
    available locally.

    Source: ``<repo_root>/`` (the omnia monorepo root)
    Dest:   ``<clone_path>/`` on the target server
    """
    config = load_test_config()
    conn = connection_params()

    # Repo root: test/image_build_manager/ -> test/ -> omnia/
    repo_root = os.path.dirname(os.path.dirname(get_module_root()))

    return sync_files(
        mode=conn["mode"],
        src=repo_root,
        dest=config["clone_path"],
        ip=conn["ip"],
        user=conn["user"],
        auth_secret=conn["auth_secret"],
        ssh_opts=conn["ssh_opts"],
    )


def _resolve_input_dir(config):
    """Resolve local input directory from dataset or src/."""
    dataset = config.get("dataset", "")
    if dataset:
        return os.path.join(
            get_module_root(), "datasets", dataset, "input",
        )
    return SRC_INPUT_DIR


def _resolve_repo_output_dir(config):
    """Resolve local repo_manager_output directory from dataset or src/."""
    dataset = config.get("dataset", "")
    if dataset:
        return os.path.join(
            get_module_root(), "datasets", dataset,
            "repo_manager_output",
        )
    return SRC_REPO_OUTPUT_DIR


def sync_image_build_input(host) -> Dict[str, Any]:
    """Push image_build input files from local source to target.

    Reads ``OMNIA_DATA_PATH`` and ``OMNIA_PROJECT_NAME`` from the target
    server's environment to resolve the correct destination::

        <OMNIA_DATA_PATH>/image_build_manager/input/<OMNIA_PROJECT_NAME>/

    Source: src/image_build_manager/input/ (default) or
            datasets/<dataset>/input/ (when dataset is set).
    """
    config = load_test_config()
    conn = connection_params()

    local_input = _resolve_input_dir(config)
    remote_input = resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
    )
    ensure_remote_dir(host, remote_input)

    return sync_files(
        mode=conn["mode"], src=local_input, dest=remote_input,
        ip=conn["ip"], user=conn["user"],
        auth_secret=conn["auth_secret"], ssh_opts=conn["ssh_opts"],
    )


def sync_repo_manager_output(host) -> Dict[str, Any]:
    """Push repo_manager_output from local source to target.

    Reads repo_manager_output_dir from image_build_config.yml.
    Falls back to <OMNIA_DATA_PATH>/repo_manager/output/<project_name>/.

    Source: src/.../samples/repo_manager_output/ (default) or
            datasets/<dataset>/repo_manager_output/ (when dataset is set).
    """
    config = load_test_config()
    conn = connection_params()

    local_output = _resolve_repo_output_dir(config)

    # Read repo_manager_output_path from image_build_config.yml
    # The config has repo_manager_output_path pointing to repo_status.yml;
    # we need its parent directory.
    local_ibm_config = os.path.join(
        _resolve_input_dir(config), IBM_CONFIG_FILE,
    )
    # Derive from target env vars — no fallbacks
    data_path = read_remote_env(host, ENV_OMNIA_DATA_PATH)
    project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
    remote_output_dir = f"{data_path}/repo_manager/output/{project}"

    if os.path.isfile(local_ibm_config):
        try:
            with open(local_ibm_config, "r", encoding="utf-8") as fh:
                ibm_cfg = yaml.safe_load(fh) or {}
            configured_path = ibm_cfg.get("repo_manager_output_path", "")
            if configured_path:
                # repo_manager_output_path points to repo_status.yml
                # — use its parent directory as the sync destination
                remote_output_dir = os.path.dirname(configured_path)
        except (yaml.YAMLError, OSError):
            pass

    ensure_remote_dir(host, remote_output_dir)

    return sync_files(
        mode=conn["mode"], src=local_output, dest=remote_output_dir,
        ip=conn["ip"], user=conn["user"],
        auth_secret=conn["auth_secret"], ssh_opts=conn["ssh_opts"],
    )


# =============================================================================
# BUILD CREDENTIAL SYNC
# =============================================================================

# Fields in test_creds.yml that map to image_build_credentials.yml on the target
_BUILD_CRED_FIELDS = ["s3_access_id", "s3_secret_key", "aarch64_ssh_password"]


def sync_build_credentials(host) -> Dict[str, Any]:
    """Write S3 and aarch64 credentials from test_creds.yml to the target.

    Bridges the gap between the test framework's credential store
    (``test_creds.yml``) and the playbook's credential file
    (``image_build_credentials.yml``).

    Flow:
        1. Load ``test_creds.yml`` (decrypted via ``load_test_credentials``).
        2. Extract ``s3_access_id``, ``s3_secret_key``, ``aarch64_ssh_password``.
        3. If any field has a non-empty value, write them as **plaintext**
           YAML to ``<input_dir>/image_build_credentials.yml`` on the target.

    The file is written as plaintext intentionally.  The
    ``collect_build_credentials`` role detects non-vault files (Step 4b)
    and handles loading + encryption itself.  This avoids vault-key
    mismatch — the role creates/manages its own vault key at
    ``<input_dir>/.image_build_credentials_key``.

    The write uses base64 encoding over SSH so credential values
    containing quotes, backslashes, or special chars are transported
    without shell-escaping issues.

    If no build credential fields are populated (all empty strings), the
    function skips silently — the ``collect_build_credentials`` role will
    prompt interactively or use the default template values.

    Returns:
        Dict with 'success', 'details', 'error' keys.
    """
    try:
        creds = load_test_credentials()
    except (ValueError, OSError) as exc:
        return {
            "success": False,
            "details": "",
            "error": f"Cannot load test_creds.yml: {exc}",
        }

    # Extract build-specific fields
    build_creds = {k: creds.get(k, "") for k in _BUILD_CRED_FIELDS}

    # Check if build credential fields have values
    has_values = any(v for v in build_creds.values())
    if not has_values:
        return {
            "success": True,
            "details": (
                "No build credentials in test_creds.yml — skipping sync. "
                "The collect_build_credentials role will prompt interactively "
                "for mandatory fields (s3_secret_key). To set credentials "
                "non-interactively, run: "
                "bash setup_env.sh --set-domain-creds"
            ),
            "error": "",
        }

    # Resolve target input path
    remote_input = resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
    )
    cred_file = f"{remote_input}/{CREDENTIALS_FILE_NAME}"

    # Build YAML content matching the template format
    yaml_content = (
        "---\n"
        "# Image build credentials (S3 / MinIO)\n"
        "# Auto-populated by test framework from test_creds.yml.\n"
        f's3_access_id: "{build_creds["s3_access_id"]}"\n'
        f's3_secret_key: "{build_creds["s3_secret_key"]}"\n'
        "\n"
        "# SSH password for ARM build host\n"
        f'aarch64_ssh_password: "{build_creds["aarch64_ssh_password"]}"\n'
    )

    # Base64-encode to avoid all shell quoting issues over SSH.
    # base64 output contains only [A-Za-z0-9+/=] — safe in any shell.
    b64 = base64.b64encode(yaml_content.encode("utf-8")).decode("ascii")

    # Ensure parent directory exists, write via base64 decode, set perms.
    # Leave as plaintext — the collect_build_credentials role (Step 4b)
    # detects non-vault files and handles encryption with its own key.
    write_cmd = (
        f"mkdir -p {remote_input} && "
        f"echo '{b64}' | base64 -d > {cred_file} && "
        f"chmod 600 {cred_file}"
    )
    result = run_on_host(host, write_cmd)
    if result.rc != 0:
        return {
            "success": False,
            "details": "",
            "error": f"Failed to write {cred_file}: {result.stderr}",
        }

    # Verify the file was written with actual values (not empty)
    verify_cmd = f"grep -c 's3_secret_key' {cred_file}"
    verify = run_on_host(host, verify_cmd)
    if verify.rc != 0:
        return {
            "success": False,
            "details": "",
            "error": (
                f"Credential file written but verification failed. "
                f"Check {cred_file} on the target."
            ),
        }

    field_summary = ", ".join(
        f"{k}={'set' if build_creds[k] else 'empty'}"
        for k in _BUILD_CRED_FIELDS
    )

    return {
        "success": True,
        "details": (
            f"Build credentials synced to {cred_file} "
            f"(plaintext — role will encrypt on first run) "
            f"[{field_summary}]"
        ),
        "error": "",
    }
