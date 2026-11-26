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

"""Orchestrator cleanup: check and empty the Slurm and Kubernetes NFS shares.

The cleanup run unmounts both shares and removes their fstab entries, whatever
``cleanup_slurm`` and ``cleanup_k8s`` of test_config.yml say; ``check_nfs_share_detached``
verifies that for the ``nfs_slurm`` and ``nfs_k8s`` mounts of storage_config.yml. Only when
the flag is true is the share then emptied (``empty_nfs_share``): it is mounted again on a
private folder (never added to fstab), emptied completely, unmounted and checked to be
empty, with up to three attempts. Emptying mounts the share on the execution OIM, so it
needs a local run as root there. The safety rules (read-only preflight first, protected
exports, no symbolic links followed) are those of ``nfs_func``.
"""

import os
from typing import Any

from omnia_auto import (
    is_local_execution,
    load_test_config,
    log,
    read_remote_env,
    run_on_host,
)

from ..messages.nfs_msgs import NFS_MSGS
from ..vars.common_vars import MONOREPO_ROOT
from ..vars.nfs_vars import NFS_SHARE_FLAGS, STORAGE_CONFIG_FILE
from . import nfs_func
from .project_func import ENV_OMNIA_DATA_PATH, resolve_target_input_project_path


def _emit(text: str) -> None:
    log(text, "INFO")


def can_run_locally() -> bool:
    """Return whether this run is local and root: mount needs both."""
    return is_local_execution() and os.geteuid() == 0


def nfs_share_selected(name: str) -> bool:
    """Return the ``cleanup_slurm`` / ``cleanup_k8s`` flag of the share (default true)."""
    value = load_test_config().get(NFS_SHARE_FLAGS[name], True)
    if not isinstance(value, bool):
        raise TypeError(f"{NFS_SHARE_FLAGS[name]} must be true or false")
    return value


def get_storage_config_path(host) -> str:
    """Return the storage_config.yml of the orchestrator input project on the OIM."""
    return os.path.join(resolve_target_input_project_path(host), STORAGE_CONFIG_FILE)


def get_protected_paths(host) -> list[str]:
    """Return the paths an export on this OIM must not contain."""
    paths = [MONOREPO_ROOT, "/etc/omnia"]
    clone_path = str(load_test_config().get("clone_path") or "")
    if clone_path:
        paths.append(clone_path)
    try:
        paths.append(read_remote_env(host, ENV_OMNIA_DATA_PATH, required=False) or "")
    except Exception:  # pylint: disable=broad-except
        pass
    return [path for path in paths if path]


def get_nfs_mount(storage_config: str, name: str) -> dict[str, Any]:
    """Return {"success", "source", "mount_point", "missing", "error"} of the ``name`` mount.

    A missing file, a missing mount or a mount that is not an NFS source is not an error:
    there is nothing to check or empty (``source`` stays empty). An invalid or forbidden
    source is.
    """
    result: dict[str, Any] = {"success": True, "source": "", "mount_point": "",
                              "missing": False, "error": ""}
    if not os.path.isfile(storage_config):
        result["missing"] = True
        return result
    try:
        mount = nfs_func.configured_mounts(storage_config, _emit).get(name, {})
        source = mount.get("source", "")
        if source and nfs_func.looks_like_nfs(source):
            nfs_func.parse_source(name, source)
            result.update(source=source, mount_point=mount.get("mount_point", ""))
    except nfs_func.NfsError as exc:
        result.update(success=False, error=str(exc))
    return result


def check_nfs_share_detached(host, name: str, source: str, mount_point: str) -> dict[str, Any]:
    """Check that the share is unmounted and has no fstab entry.

    The mount point is checked in the kernel mount table and in /etc/fstab. A mount without a
    mount point is looked up by its source instead.

    Returns:
        Dict with keys: success, fields (label, value pairs for the report), problems, error.
    """
    problems: list[str] = []
    fields: list[tuple[str, object]] = [("Share", name), ("Source", source),
                                        ("Mount point", mount_point or "not set")]
    if mount_point:
        mounted = run_on_host(host, "findmnt -rn -M %s", mount_point).rc == 0
        in_fstab = run_on_host(host, "findmnt --fstab -rn --target %s", mount_point).rc == 0
        if mounted:
            problems.append(NFS_MSGS["still_mounted"].format(mount_point=mount_point))
        if in_fstab:
            problems.append(NFS_MSGS["still_in_fstab"].format(mount_point=mount_point))
    else:
        found = run_on_host(host, "findmnt -rn -t nfs,nfs4 --source %s", source)
        mounted = found.rc == 0 and bool(found.stdout.strip())
        in_fstab = run_on_host(host, "findmnt --fstab -rn --source %s", source).rc == 0
        if mounted:
            targets = ", ".join(line.split()[0] for line in found.stdout.splitlines() if line)
            problems.append(NFS_MSGS["source_mounted"].format(source=source, targets=targets))
        if in_fstab:
            problems.append(NFS_MSGS["source_in_fstab"].format(source=source))
    fields.append(("Mounted", "YES" if mounted else "no"))
    fields.append(("fstab entry", "PRESENT" if in_fstab else "absent"))
    return {"success": not problems, "fields": fields, "problems": problems,
            "error": "; ".join(problems)}


def empty_nfs_share(name: str, source: str, protected: list[str]) -> dict[str, Any]:
    """Check the share is reachable (read-only), then empty it and check nothing is left.

    The share is emptied on a temporary private mount that is never added to fstab; it is
    unmounted again afterwards and verified empty with a fresh read-only mount, up to three
    attempts.
    """
    result: dict[str, Any] = {"success": True, "stats": {}, "error": ""}
    try:
        nfs_func.check_share(name, name, source, _emit, protected)
        result["stats"] = nfs_func.wipe_share(name, name, source, _emit, protected)
    except nfs_func.NfsError as exc:
        result.update(success=False, error=str(exc))
    return result
