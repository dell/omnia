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
Clone and file-sync utilities.

- ``clone_repo``  — clone or pull a git repository (local or SSH)
- ``sync_files``  — rsync a path (directory or file) (local or SSH)

Usage from a consumer module::

    from omnia_auto import clone_repo, sync_files

    # Local clone
    clone_repo(mode="local", url="https://…", dest="/root/repo")

    # SSH clone
    clone_repo(mode="ssh", url="https://…", dest="/root/repo",
               ip=conn["ip"], user=conn["user"],
               auth_secret=conn["auth_secret"],
               ssh_opts=conn["ssh_opts"])

    # Sync a directory over SSH
    sync_files(mode="ssh", src="/local/dir", dest="/remote/dir",
               ip=conn["ip"], user=conn["user"],
               auth_secret=conn["auth_secret"],
               ssh_opts=conn["ssh_opts"])
"""

import os
import shlex
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from .process_security import (
    descriptor_tuple,
    scrubbed_subprocess_environment,
    sshpass_pipe,
)
from ._ssh_options import (
    parse_ssh_options,
    validate_ssh_destination,
    validate_ssh_port,
)


# =====================================================================
# INTERNAL HELPERS — List-based command builders (Checkmarx-safe)
# =====================================================================

def _parse_ssh_opts(ssh_opts: str) -> List[str]:
    """Parse SSH options string into a list of arguments."""
    return parse_ssh_options(ssh_opts)


def _validate_clone_destination(dest: str) -> None:
    """Reject broad destinations before a force clone can remove them."""
    normalized = os.path.abspath(os.path.expanduser(dest))
    current_dir = os.path.abspath(os.getcwd())
    protected = {
        os.path.abspath(os.sep),
        os.path.abspath(os.path.expanduser("~")),
        current_dir,
        "/etc",
        "/opt",
        "/root",
        "/tmp",  # nosec B108 -- protected deletion target, not temp creation
        "/usr",
        "/var",
    }
    try:
        contains_working_directory = (
            os.path.commonpath([normalized, current_dir]) == normalized
        )
    except ValueError:
        contains_working_directory = False
    if normalized in protected or contains_working_directory:
        raise ValueError(
            f"Refusing to use protected clone destination: {dest}"
        )


def _validate_path(value: str, label: str) -> str:
    """Validate a local or remote path argument."""
    if not isinstance(value, str) or not value or any(
        character in value for character in ("\x00", "\r", "\n")
    ):
        raise ValueError(f"{label} must be a non-empty single-line path")
    return value


def _validate_timeout(timeout: int) -> None:
    """Validate a subprocess timeout."""
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError("timeout must be a positive integer")


def _build_ssh_cmd_list(
    ip: str,
    user: str,
    port: int,
    auth_fd: Optional[int],
    ssh_opts: str,
    remote_cmd: str,
) -> List[str]:
    """Build SSH command as a list (Checkmarx-safe, no shell mode).

    Args:
        ip: Target host IP.
        user: SSH user.
        port: SSH port.
        auth_fd: Descriptor read by sshpass, or ``None`` for key auth.
        ssh_opts: SSH options string.
        remote_cmd: Command to execute on the remote host.

    Returns:
        Command as a list of strings.
    """
    opts = _parse_ssh_opts(ssh_opts)
    target = f"{user}@{ip}"

    if auth_fd is not None:
        return [
            "sshpass", "-d", str(auth_fd), "ssh", "-p", str(port),
        ] + opts + ["--", target, remote_cmd]
    return ["ssh", "-p", str(port)] + opts + ["--", target, remote_cmd]


def _build_scp_cmd_list(
    ip: str,
    user: str,
    port: int,
    auth_fd: Optional[int],
    ssh_opts: str,
    src: str,
    dest: str,
) -> List[str]:
    """Build SCP command as a list (Checkmarx-safe, no shell mode).

    Args:
        ip: Target host IP.
        user: SSH user.
        port: SSH port.
        auth_fd: Descriptor read by sshpass, or ``None`` for key auth.
        ssh_opts: SSH options string.
        src: Local source path.
        dest: Remote destination path.

    Returns:
        Command as a list of strings.
    """
    opts = _parse_ssh_opts(ssh_opts)
    target = f"{user}@{ip}:{shlex.quote(dest)}"

    if auth_fd is not None:
        return [
            "sshpass", "-d", str(auth_fd), "scp", "-P", str(port),
        ] + opts + ["--", src, target]
    return ["scp", "-P", str(port)] + opts + ["--", src, target]


def _build_rsync_ssh_e(
    auth_fd: Optional[int], ssh_opts: str, port: int,
) -> str:
    """Build the ``-e`` argument for rsync over SSH.

    Args:
        auth_fd: Descriptor read by sshpass, or ``None`` for key auth.
        ssh_opts: SSH options string.
        port: SSH port.

    Returns:
        SSH command string for rsync ``-e``.
    """
    opts = _parse_ssh_opts(ssh_opts)
    if auth_fd is not None:
        return shlex.join([
            "sshpass", "-d", str(auth_fd), "ssh", "-p", str(port), *opts,
        ])
    return shlex.join(["ssh", "-p", str(port), *opts])


# =====================================================================
# CLONE
# =====================================================================

def clone_repo(
    mode: str,
    url: str,
    dest: str,
    *,
    ip: Optional[str] = None,
    user: str = "root",
    port: int = 22,
    auth_secret: Optional[str] = None,
    ssh_opts: str = "-o StrictHostKeyChecking=accept-new -o LogLevel=ERROR",
    force: bool = False,
    timeout: int = 300,
) -> Dict[str, Any]:
    """Clone (or pull) a git repository.

    Args:
        mode: ``"local"`` or ``"ssh"``.
        url: Git clone URL.
        dest: Destination path for the repo.
        ip: Target host IP (required when ``mode="ssh"``).
        user: SSH user (default ``root``).
        port: SSH port (default ``22``).
        auth_secret: SSH auth secret.  When set, ``sshpass`` is used.
        ssh_opts: SSH options string.
        force: Remove existing repo and re-clone.
        timeout: Subprocess timeout in seconds.

    Returns:
        Dict with ``success``, ``details``, ``error``.
    """
    result: Dict[str, Any] = {"success": False, "details": "", "error": ""}

    if not isinstance(force, bool):
        result["error"] = "force must be a boolean"
        return result

    if mode not in ("local", "ssh"):
        result["error"] = f"Invalid mode '{mode}': must be 'local' or 'ssh'"
        return result
    if mode == "ssh" and not ip:
        result["error"] = "mode='ssh' requires 'ip'"
        return result
    if mode == "ssh":
        try:
            ip, user = validate_ssh_destination(ip, user)
            port = validate_ssh_port(port)
        except ValueError as exc:
            result["error"] = str(exc)
            return result
    try:
        url = _validate_path(url, "url")
        dest = _validate_path(dest, "dest")
        _validate_timeout(timeout)
    except ValueError as exc:
        result["error"] = str(exc)
        return result
    if mode == "ssh" and force and not os.path.isabs(dest):
        result["error"] = "Remote force clone requires an absolute destination"
        return result
    if force:
        try:
            _validate_clone_destination(dest)
        except ValueError as exc:
            result["error"] = str(exc)
            return result

    def _run_cmd(
        cmd_list: List[str],
        pass_fds: Tuple[int, ...] = (),
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.CompletedProcess:
        """Run a command list with timeout."""
        return subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            pass_fds=pass_fds,
            env=env,
        )

    def _run_ssh(remote_cmd: str) -> subprocess.CompletedProcess:
        """Run a remote command via SSH (list args)."""
        with sshpass_pipe(auth_secret) as auth_fd:
            cmd_list = _build_ssh_cmd_list(
                ip, user, port, auth_fd, ssh_opts, remote_cmd,
            )
            return _run_cmd(
                cmd_list,
                descriptor_tuple(auth_fd),
                scrubbed_subprocess_environment(),
            )

    try:
        # Check existing repo
        if mode == "local":
            repo_exists = os.path.isdir(os.path.join(dest, ".git"))
        else:
            chk = _run_ssh(
                f"test -d {shlex.quote(dest)}/.git && echo YES || echo NO"
            )
            if chk.returncode != 0:
                result["error"] = (
                    f"Unable to inspect remote destination: {chk.stderr}"
                )
                return result
            repo_exists = "YES" in chk.stdout

        if repo_exists and force:
            if mode == "local":
                shutil.rmtree(dest)
            else:
                rm = _run_ssh(f"rm -rf -- {shlex.quote(dest)}")
                if rm.returncode != 0:
                    result["error"] = f"Failed to remove {dest}: {rm.stderr}"
                    return result
            repo_exists = False

        if not repo_exists:
            if mode == "local":
                cl = _run_cmd(["git", "clone", "--", url, dest])
            else:
                cl = _run_ssh(
                    f"git clone -- {shlex.quote(url)} {shlex.quote(dest)}"
                )
            if cl.returncode != 0:
                result["error"] = f"git clone failed: {cl.stdout}{cl.stderr}"
                return result
            result["details"] = f"Cloned {url} -> {dest}"
        else:
            if mode == "local":
                pull = _run_cmd(["git", "-C", dest, "pull", "--ff-only"])
            else:
                pull = _run_ssh(
                    f"git -C {shlex.quote(dest)} pull --ff-only"
                )
            if pull.returncode != 0:
                result["error"] = (
                    f"git pull failed: {pull.stdout}{pull.stderr}"
                )
                return result
            result["details"] = f"Repo exists at {dest}, pulled latest"

        result["success"] = True

    except subprocess.TimeoutExpired:
        result["error"] = f"clone_repo timed out after {timeout}s"
    except (OSError, ValueError) as exc:
        result["error"] = f"Error during clone: {exc}"

    return result


# =====================================================================
# SYNC
# =====================================================================

def sync_files(
    mode: str,
    src: str,
    dest: str,
    *,
    ip: Optional[str] = None,
    user: str = "root",
    port: int = 22,
    auth_secret: Optional[str] = None,
    ssh_opts: str = "-o StrictHostKeyChecking=accept-new -o LogLevel=ERROR",
    timeout: int = 120,
    mkdir: bool = True,
) -> Dict[str, Any]:
    """Sync files or directories from *src* to *dest*.

    Works for both single files and directories.  Uses ``rsync``
    for directories, ``cp``/``scp`` for single files.

    Args:
        mode: ``"local"`` or ``"ssh"``.
        src: Source path (local filesystem).
        dest: Destination path.
        ip: Target host IP (required when ``mode="ssh"``).
        user: SSH user (default ``root``).
        port: SSH port (default ``22``).
        auth_secret: SSH auth secret.  When set, ``sshpass`` is used.
        ssh_opts: SSH options string.
        timeout: Subprocess timeout in seconds.
        mkdir: Create destination parent directory before sync.

    Returns:
        Dict with ``success``, ``details``, ``error``.
    """
    result: Dict[str, Any] = {"success": False, "details": "", "error": ""}

    if not isinstance(mkdir, bool):
        result["error"] = "mkdir must be a boolean"
        return result

    if mode not in ("local", "ssh"):
        result["error"] = f"Invalid mode '{mode}': must be 'local' or 'ssh'"
        return result
    try:
        src = _validate_path(src, "src")
        dest = _validate_path(dest, "dest")
        _validate_timeout(timeout)
    except ValueError as exc:
        result["error"] = str(exc)
        return result
    if not os.path.exists(src):
        result["error"] = f"Source not found: {src}"
        return result
    if mode == "ssh" and not ip:
        result["error"] = "mode='ssh' requires 'ip'"
        return result
    if mode == "ssh":
        try:
            ip, user = validate_ssh_destination(ip, user)
            port = validate_ssh_port(port)
        except ValueError as exc:
            result["error"] = str(exc)
            return result

    is_dir = os.path.isdir(src)

    try:
        # --- local mode -------------------------------------------
        if mode == "local":
            if mkdir:
                dest_dir = dest if is_dir else (os.path.dirname(dest) or ".")
                os.makedirs(dest_dir, exist_ok=True)

            if is_dir:
                r = subprocess.run(
                    [
                        "rsync", "-avz", "--protect-args", "--",
                        f"{src}/", f"{dest}/",
                    ],
                    capture_output=True, text=True,
                    timeout=timeout, check=False,
                )
            else:
                r = subprocess.run(
                    ["cp", "--", src, dest],
                    capture_output=True, text=True,
                    timeout=timeout, check=False,
                )

            if r.returncode != 0:
                result["error"] = f"sync failed: {r.stderr}"
                return result

            result["success"] = True
            result["details"] = f"Synced {src} -> {dest}"
            return result

        # --- SSH mode ---------------------------------------------
        if mkdir:
            dest_dir = dest if is_dir else (os.path.dirname(dest) or ".")
            with sshpass_pipe(auth_secret) as auth_fd:
                mkdir_cmd = _build_ssh_cmd_list(
                    ip, user, port, auth_fd, ssh_opts,
                    f"mkdir -p {shlex.quote(dest_dir)}",
                )
                mkdir_result = subprocess.run(
                    mkdir_cmd,
                    capture_output=True, text=True,
                    timeout=30, check=False,
                    pass_fds=descriptor_tuple(auth_fd),
                    env=scrubbed_subprocess_environment(),
                )
                if mkdir_result.returncode != 0:
                    result["error"] = (
                        "Unable to create remote destination: "
                        f"{mkdir_result.stderr}"
                    )
                    return result

        if is_dir:
            with sshpass_pipe(auth_secret) as auth_fd:
                ssh_e = _build_rsync_ssh_e(auth_fd, ssh_opts, port)
                r = subprocess.run(
                    [
                        "rsync", "-avz", "-e", ssh_e,
                        "--protect-args", "--",
                        f"{src}/", f"{user}@{ip}:{dest}/",
                    ],
                    capture_output=True, text=True,
                    timeout=timeout, check=False,
                    pass_fds=descriptor_tuple(auth_fd),
                    env=scrubbed_subprocess_environment(),
                )
        else:
            with sshpass_pipe(auth_secret) as auth_fd:
                scp_cmd = _build_scp_cmd_list(
                    ip, user, port, auth_fd, ssh_opts, src, dest,
                )
                r = subprocess.run(
                    scp_cmd,
                    capture_output=True, text=True,
                    timeout=timeout, check=False,
                    pass_fds=descriptor_tuple(auth_fd),
                    env=scrubbed_subprocess_environment(),
                )

        if r.returncode != 0:
            result["error"] = f"sync failed: {r.stderr}"
            return result

        result["success"] = True
        result["details"] = f"Synced {src} -> {user}@{ip}:{dest}"

    except subprocess.TimeoutExpired:
        result["error"] = f"sync_files timed out after {timeout}s"
    except (OSError, ValueError) as exc:
        result["error"] = f"Error during sync: {exc}"

    return result
