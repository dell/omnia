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

"""Orchestrator cleanup: empty the Slurm and Kubernetes NFS shares.

``cleanup_slurm`` and ``cleanup_k8s`` of test_config.yml decide: true empties the matching
share of storage_config.yml (``nfs_slurm`` or ``nfs_k8s``), false skips its test. The shares
are mounted by the execution OIM, so this needs a local run as root on that OIM. The safety
rules (read-only preflight first, protected exports, no symbolic links followed) are those of
``nfs_func``.
"""

import os
from typing import Any

from omnia_auto import is_local_execution, load_test_config, log, read_remote_env

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


def get_nfs_source(storage_config: str, name: str) -> dict[str, Any]:
    """Return {"success", "source", "missing", "error"} of the ``name`` mount.

    A missing file, a missing mount or a mount that is not an NFS source is not an error:
    there is nothing to empty (``source`` stays empty). An invalid or forbidden source is.
    """
    result: dict[str, Any] = {"success": True, "source": "", "missing": False, "error": ""}
    if not os.path.isfile(storage_config):
        result["missing"] = True
        return result
    try:
        source = nfs_func.configured_sources(storage_config, _emit).get(name, "")
        if source and nfs_func.looks_like_nfs(source):
            nfs_func.parse_source(name, source)
            result["source"] = source
    except nfs_func.NfsError as exc:
        result.update(success=False, error=str(exc))
    return result


def empty_nfs_share(name: str, source: str, protected: list[str]) -> dict[str, Any]:
    """Check the share is reachable (read-only), empty it, then check nothing is left."""
    result: dict[str, Any] = {"success": True, "stats": {}, "error": ""}
    try:
        nfs_func.check_share(name, name, source, _emit, protected)
        result["stats"] = nfs_func.wipe_share(name, name, source, _emit, protected)
        left = nfs_func.check_share(name, name, source, _emit, protected)
        if left:
            result.update(success=False, error=NFS_MSGS["left"].format(name=name, count=left))
    except nfs_func.NfsError as exc:
        result.update(success=False, error=str(exc))
    return result
