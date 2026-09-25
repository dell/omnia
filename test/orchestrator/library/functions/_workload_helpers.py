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

"""Shared Kubernetes and Slurm context, selection, and skip contracts."""

import re

from omnia_auto import load_test_credentials

from ..vars.pxeboot_vars import (
    KUBERNETES_PREFIX,
    KUBERNETES_PRIMARY_CONTROL_PLANE_PREFIX,
    PXEBOOT_COMMANDS,
    SLURM_COMPUTE_PREFIX,
    SLURM_CONTROL_PREFIX,
    SLURM_PREFIXES,
    SLURM_SUBMISSION_PREFIXES,
)
from ._provision_helpers import load_context
from ._pxeboot_helpers import (
    first_row,
    load_workload_context,
    marker_is_authorized,
    remote_command,
    rows_matching,
    runtime_result,
    selected_kubernetes_config,
    selected_slurm_config,
)

_GPU_GRES_RE = re.compile(r"(?:^|,)gpu(?::[^,:()]+)?:(\d+)(?:\(|,|$)")


def kubernetes_context(host):
    """Return runtime context, mapped Kubernetes rows, primary, and config."""
    context = load_context(host)
    rows = rows_matching(context, (KUBERNETES_PREFIX,))
    if not rows:
        return context, rows, None, None
    context = load_workload_context(host, context)
    control = first_row(rows, KUBERNETES_PRIMARY_CONTROL_PLANE_PREFIX)
    if control is None:
        raise ValueError("No primary Kubernetes control-plane node was generated")
    return context, rows, control, selected_kubernetes_config(context)


def slurm_context(host):
    """Return runtime context, mapped Slurm rows, controller, and config."""
    context = load_context(host)
    rows = rows_matching(context, SLURM_PREFIXES)
    if not rows:
        return context, rows, None, None
    context = load_workload_context(host, context)
    control = first_row(rows, SLURM_CONTROL_PREFIX)
    if control is None:
        raise ValueError("No Slurm control node is present in the desired mapping")
    return context, rows, control, selected_slurm_config(context)


def slurm_shared_storage(context, slurm_config):
    """Resolve the configured common Slurm NFS storage entry."""
    storage_name = str(slurm_config.get("nfs_storage_name") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", storage_name):
        raise ValueError("slurm_cluster.nfs_storage_name is missing or invalid")
    mounts = context.get("storage_config", {}).get("mounts", [])
    if not isinstance(mounts, list):
        raise TypeError("storage_config.mounts must be a list")
    matches = [
        entry
        for entry in mounts
        if isinstance(entry, dict) and entry.get("name") == storage_name
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Storage '{storage_name}' must resolve to exactly one mount entry"
        )
    source = str(matches[0].get("source") or "").strip()
    mount_point = str(matches[0].get("mount_point") or "").rstrip("/")
    if not source or not re.fullmatch(r"[A-Za-z0-9_.:/-]+", source):
        raise ValueError(f"Storage '{storage_name}' has an invalid source")
    if (
        not re.fullmatch(r"/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", mount_point)
        # These protected paths are being explicitly rejected.
        or mount_point in {"/", "/home", "/root", "/tmp"}  # nosec B108
    ):
        raise ValueError(f"Storage '{storage_name}' has an unsafe mount point")
    return {
        "name": storage_name,
        "source": source,
        "mount_point": mount_point,
    }


def optional_skip(summary: str, reason: str = ""):
    """Return the canonical successful skip result for an optional capability."""
    return runtime_result(
        True,
        summary,
        [("Reason", reason)] if reason else [],
        "",
        skipped=True,
    )


def require_marker(summary: str, marker: str, reason: str):
    """Return a skip result unless the caller received explicit authorization."""
    if marker_is_authorized(marker):
        return None
    return optional_skip(summary, reason)


def slurm_compute_rows(rows):
    """Return mapped Slurm compute roles."""
    return [
        row
        for row in rows
        if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(SLURM_COMPUTE_PREFIX)
    ]


def slurm_gpu_rows(host, control, compute_rows):
    """Return mapped compute rows where Slurm declares a GPU GRES."""
    scheduler = remote_command(host, control, PXEBOOT_COMMANDS["slurm_nodes"])
    if scheduler.rc != 0:
        raise RuntimeError("scontrol could not read Slurm GPU GRES state")
    inventory = {}
    for line in scheduler.stdout.splitlines():
        attributes = dict(re.findall(r"(?:^|\s)([A-Za-z][A-Za-z0-9]*)=(\S+)", line))
        hostname = str(attributes.get("NodeName", "")).split(".", 1)[0]
        gres = str(attributes.get("Gres", ""))
        count_match = _GPU_GRES_RE.search(gres)
        if hostname and count_match:
            inventory[hostname] = (gres, int(count_match.group(1)))
    return [
        (row, *inventory[row["HOSTNAME"]])
        for row in compute_rows
        if row["HOSTNAME"] in inventory
    ]


def slurm_submission_rows(rows):
    """Return mapped Slurm roles allowed to submit jobs."""
    return [
        row
        for row in rows
        if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(SLURM_SUBMISSION_PREFIXES)
    ]


def ldap_test_username() -> str:
    """Return the validated non-secret LDAP test identity."""
    username = str(load_test_credentials().get("ldap_username") or "")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", username):
        raise ValueError("ldap_username is missing or invalid in test_creds.yml")
    return username


def require_functional(summary: str):
    """Require explicit authorization before creating temporary workloads."""
    return require_marker(
        summary,
        "functional",
        "Select the functional marker to authorize temporary workloads",
    )
