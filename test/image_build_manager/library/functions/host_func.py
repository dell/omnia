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

import hashlib
import os
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
import uuid
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
    "resolve_target_source_root",
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
    CREDENTIALS_KEY_NAME,
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

_LOCAL_CREDENTIAL_ARTIFACTS = (
    CREDENTIALS_FILE_NAME,
    CREDENTIALS_KEY_NAME,
)
_project_sync_ignore = shutil.ignore_patterns(
    ".git",
    ".agents",
    ".codex",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "*.pyc",
    ".venv",
    "venv",
    "active-venv",
    "test_creds.yml",
    "test_creds.yml.*",
    ".test_creds.key",
    ".test_creds.key.*",
    CREDENTIALS_FILE_NAME,
    f"{CREDENTIALS_FILE_NAME}.*",
    CREDENTIALS_KEY_NAME,
    f"{CREDENTIALS_KEY_NAME}.*",
)


def _link_or_copy(source: str, destination: str) -> str:
    """Hard-link staged project files when possible, otherwise copy them."""
    try:
        os.link(source, destination, follow_symlinks=False)
        return destination
    except OSError:
        return shutil.copy2(
            source, destination, follow_symlinks=False
        )


def _resolve_dataset_subdir(
    config: Dict[str, Any], subdirectory: str, fallback: str
) -> str:
    """Resolve one dataset subdirectory without allowing path traversal."""
    dataset = config.get("dataset", "")
    if not dataset:
        return fallback
    if not isinstance(dataset, str):
        raise ValueError("dataset must be a directory name string")
    if (
        dataset in {".", "..", "generator"}
        or os.path.isabs(dataset)
        or os.path.basename(dataset) != dataset
        or "\x00" in dataset
    ):
        raise ValueError(f"Unsafe dataset name: {dataset!r}")

    datasets_root = os.path.realpath(os.path.join(get_module_root(), "datasets"))
    dataset_path = os.path.join(datasets_root, dataset)
    if os.path.islink(dataset_path):
        raise ValueError(f"Dataset symlinks are not allowed: {dataset}")
    resolved_dataset = os.path.realpath(dataset_path)
    if os.path.dirname(resolved_dataset) != datasets_root:
        raise ValueError(f"Dataset escapes datasets directory: {dataset!r}")

    subdir_path = os.path.join(resolved_dataset, subdirectory)
    if os.path.islink(subdir_path):
        raise ValueError(
            f"Dataset subdirectory symlinks are not allowed: {dataset}/{subdirectory}"
        )
    resolved_subdir = os.path.realpath(subdir_path)
    if os.path.commonpath((resolved_dataset, resolved_subdir)) != resolved_dataset:
        raise ValueError(
            f"Dataset subdirectory escapes its dataset: {dataset}/{subdirectory}"
        )
    return resolved_subdir


def _is_credential_artifact(entry_name: str) -> bool:
    """Identify credential files, keys, and their common backup suffixes."""
    return any(
        entry_name == name or entry_name.startswith(f"{name}.")
        for name in _LOCAL_CREDENTIAL_ARTIFACTS
    )


def _reject_symlinks(directory: str) -> None:
    """Reject nested links before copying a dataset tree into staging."""
    for current_dir, directory_names, file_names in os.walk(directory):
        for entry_name in directory_names + file_names:
            if os.path.islink(os.path.join(current_dir, entry_name)):
                raise OSError(
                    f"Refusing to sync symlink from dataset: "
                    f"{os.path.join(current_dir, entry_name)}"
                )


def resolve_target_source_root() -> str:
    """Resolve the Omnia source root for the current execution target.

    Local execution reads directly from the current checkout.  Remote
    execution reads from ``clone_path``, where the checkout is synced on the
    target server.  This mirrors the path selection used by the shared
    ``omnia_auto`` playbook runner.

    Returns:
        Absolute source-root path on the execution target.

    Raises:
        ValueError: If remote execution is selected without ``clone_path``.
    """
    if is_local_execution():
        # Module root: test/image_build_manager/ -> repo root: omnia/
        return os.path.dirname(os.path.dirname(get_module_root()))

    config = load_test_config()
    raw_clone_path = config.get("clone_path")
    if not isinstance(raw_clone_path, str) or not raw_clone_path.strip():
        raise ValueError(
            "clone_path must be set in test_config.yml for remote execution"
        )
    clone_path = raw_clone_path.strip()
    if not os.path.isabs(clone_path):
        raise ValueError(
            f"clone_path must be absolute for remote execution: {clone_path}"
        )
    return os.path.normpath(clone_path)


def sync_project_to_remote(_host) -> Dict[str, Any]:
    """Sync the local omnia project tree to clone_path on target.

    Copies a filtered working tree from the local monorepo to the remote
    ``clone_path``, using the same rsync/SSH checks as other sync functions.
    Local credential files, vault keys, VCS metadata, virtual environments,
    and caches are excluded. This replaces git-clone when the code is already
    available locally.

    Source: ``<repo_root>/`` (the omnia monorepo root)
    Dest:   ``<clone_path>/`` on the target server
    """
    config = load_test_config()
    conn = connection_params()

    # Repo root: test/image_build_manager/ -> test/ -> omnia/
    repo_root = os.path.dirname(os.path.dirname(get_module_root()))

    try:
        with tempfile.TemporaryDirectory(
            prefix="omnia_ibm_project_"
        ) as staging_dir:
            staged_project = os.path.join(staging_dir, "omnia")
            shutil.copytree(
                repo_root,
                staged_project,
                symlinks=True,
                ignore=_project_sync_ignore,
                copy_function=_link_or_copy,
            )
            result = sync_files(
                mode=conn["mode"],
                src=staged_project,
                dest=config["clone_path"],
                ip=conn["ip"],
                user=conn["user"],
                auth_secret=conn["auth_secret"],
                ssh_opts=conn["ssh_opts"],
            )
    except OSError as exc:
        return {
            "success": False,
            "details": "",
            "error": f"Failed to stage project for sync: {exc}",
        }

    if result["success"]:
        result["details"] = (
            f"Synced filtered project {repo_root} -> {config['clone_path']} "
            "(local credentials and caches excluded)"
        )
    return result


def _resolve_input_dir(config):
    """Resolve local input directory from dataset or src/."""
    return _resolve_dataset_subdir(config, "input", SRC_INPUT_DIR)


def _resolve_repo_output_dir(config):
    """Resolve local repo_manager_output directory from dataset or src/."""
    return _resolve_dataset_subdir(
        config, "repo_manager_output", SRC_REPO_OUTPUT_DIR
    )


def sync_image_build_input(
    host, config: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Push image_build input files from local source to target.

    Reads ``OMNIA_DATA_PATH`` and ``OMNIA_PROJECT_NAME`` from the target
    server's environment to resolve the correct destination::

        <OMNIA_DATA_PATH>/image_build_manager/input/<OMNIA_PROJECT_NAME>/

    Source: src/image_build_manager/input/ (default) or
            datasets/<dataset>/input/ (when dataset is set).

    Any credential artifacts are deliberately excluded. Generated datasets
    contain no credentials; runtime credentials are managed separately by
    ``sync_build_credentials`` or the local domain setup flow.
    """
    if config is None:
        config = load_test_config()
    conn = connection_params()

    local_input = _resolve_input_dir(config)
    remote_input = resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
    )
    ensure_remote_dir(host, remote_input)

    try:
        _reject_symlinks(local_input)
        with tempfile.TemporaryDirectory(
            prefix="omnia_ibm_input_"
        ) as staging_dir:
            staged_input = os.path.join(staging_dir, "input")
            os.makedirs(staged_input, exist_ok=True)
            for entry_name in sorted(os.listdir(local_input)):
                if _is_credential_artifact(entry_name):
                    continue
                source = os.path.join(local_input, entry_name)
                destination = os.path.join(staged_input, entry_name)
                if os.path.isdir(source):
                    shutil.copytree(source, destination)
                else:
                    shutil.copy2(source, destination)

            result = sync_files(
                mode=conn["mode"], src=staged_input, dest=remote_input,
                ip=conn["ip"], user=conn["user"],
                auth_secret=conn["auth_secret"], ssh_opts=conn["ssh_opts"],
            )
    except OSError as exc:
        return {
            "success": False,
            "details": "",
            "error": f"Failed to stage image-build input: {exc}",
        }

    if result["success"]:
        result["details"] += " (credentials excluded)"
    return result


def sync_repo_manager_output(
    host, config: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Push repo_manager_output from local source to target.

    Reads repo_manager_output_dir from image_build_config.yml.
    Falls back to <OMNIA_DATA_PATH>/repo_manager/output/<project_name>/.

    Source: src/.../samples/repo_manager_output/ (default) or
            datasets/<dataset>/repo_manager_output/ (when dataset is set).
    """
    if config is None:
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

_SAFE_DATA_PATH = re.compile(r"/[A-Za-z0-9._/-]+")
_SAFE_PROJECT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_MAX_CREDENTIAL_SIZE = 1024 * 1024
_MAX_KEY_SIZE = 4096


def _credential_result(
    success: bool, details: str = "", error: str = ""
) -> Dict[str, Any]:
    """Build the standard sync result mapping."""
    return {"success": success, "details": details, "error": error}


def _validate_credential_scope(
    data_path: str, project: str, location: str
) -> None:
    """Reject paths unsafe for local access, rsync, or a remote shell."""
    if (
        not data_path
        or data_path == "/"
        or data_path != os.path.normpath(data_path)
        or not _SAFE_DATA_PATH.fullmatch(data_path)
    ):
        raise ValueError(f"{location} OMNIA_DATA_PATH is unsafe: {data_path!r}")
    if (
        not project
        or project in {".", ".."}
        or len(project) > 128
        or not _SAFE_PROJECT.fullmatch(project)
    ):
        raise ValueError(
            f"{location} OMNIA_PROJECT_NAME is unsafe: {project!r}"
        )


def _credential_locations(
    host,
) -> tuple[
    tuple[str, str], str, tuple[str, str], tuple[str, str]
]:
    """Resolve controller artifacts, target directory, and both scopes."""
    target_data = read_remote_env(host, ENV_OMNIA_DATA_PATH)
    target_project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
    controller_data = os.environ.get(ENV_OMNIA_DATA_PATH) or "/opt/omnia"
    controller_project = os.environ.get(ENV_OMNIA_PROJECT_NAME) or "project_default"
    _validate_credential_scope(target_data, target_project, "Target")
    local_input = os.path.join(
        controller_data, DOMAIN_NAME, "input", controller_project
    )
    sources = (
        os.path.join(local_input, CREDENTIALS_FILE_NAME),
        os.path.join(local_input, CREDENTIALS_KEY_NAME),
    )
    remote_input = os.path.join(
        target_data, DOMAIN_NAME, "input", target_project
    )
    return (
        sources,
        remote_input,
        (controller_data, controller_project),
        (target_data, target_project),
    )


def _validate_matching_credential_scopes(
    controller_scope: tuple[str, str], target_scope: tuple[str, str]
) -> None:
    """Validate and match scopes before transferring controller artifacts."""
    _validate_credential_scope(
        controller_scope[0], controller_scope[1], "Controller"
    )
    if controller_scope != target_scope:
        raise ValueError(
            "Controller OMNIA_DATA_PATH/OMNIA_PROJECT_NAME do not match the "
            "target. Export the target values, then rerun "
            "./setup_env.sh --set-domain-creds"
        )


def _validate_encrypted_credential_pair(sources: tuple[str, str]) -> None:
    """Verify type, permissions, size, Vault header, and paired key."""
    credential, key = sources
    size_limits = ((credential, _MAX_CREDENTIAL_SIZE), (key, _MAX_KEY_SIZE))
    for path, size_limit in size_limits:
        if os.path.islink(path) or not os.path.isfile(path):
            raise ValueError(
                "Domain credential files must be regular files, not symlinks"
            )
        file_stat = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError(f"Domain credential artifact is not a file: {path}")
        if stat.S_IMODE(file_stat.st_mode) & 0o077:
            raise ValueError(
                f"Domain credential artifact must be mode 0600 or stricter: {path}"
            )
        if not 0 < file_stat.st_size <= size_limit:
            raise ValueError(f"Domain credential artifact has invalid size: {path}")
    with open(credential, "rb") as stream:
        if not stream.readline().startswith(b"$ANSIBLE_VAULT;"):
            raise ValueError("Refusing to sync plaintext domain credentials")
    with tempfile.TemporaryDirectory(
        prefix="omnia_ibm_vault_check_"
    ) as local_temp:
        check_env = os.environ.copy()
        check_env["ANSIBLE_LOCAL_TEMP"] = local_temp
        try:
            check = subprocess.run(
                [
                    "ansible-vault", "view", credential,
                    "--vault-password-file", key,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
                check=False,
                env=check_env,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ValueError(f"Cannot verify encrypted credential pair: {exc}") from exc
    if check.returncode != 0:
        raise ValueError(
            "Encrypted domain credential file does not match its vault key"
        )


def _copy_credential_staging(
    sources: tuple[str, str], staging_root: str
) -> str:
    """Copy the verified pair into a private local staging directory."""
    staged_credentials = os.path.join(staging_root, "credentials")
    os.makedirs(staged_credentials, mode=0o700)
    for source in sources:
        destination = os.path.join(
            staged_credentials, os.path.basename(source)
        )
        shutil.copy2(source, destination, follow_symlinks=False)
        os.chmod(destination, 0o600)
    return staged_credentials


def _credential_hashes(sources: tuple[str, str]) -> tuple[str, str]:
    """Return SHA-256 digests without loading credential data into memory."""
    digests = []
    for path in sources:
        digest = hashlib.sha256()
        with open(path, "rb") as stream:
            chunk = stream.read(1024 * 1024)
            while chunk:
                digest.update(chunk)
                chunk = stream.read(1024 * 1024)
        digests.append(digest.hexdigest())
    return digests[0], digests[1]


def _remote_credential_paths(
    remote_staging: str, remote_input: str, token: str
) -> Dict[str, str]:
    """Build the exact private paths used for one credential transaction."""
    final_credential = os.path.join(remote_input, CREDENTIALS_FILE_NAME)
    final_key = os.path.join(remote_input, CREDENTIALS_KEY_NAME)
    return {
        "staged_credential": os.path.join(
            remote_staging, CREDENTIALS_FILE_NAME
        ),
        "staged_key": os.path.join(remote_staging, CREDENTIALS_KEY_NAME),
        "final_credential": final_credential,
        "final_key": final_key,
        "new_credential": f"{final_credential}.new-{token}",
        "new_key": f"{final_key}.new-{token}",
        "backup_credential": f"{final_credential}.backup-{token}",
        "backup_key": f"{final_key}.backup-{token}",
    }


def _credential_activation_command(
    paths: Dict[str, str], expected_hashes: tuple[str, str]
) -> str:
    """Create a rollback-safe shell transaction for the encrypted pair."""
    quoted = {name: shlex.quote(path) for name, path in paths.items()}
    credential_hash, key_hash = expected_hashes
    return (
        "set -eu; "
        "had_credential=0; had_key=0; finals_touched=0; "
        "activation_complete=0; "
        "rollback() { status=$?; trap - EXIT; set +e; rollback_failed=0; "
        "if [ \"$finals_touched\" -eq 1 ] && "
        "[ \"$activation_complete\" -eq 0 ]; then "
        "if [ \"$had_credential\" -eq 1 ]; then "
        f"mv -f -- {quoted['backup_credential']} "
        f"{quoted['final_credential']} || rollback_failed=1; "
        f"else rm -f -- {quoted['final_credential']} || "
        "rollback_failed=1; fi; "
        "if [ \"$had_key\" -eq 1 ]; then "
        f"mv -f -- {quoted['backup_key']} {quoted['final_key']} || "
        "rollback_failed=1; "
        f"else rm -f -- {quoted['final_key']} || rollback_failed=1; fi; "
        "else "
        f"rm -f -- {quoted['backup_credential']} {quoted['backup_key']} || "
        "rollback_failed=1; fi; "
        f"rm -f -- {quoted['new_credential']} {quoted['new_key']} "
        "|| rollback_failed=1; "
        "if [ \"$rollback_failed\" -ne 0 ]; then exit 97; fi; "
        "exit \"$status\"; }; "
        "trap rollback EXIT; "
        f"test ! -L {quoted['final_credential']}; "
        f"test ! -L {quoted['final_key']}; "
        f"chmod 600 {quoted['staged_credential']} {quoted['staged_key']}; "
        f"test \"$(sha256sum {quoted['staged_credential']} | cut -d' ' -f1)\" "
        f"= {shlex.quote(credential_hash)}; "
        f"test \"$(sha256sum {quoted['staged_key']} | cut -d' ' -f1)\" "
        f"= {shlex.quote(key_hash)}; "
        f"if [ -e {quoted['final_credential']} ]; then "
        f"install -m 600 {quoted['final_credential']} "
        f"{quoted['backup_credential']}; had_credential=1; fi; "
        f"if [ -e {quoted['final_key']} ]; then "
        f"install -m 600 {quoted['final_key']} {quoted['backup_key']}; "
        "had_key=1; fi; "
        f"install -m 600 {quoted['staged_key']} {quoted['new_key']}; "
        f"install -m 600 {quoted['staged_credential']} "
        f"{quoted['new_credential']}; "
        "finals_touched=1; "
        f"mv -f -- {quoted['new_key']} {quoted['final_key']}; "
        f"mv -f -- {quoted['new_credential']} "
        f"{quoted['final_credential']}; "
        f"chmod 600 {quoted['final_credential']} {quoted['final_key']}; "
        "activation_complete=1; "
        f"rm -f -- {quoted['backup_credential']} {quoted['backup_key']}; "
        "trap - EXIT"
    )


def _activate_remote_credential_pair(
    host,
    remote_staging: str,
    remote_input: str,
    token: str,
    expected_hashes: tuple[str, str],
) -> Dict[str, Any]:
    """Verify staged file integrity, install it, and remove remote staging."""
    paths = _remote_credential_paths(remote_staging, remote_input, token)
    command = _credential_activation_command(paths, expected_hashes)
    cleanup_command = (
        "rm -rf -- "
        f"{shlex.quote(remote_staging)} "
        f"{shlex.quote(paths['new_credential'])} "
        f"{shlex.quote(paths['new_key'])}"
    )
    try:
        activation = run_on_host(host, command)
    except (OSError, RuntimeError):
        try:
            run_on_host(host, cleanup_command)
        except (OSError, RuntimeError):
            pass
        raise
    cleanup = run_on_host(
        host,
        cleanup_command,
    )
    if activation.rc != 0:
        failure = "Remote credential verification or installation failed"
        if activation.rc == 97:
            failure = (
                "Remote credential rollback failed; private backup files were "
                "retained in the target input directory for recovery"
            )
        return _credential_result(
            False,
            error=f"{failure} (rc={activation.rc})",
        )
    if cleanup.rc != 0:
        return _credential_result(
            False,
            error="Credentials installed, but remote staging cleanup failed",
        )
    return _credential_result(
        True,
        details=(
            "Encrypted image-build credential file and vault key synced to "
            f"{remote_input}"
        ),
    )


def _transfer_credential_pair(
    host, sources: tuple[str, str], remote_input: str
) -> Dict[str, Any]:
    """Transfer the pair to a private target staging path, then activate it."""
    connection = connection_params()
    expected_hashes = _credential_hashes(sources)
    token = uuid.uuid4().hex
    remote_staging = os.path.join(
        remote_input, f".omnia_ibm_credentials_{token}"
    )
    with tempfile.TemporaryDirectory(
        prefix="omnia_ibm_credentials_"
    ) as staging_root:
        staged_credentials = _copy_credential_staging(sources, staging_root)
        result = sync_files(
            mode=connection["mode"],
            src=staged_credentials,
            dest=remote_staging,
            ip=connection["ip"],
            user=connection["user"],
            auth_secret=connection["auth_secret"],
            ssh_opts=connection["ssh_opts"],
        )
    if not result.get("success"):
        run_on_host(host, f"rm -rf -- {shlex.quote(remote_staging)}")
        return result
    return _activate_remote_credential_pair(
        host, remote_staging, remote_input, token, expected_hashes
    )


def sync_build_credentials(host) -> Dict[str, Any]:
    """Validate and securely sync the separate encrypted domain pair."""
    try:
        sources, remote_input, controller_scope, target_scope = (
            _credential_locations(host)
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return _credential_result(
            False, error=f"Cannot resolve credential locations: {exc}"
        )
    existing = tuple(os.path.lexists(path) for path in sources)
    if not any(existing):
        return _credential_result(
            True,
            details=(
                "No controller encrypted domain credentials found — skipping "
                "transfer. Existing target-managed credentials remain unchanged. "
                "To transfer a pair, export the target OMNIA_DATA_PATH and "
                "OMNIA_PROJECT_NAME on the controller, then from "
                "test/image_build_manager run ./setup_env.sh --set-domain-creds."
            ),
        )
    if not all(existing):
        missing = CREDENTIALS_FILE_NAME if not existing[0] else CREDENTIALS_KEY_NAME
        return _credential_result(
            False,
            error=f"Incomplete controller domain credential pair; missing {missing}",
        )
    try:
        _validate_matching_credential_scopes(controller_scope, target_scope)
    except ValueError as exc:
        return _credential_result(
            False, error=f"Cannot resolve credential locations: {exc}"
        )
    try:
        _validate_encrypted_credential_pair(sources)
        return _transfer_credential_pair(host, sources, remote_input)
    except (OSError, RuntimeError, ValueError) as exc:
        return _credential_result(
            False, error=f"Cannot sync encrypted domain credentials: {exc}"
        )
