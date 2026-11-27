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

"""Kafka local-disk post-boot verification functions.

Covers ER-ORCH-011 TC-FVT-030 (Kafka label follows node status) and
TC-FVT-032 (per-node status file and failure log line).
"""

from __future__ import annotations

import json
from typing import Any, Dict

from ..vars.pxeboot_vars import PXEBOOT_COMMANDS
from ._pxeboot_helpers import (
    group_fields,
    remote_command,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import kafka_declared
from ._workload_helpers import kubernetes_context as _context
from ._workload_helpers import optional_skip as _skip

_KAFKA_LABEL_KEY = "omnia.dell.com/kafka-storage"
_KAFKA_LABEL_VALUE = "true"
_NFS_K8S_MOUNT = "nfs_k8s"
_KAFKA_STATUS_SUBDIR = "kafka_disk_mapping"


def _nfs_k8s_mount_point(context: Any) -> str:
    """Resolve the nfs_k8s mount_point from storage_config.mounts."""
    mounts = context.get("storage_config", {}).get("mounts", [])
    matches = [
        e for e in mounts
        if isinstance(e, dict) and e.get("name") == _NFS_K8S_MOUNT
    ]
    if not matches:
        raise ValueError("No nfs_k8s mount entry found in storage_config")
    return str(matches[0].get("mount_point", "")).rstrip("/")


# ---------------------------------------------------------------------------
# TC-FVT-030: Kafka label follows node status
# ---------------------------------------------------------------------------

def check_kubernetes_kafka_node_label(host) -> Dict[str, Any]:  # pylint: disable=too-many-locals
    """TC-FVT-030: Kafka label is present on worker nodes whose disk status is ok.

    For every Kafka-declared worker node:
      - reads the per-node status file from the NFS share
      - checks whether the Kubernetes node carries the Kafka label
      - passes when status=ok implies label=true and status!=ok implies label absent
    """
    summary = "Kafka node label follows disk status"
    try:
        runtime, rows, control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        if not kafka_declared(runtime):
            return _skip(summary, "No Kafka local_storage entry declared")

        kafka_rows = [
            row for row in rows
            if "kube_node" in row.get("EXPECTED_FUNCTIONAL_GROUP", "")
        ]
        if not kafka_rows:
            return _skip(summary, "No Kafka worker rows in the approved map")

        nfs_mount = _nfs_k8s_mount_point(runtime)
        outcomes: dict[str, tuple[bool, str]] = {}
        for row in kafka_rows:
            node_ip = row["ADMIN_IP"]
            hostname = row["HOSTNAME"]

            # Read the per-node status file from the NFS share on the OIM
            status_cmd = PXEBOOT_COMMANDS["kafka_disk_status"] % (nfs_mount, node_ip)
            status_out = remote_command(host, control, status_cmd)
            status_data: dict[str, Any] = {}
            if status_out.rc == 0 and status_out.stdout.strip():
                try:
                    status_data = json.loads(status_out.stdout)
                except (ValueError, TypeError):
                    pass
            disk_status = str(status_data.get("result", "missing"))

            # Check the Kubernetes node label (nodes registered by IP in this cluster)
            label_cmd = PXEBOOT_COMMANDS["kafka_node_label"] % node_ip
            label_out = remote_command(host, control, label_cmd)
            has_label = label_out.rc == 0 and _KAFKA_LABEL_VALUE in label_out.stdout

            # Contract: label=true iff status=ok and no disable marker
            if disk_status == "ok":
                ok = has_label
                detail = (
                    f"status=ok | label={'present' if has_label else 'MISSING'}"
                )
            else:
                ok = not has_label
                detail = (
                    f"status={disk_status} | "
                    f"label={'correctly absent' if not has_label else 'UNEXPECTED'}"
                )
            outcomes[hostname] = (ok, detail)

        failed = [h for h, (ok, _) in outcomes.items() if not ok]
        return runtime_result(
            not failed,
            summary,
            group_fields(kafka_rows, outcomes),
            "Kafka label mismatch on: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-FVT-032: Per-node status file and failure log line
# ---------------------------------------------------------------------------

def check_kubernetes_kafka_disk_status(host) -> Dict[str, Any]:  # pylint: disable=too-many-locals
    """TC-FVT-032: Per-node status file exists and has a valid result field.

    For every Kafka-declared worker node reads status-<ip>.json from the NFS
    share and verifies:
      - the file exists and is valid JSON
      - the 'result' field is 'ok', 'failed' or 'disabled'
        ('disabled' = node_overrides enabled: false; no disk is prepared)
      - when result='failed', an ERROR log line exists in the disk-prep log
    """
    summary = "Kafka per-node disk status file"
    try:
        runtime, rows, control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        if not kafka_declared(runtime):
            return _skip(summary, "No Kafka local_storage entry declared")

        kafka_rows = [
            row for row in rows
            if "kube_node" in row.get("EXPECTED_FUNCTIONAL_GROUP", "")
        ]
        if not kafka_rows:
            return _skip(summary, "No Kafka worker rows in the approved map")

        nfs_mount = _nfs_k8s_mount_point(runtime)
        outcomes: dict[str, tuple[bool, str]] = {}
        for row in kafka_rows:
            node_ip = row["ADMIN_IP"]
            hostname = row["HOSTNAME"]

            status_cmd = PXEBOOT_COMMANDS["kafka_disk_status"] % (nfs_mount, node_ip)
            status_out = remote_command(host, control, status_cmd)

            if status_out.rc != 0 or not status_out.stdout.strip():
                outcomes[hostname] = (
                    False,
                    f"status file missing or unreadable for {node_ip}",
                )
                continue

            try:
                status_data = json.loads(status_out.stdout)
            except (ValueError, TypeError) as exc:
                outcomes[hostname] = (False, f"invalid JSON: {exc}")
                continue

            result = str(status_data.get("result", ""))
            if result not in ("ok", "failed", "disabled"):
                outcomes[hostname] = (
                    False,
                    f"unexpected result value: {result!r}",
                )
                continue

            if result == "failed":
                # The disk-prep log is node-local: read it on the failed node.
                log_cmd = PXEBOOT_COMMANDS["kafka_error_log"] % node_ip
                log_out = remote_command(host, row, log_cmd)
                has_error_line = log_out.rc == 0 and "ERROR" in log_out.stdout
                ok = has_error_line
                detail = (
                    f"result=failed | "
                    f"ERROR log line: {'present' if has_error_line else 'MISSING'}"
                )
            else:
                ok = True
                detail = f"result={result}"

            outcomes[hostname] = (ok, detail)

        failed = [h for h, (ok, _) in outcomes.items() if not ok]
        return runtime_result(
            not failed,
            summary,
            group_fields(kafka_rows, outcomes),
            "Status file issues on: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
