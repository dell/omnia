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
import subprocess
from typing import Any, Dict, Optional


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
    auth_secret: Optional[str] = None,
    ssh_opts: str = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR",
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
        auth_secret: SSH auth secret.  When set, ``sshpass`` is used.
        ssh_opts: SSH options string.
        force: Remove existing repo and re-clone.
        timeout: Subprocess timeout in seconds.

    Returns:
        Dict with ``success``, ``details``, ``error``.
    """
    result = {"success": False, "details": "", "error": ""}

    if mode not in ("local", "ssh"):
        result["error"] = f"Invalid mode '{mode}': must be 'local' or 'ssh'"
        return result
    if mode == "ssh" and not ip:
        result["error"] = "mode='ssh' requires 'ip'"
        return result
    if not url:
        result["error"] = "'url' is required"
        return result
    if not dest:
        result["error"] = "'dest' is required"
        return result

    # --- helpers ---------------------------------------------------
    def _run(cmd: str) -> subprocess.CompletedProcess:
        if mode == "local":
            return subprocess.run(
                cmd, shell=True, capture_output=True, text=True,  # nosec B602
                timeout=timeout, check=False,
            )
        ssh_cmd = _build_ssh_cmd(ip, user, auth_secret, ssh_opts, cmd)
        return subprocess.run(
            ssh_cmd, shell=True, capture_output=True, text=True,  # nosec B602
            timeout=timeout, check=False,
        )

    try:
        # --- check existing repo ----------------------------------
        chk = _run(f"test -d {dest}/.git && echo YES || echo NO")
        repo_exists = chk.returncode == 0 and "YES" in chk.stdout

        if repo_exists and force:
            rm = _run(f"rm -rf {dest}")
            if rm.returncode != 0:
                result["error"] = f"Failed to remove {dest}: {rm.stderr}"
                return result
            repo_exists = False

        if not repo_exists:
            cl = _run(f"git clone {url} {dest} 2>&1")
            if cl.returncode != 0:
                result["error"] = (
                    f"git clone failed: {cl.stdout}{cl.stderr}"
                )
                return result
            result["details"] = f"Cloned {url} -> {dest}"
        else:
            _run(f"cd {dest} && git pull 2>&1")
            result["details"] = f"Repo exists at {dest}, pulled latest"

        result["success"] = True

    except subprocess.TimeoutExpired:
        result["error"] = f"clone_repo timed out after {timeout}s"
    except OSError as exc:
        result["error"] = f"OS error during clone: {exc}"

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
    auth_secret: Optional[str] = None,
    ssh_opts: str = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR",
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
        auth_secret: SSH auth secret.  When set, ``sshpass`` is used.
        ssh_opts: SSH options string.
        timeout: Subprocess timeout in seconds.
        mkdir: Create destination parent directory before sync.

    Returns:
        Dict with ``success``, ``details``, ``error``.
    """
    result = {"success": False, "details": "", "error": ""}

    if mode not in ("local", "ssh"):
        result["error"] = f"Invalid mode '{mode}': must be 'local' or 'ssh'"
        return result
    if not src:
        result["error"] = "'src' is required"
        return result
    if not dest:
        result["error"] = "'dest' is required"
        return result
    if not os.path.exists(src):
        result["error"] = f"Source not found: {src}"
        return result
    if mode == "ssh" and not ip:
        result["error"] = "mode='ssh' requires 'ip'"
        return result

    is_dir = os.path.isdir(src)

    try:
        # --- local mode -------------------------------------------
        if mode == "local":
            if mkdir:
                dest_dir = dest if is_dir else os.path.dirname(dest)
                os.makedirs(dest_dir, exist_ok=True)

            if is_dir:
                r = subprocess.run(
                    ["rsync", "-avz", f"{src}/", f"{dest}/"],
                    capture_output=True, text=True,
                    timeout=timeout, check=False,
                )
            else:
                r = subprocess.run(
                    ["cp", src, dest],
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
            dest_dir = dest if is_dir else os.path.dirname(dest)
            mkdir_cmd = _build_ssh_cmd(
                ip, user, auth_secret, ssh_opts,
                f"mkdir -p {shlex.quote(dest_dir)}",
            )
            subprocess.run(
                mkdir_cmd, shell=True, capture_output=True,  # nosec B602
                text=True, timeout=30, check=False,
            )

        if is_dir:
            ssh_e = _build_ssh_e(auth_secret, ssh_opts)
            r = subprocess.run(
                [
                    "rsync", "-avz", "-e", ssh_e,
                    f"{src}/", f"{user}@{ip}:{dest}/",
                ],
                capture_output=True, text=True,
                timeout=timeout, check=False,
            )
        else:
            if auth_secret:
                scp_cmd = (
                    f"sshpass -p {shlex.quote(auth_secret)}"
                    f" scp {ssh_opts}"
                    f" {shlex.quote(src)}"
                    f" {shlex.quote(user)}@{shlex.quote(ip)}"
                    f":{shlex.quote(dest)}"
                )
                r = subprocess.run(
                    scp_cmd,
                    shell=True, capture_output=True, text=True,  # nosec B602
                    timeout=timeout, check=False,
                )
            else:
                r = subprocess.run(
                    ["scp", *ssh_opts.split(), src,
                     f"{user}@{ip}:{dest}"],
                    capture_output=True, text=True,
                    timeout=timeout, check=False,
                )

        if r.returncode != 0:
            result["error"] = f"sync failed: {r.stderr}"
            return result

        result["success"] = True
        result["details"] = f"Synced {src} -> {user}@{ip}:{dest}"

    except subprocess.TimeoutExpired:
        result["error"] = f"sync_files timed out after {timeout}s"
    except OSError as exc:
        result["error"] = f"OS error during sync: {exc}"

    return result


# =====================================================================
# INTERNAL HELPERS
# =====================================================================

def _build_ssh_cmd(
    ip: str,
    user: str,
    auth_secret: Optional[str],
    ssh_opts: str,
    cmd: str,
) -> str:
    """Build an SSH (or sshpass + SSH) command string.

    Args:
        ip: Target host IP.
        user: SSH user.
        auth_secret: SSH auth secret (sshpass is used when set).
        ssh_opts: SSH options string.
        cmd: Command to execute on the remote host.

    Returns:
        Shell command string.
    """
    quoted_cmd = shlex.quote(cmd)
    if auth_secret:
        return (
            f"sshpass -p {shlex.quote(auth_secret)} ssh {ssh_opts} "
            f"{shlex.quote(user)}@{shlex.quote(ip)} {quoted_cmd}"
        )
    return (
        f"ssh {ssh_opts} "
        f"{shlex.quote(user)}@{shlex.quote(ip)} {quoted_cmd}"
    )


def _build_ssh_e(auth_secret: Optional[str], ssh_opts: str) -> str:
    """Build the ``-e`` argument for rsync over SSH.

    Args:
        auth_secret: SSH auth secret (sshpass is used when set).
        ssh_opts: SSH options string.

    Returns:
        SSH command string for rsync ``-e``.
    """
    if auth_secret:
        return (
            f"sshpass -p {shlex.quote(auth_secret)} ssh {ssh_opts}"
        )
    return f"ssh {ssh_opts}"
