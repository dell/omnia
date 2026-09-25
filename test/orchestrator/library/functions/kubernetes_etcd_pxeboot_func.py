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

"""Kubernetes etcd health and topology verification after PXE."""

import json
from collections.abc import Mapping
from typing import Any

from ..vars.pxeboot_vars import ETCD_RAFT_INDEX_DELTA_MAX, PXEBOOT_COMMANDS
from ._kubernetes_helpers import pod_ready
from ._pxeboot_helpers import (
    remote_command,
    remote_json,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import kubernetes_context as _context
from ._workload_helpers import optional_skip as _skip


def _etcd_pod(host, control) -> str:
    payload = remote_json(host, control, PXEBOOT_COMMANDS["kubernetes_pods"])
    items = payload.get("items", []) if isinstance(payload, dict) else []
    matches = [
        str(item.get("metadata", {}).get("name", ""))
        for item in items
        if str(item.get("metadata", {}).get("namespace", "")) == "kube-system"
        and str(item.get("metadata", {}).get("name", "")).startswith("etcd-")
        and pod_ready(item)
    ]
    if not matches:
        raise ValueError("No ready kube-system etcd pod was found")
    return min(matches)


def _json_command(host, row, command: str) -> Any:
    result = remote_command(host, row, command)
    if result.rc != 0:
        raise RuntimeError("Kubernetes command returned a non-zero status")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("Kubernetes command returned invalid JSON") from exc


def check_kubernetes_etcd_health(host):
    """Verify every discovered etcd endpoint reports healthy."""
    summary = "Kubernetes etcd endpoint health"
    try:
        _runtime, rows, control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        pod = _etcd_pod(host, control)
        payload = _json_command(
            host,
            control,
            PXEBOOT_COMMANDS["kubernetes_etcd_health"] % pod,
        )
        endpoints = payload if isinstance(payload, list) else []
        unhealthy = [
            str(item.get("endpoint", "unknown"))
            for item in endpoints
            if not isinstance(item, dict) or not bool(item.get("health", False))
        ]
        expected = sum(
            "control_plane" in row["EXPECTED_FUNCTIONAL_GROUP"] for row in rows
        )
        ok = len(endpoints) == expected and not unhealthy
        fields: list[tuple[str, object]] = [
            ("Expected endpoints", expected),
            ("Healthy endpoints", f"{len(endpoints) - len(unhealthy)}/{expected}"),
        ]
        for item in endpoints:
            endpoint = str(item.get("endpoint") or "unknown")
            healthy = bool(item.get("health", False))
            fields.append(
                (
                    f"  {endpoint}",
                    f"{'✓ healthy' if healthy else '✗ unhealthy'}"
                    + (f" | latency={item.get('took')}" if item.get("took") else ""),
                )
            )
        return runtime_result(
            ok,
            summary,
            fields,
            "etcd endpoint health or endpoint count is invalid" if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def _status_value(item: Mapping[str, Any], *keys: str) -> Any:
    value: Any = item
    for key in keys:
        if not isinstance(value, Mapping):
            return None
        current = value
        value = current.get(key)
        if value is None:
            value = current.get(key.lower())
    return value


def check_kubernetes_etcd_topology(host):
    """Verify member count, one elected leader, and bounded raft divergence."""
    summary = "Kubernetes etcd membership and consistency"
    try:
        _runtime, rows, control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        pod = _etcd_pod(host, control)
        members_payload = _json_command(
            host,
            control,
            PXEBOOT_COMMANDS["kubernetes_etcd_members"] % pod,
        )
        status_payload = _json_command(
            host,
            control,
            PXEBOOT_COMMANDS["kubernetes_etcd_status"] % pod,
        )
        members = (
            members_payload.get("members", [])
            if isinstance(members_payload, dict)
            else []
        )
        statuses = status_payload if isinstance(status_payload, list) else []
        expected = sum(
            "control_plane" in row["EXPECTED_FUNCTIONAL_GROUP"] for row in rows
        )
        member_ids = {
            str(item.get("ID") or item.get("id") or "")
            for item in members
            if isinstance(item, dict)
        }
        member_ids.discard("")
        status_member_ids = {
            str(_status_value(item, "Status", "header", "member_id") or "")
            for item in statuses
            if isinstance(item, dict)
        }
        status_member_ids.discard("")
        leaders = {
            str(_status_value(item, "Status", "leader") or "")
            for item in statuses
            if isinstance(item, dict)
        }
        leaders.discard("")
        raft_indexes = [
            int(value)
            for item in statuses
            if isinstance(item, dict)
            for value in [_status_value(item, "Status", "raftIndex")]
            if str(value or "").isdigit()
        ]
        raft_terms = {
            str(_status_value(item, "Status", "raftTerm") or "")
            for item in statuses
            if isinstance(item, dict)
        }
        raft_terms.discard("")
        cluster_ids = {
            str(_status_value(item, "Status", "header", "cluster_id") or "")
            for item in statuses
            if isinstance(item, dict)
        }
        cluster_ids.discard("")
        delta = max(raft_indexes) - min(raft_indexes) if raft_indexes else -1
        ok = (
            len(members) == expected
            and len(statuses) == expected
            and len(member_ids) == expected
            and status_member_ids == member_ids
            and len(leaders) == 1
            and leaders.issubset(member_ids)
            and len(raft_indexes) == expected
            and len(raft_terms) == 1
            and len(cluster_ids) == 1
            and delta <= ETCD_RAFT_INDEX_DELTA_MAX
        )
        member_names = {
            str(item.get("ID") or item.get("id") or ""): str(
                item.get("name") or "unnamed"
            )
            for item in members
            if isinstance(item, dict)
        }
        leader_id = next(iter(leaders), "")
        fields: list[tuple[str, object]] = [
            ("Expected members", expected),
            ("Registered members", f"{len(members)}/{expected}"),
            ("Elected leader", member_names.get(leader_id, leader_id or "none")),
            ("Raft term", next(iter(raft_terms), "unknown")),
            ("Raft index delta", delta),
        ]
        for item in statuses:
            if not isinstance(item, dict):
                continue
            endpoint = str(item.get("Endpoint") or item.get("endpoint") or "unknown")
            member_id = str(_status_value(item, "Status", "header", "member_id") or "")
            index = _status_value(item, "Status", "raftIndex")
            version = _status_value(item, "Status", "version") or "unknown"
            role = "LEADER" if member_id == leader_id else "FOLLOWER"
            fields.append(
                (
                    f"  {member_names.get(member_id, endpoint)}",
                    f"✓ {role} | endpoint={endpoint} | "
                    + f"version={version} | raft-index={index}",
                )
            )
        return runtime_result(
            ok,
            summary,
            fields,
            "etcd membership, leader, or raft consistency is invalid" if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
