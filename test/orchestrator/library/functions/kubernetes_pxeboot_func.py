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

"""Kubernetes post-boot verification derived from supported product behavior."""

import ipaddress

from ..vars.pxeboot_vars import (
    KUBERNETES_CNI_POD_PREFIXES,
    KUBERNETES_CSI_POD_PREFIXES,
    PXEBOOT_COMMANDS,
)
from ._kubernetes_helpers import pod_ready, resolve_kubernetes_node
from ._pxeboot_helpers import (
    group_fields,
    remote_command,
    remote_json,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import kubernetes_context as _context
from ._workload_helpers import optional_skip as _skip


def _condition_true(conditions, condition_type: str) -> bool:
    return any(
        condition.get("type") == condition_type
        and str(condition.get("status", "")).lower() == "true"
        for condition in (conditions or [])
        if isinstance(condition, dict)
    )


def check_kubernetes_nodes(host):
    """Verify desired membership, readiness, CRI-O, and version consistency."""
    summary = "Kubernetes membership and node readiness"
    try:
        _runtime, rows, control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        payload = remote_json(host, control, PXEBOOT_COMMANDS["kubernetes_nodes"])
        items = payload.get("items", []) if isinstance(payload, dict) else []
        actual = {
            str(item.get("metadata", {}).get("name", "")): item
            for item in items
            if isinstance(item, dict)
        }
        outcomes = {}
        versions = set()
        matched_names = set()
        for row in rows:
            cluster_name, item = resolve_kubernetes_node(
                items,
                row["HOSTNAME"],
                row["ADMIN_IP"],
            )
            if item is None:
                outcomes[row["HOSTNAME"]] = {
                    "ok": False,
                    "cluster_name": "not registered",
                    "ready": False,
                    "version": "unknown",
                    "runtime": "unknown",
                }
                continue
            matched_names.add(cluster_name)
            status = item.get("status", {})
            node_info = status.get("nodeInfo", {})
            version = str(node_info.get("kubeletVersion", ""))
            runtime = str(node_info.get("containerRuntimeVersion", ""))
            ready = _condition_true(status.get("conditions"), "Ready")
            valid_runtime = runtime.startswith("cri-o://")
            if version:
                versions.add(version)
            outcomes[row["HOSTNAME"]] = {
                "ok": ready and valid_runtime,
                "cluster_name": cluster_name,
                "ready": ready,
                "version": version or "unknown",
                "runtime": runtime or "unknown",
            }
        unexpected = sorted(set(actual) - matched_names)
        failed = [name for name, outcome in outcomes.items() if not outcome["ok"]]
        if len(versions) > 1:
            failed.append("inconsistent-kubelet-versions")
        fields = [
            ("Desired Kubernetes nodes", len(rows)),
            ("Cluster nodes", len(actual)),
            ("Unexpected nodes", ", ".join(unexpected) or "none"),
        ]
        grouped = {}
        for row in rows:
            grouped.setdefault(row["EXPECTED_FUNCTIONAL_GROUP"], []).append(row)
        for group_name, group_rows in sorted(grouped.items()):
            passed = sum(outcomes[row["HOSTNAME"]]["ok"] for row in group_rows)
            fields.append(
                ("Functional group", f"[{group_name}] ({passed}/{len(group_rows)})")
            )
            for row in group_rows:
                outcome = outcomes[row["HOSTNAME"]]
                icon = "✓" if outcome["ok"] else "✗"
                fields.extend(
                    [
                        (f"  {row['HOSTNAME']}", f"{icon} {row['ADMIN_IP']}"),
                        (
                            "    Cluster identity",
                            f"{icon} {outcome['cluster_name']}",
                        ),
                        (
                            "    Ready state",
                            f"{'✓' if outcome['ready'] else '✗'} "
                            + f"{'Ready' if outcome['ready'] else 'NotReady'}",
                        ),
                        (
                            "    Kubelet",
                            f"{'✓' if outcome['version'] != 'unknown' else '✗'} "
                            + f"{outcome['version']}",
                        ),
                        (
                            "    Container runtime",
                            f"{'✓' if str(outcome['runtime']).startswith('cri-o://') else '✗'} "
                            + f"{outcome['runtime']}",
                        ),
                    ]
                )
        return runtime_result(
            not failed and not unexpected,
            summary,
            fields,
            "; ".join(
                part
                for part in (
                    "Invalid nodes: " + ", ".join(failed) if failed else "",
                    "Unexpected nodes: " + ", ".join(unexpected) if unexpected else "",
                )
                if part
            ),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_kubernetes_node_services(host):
    """Verify kubelet, CRI-O, and chronyd on every Kubernetes node."""
    summary = "Kubernetes node services"
    try:
        _runtime, rows, _control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        outcomes = {}
        for row in rows:
            states = {}
            for service in ("kubelet", "crio", "chronyd"):
                result = remote_command(
                    host,
                    row,
                    PXEBOOT_COMMANDS["node_services"] % service,
                )
                states[service] = result.stdout.strip() if result.rc == 0 else "failed"
            ok = all(state == "active" for state in states.values())
            outcomes[row["HOSTNAME"]] = {"ok": ok, "states": states}
        failed = [name for name, outcome in outcomes.items() if not outcome["ok"]]
        fields = []
        grouped = {}
        for row in rows:
            grouped.setdefault(row["EXPECTED_FUNCTIONAL_GROUP"], []).append(row)
        for group_name, group_rows in sorted(grouped.items()):
            passed = sum(outcomes[row["HOSTNAME"]]["ok"] for row in group_rows)
            fields.append(
                ("Functional group", f"[{group_name}] ({passed}/{len(group_rows)})")
            )
            for row in group_rows:
                outcome = outcomes[row["HOSTNAME"]]
                fields.append(
                    (
                        f"  {row['HOSTNAME']}",
                        f"{'✓' if outcome['ok'] else '✗'} {row['ADMIN_IP']}",
                    )
                )
                for service, state in outcome["states"].items():
                    fields.append(
                        (
                            f"    {service}",
                            f"{'✓' if state == 'active' else '✗'} {state}",
                        )
                    )
        return runtime_result(
            not failed,
            summary,
            fields,
            "Service failures: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_kubernetes_control_plane(host):
    """Verify API readiness, etcd membership, and control-plane static pods."""
    summary = "Kubernetes control plane and etcd"
    try:
        _runtime, rows, control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        readyz = remote_command(host, control, PXEBOOT_COMMANDS["kubernetes_readyz"])
        pods = remote_json(host, control, PXEBOOT_COMMANDS["kubernetes_pods"])
        pod_items = pods.get("items", []) if isinstance(pods, dict) else []
        control_rows = [
            row for row in rows if "control_plane" in row["EXPECTED_FUNCTIONAL_GROUP"]
        ]
        etcd_pods = [
            item
            for item in pod_items
            if str(item.get("metadata", {}).get("name", "")).startswith("etcd-")
        ]
        running_etcd = [
            item
            for item in etcd_pods
            if item.get("status", {}).get("phase") == "Running"
        ]
        ok = readyz.rc == 0 and len(running_etcd) == len(control_rows)
        fields = [
            ("API readyz", "passed" if readyz.rc == 0 else "failed"),
            ("Control-plane nodes", len(control_rows)),
            ("Running etcd members", len(running_etcd)),
        ]
        return runtime_result(
            ok,
            summary,
            fields,
            "API readiness or etcd member count is invalid" if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_kubernetes_system_pods(host):
    """Verify core, selected CNI, MetalLB, NFS, and optional CSI pods."""
    summary = "Kubernetes system workloads"
    try:
        context, rows, control, config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        payload = remote_json(host, control, PXEBOOT_COMMANDS["kubernetes_pods"])
        items = payload.get("items", []) if isinstance(payload, dict) else []
        cni = str(config.get("k8s_cni", "calico")).lower()
        control_count = sum(
            "control_plane" in row["EXPECTED_FUNCTIONAL_GROUP"] for row in rows
        )
        cluster_name = str(config.get("cluster_name") or "")
        ha_enabled = any(
            isinstance(entry, dict)
            and entry.get("cluster_name") == cluster_name
            and bool(entry.get("enable_k8s_ha", False))
            for entry in context["high_availability_config"].get(
                "service_k8s_cluster_ha",
                [],
            )
        )
        checks: list[tuple[str, str, int | None]] = [
            ("kube-system", "etcd-", control_count),
            ("kube-system", "kube-apiserver-", control_count),
            ("kube-system", "kube-controller-manager-", control_count),
            ("kube-system", "kube-scheduler-", control_count),
            ("kube-system", "kube-proxy-", len(rows)),
        ]
        if ha_enabled:
            checks.append(("kube-system", "kube-vip-", control_count))
        checks.append(("kube-system", "coredns-", None))
        checks.extend(
            (
                "kube-system",
                prefix,
                len(rows) if prefix in {"calico-node-", "kube-flannel-"} else None,
            )
            for prefix in KUBERNETES_CNI_POD_PREFIXES.get(cni, ())
        )
        checks.extend(
            [
                ("metallb-system", "controller-", None),
                ("metallb-system", "speaker-", len(rows)),
                (
                    "default",
                    "nfs-client-nfs-subdir-external-provisioner-",
                    None,
                ),
            ]
        )
        if bool(config.get("enable_powerscale_csi", False)):
            checks.extend(
                (
                    "kube-system" if prefix == "snapshot-controller-" else "isilon",
                    prefix,
                    None,
                )
                for prefix in KUBERNETES_CSI_POD_PREFIXES
            )
        fields = [
            ("Configured CNI", cni),
            ("Kubernetes HA", "enabled" if ha_enabled else "disabled"),
        ]
        failures = []
        for namespace, prefix, expected_count in checks:
            matching = [
                item
                for item in items
                if str(item.get("metadata", {}).get("namespace", "")) == namespace
                if str(item.get("metadata", {}).get("name", "")).startswith(prefix)
            ]
            ready = sum(pod_ready(item) for item in matching)
            component = prefix.rstrip("-")
            count_ok = (
                len(matching) == expected_count
                if expected_count is not None
                else bool(matching)
            )
            component_ok = count_ok and ready == len(matching)
            expected_text = (
                str(expected_count) if expected_count is not None else "at least 1"
            )
            fields.append(
                (
                    f"  {namespace}/{component}",
                    f"{'✓' if component_ok else '✗'} "
                    + f"{ready}/{len(matching)} ready | expected={expected_text}",
                )
            )
            for pod in sorted(
                matching,
                key=lambda item: str(item.get("metadata", {}).get("name", "")),
            ):
                metadata = pod.get("metadata", {})
                status = pod.get("status", {})
                container_statuses = status.get("containerStatuses") or []
                ready_containers = sum(
                    bool(container.get("ready"))
                    for container in container_statuses
                    if isinstance(container, dict)
                )
                pod_ok = pod_ready(pod)
                fields.append(
                    (
                        f"    {metadata.get('name', 'unknown')}",
                        f"{'✓' if pod_ok else '✗'} "
                        + f"{status.get('phase', 'Unknown')} | "
                        + f"containers={ready_containers}/"
                        + f"{len(container_statuses)} ready | "
                        + f"node={pod.get('spec', {}).get('nodeName') or 'unassigned'}",
                    )
                )
            if not component_ok:
                failures.append(f"{namespace}/{component}")
        return runtime_result(
            not failures,
            summary,
            fields,
            "Missing or unhealthy workloads: " + ", ".join(failures)
            if failures
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_kubernetes_virtual_ip(host):
    """Verify the configured Kubernetes VIP is present on exactly one control plane."""
    summary = "Kubernetes virtual IP ownership"
    try:
        context, rows, _control, config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        cluster_name = str(config.get("cluster_name", ""))
        entries = context["high_availability_config"].get("service_k8s_cluster_ha", [])
        matches = [
            entry
            for entry in entries
            if isinstance(entry, dict) and entry.get("cluster_name") == cluster_name
        ]
        if len(matches) != 1:
            raise ValueError("Kubernetes HA configuration is missing or ambiguous")
        ha = matches[0]
        if not bool(ha.get("enable_k8s_ha", False)):
            return _skip(summary, "Kubernetes HA is disabled")
        vip = str(ipaddress.ip_address(str(ha.get("virtual_ip_address", ""))))
        owners = []
        fields = [("Virtual IP", vip)]
        for row in rows:
            if "control_plane" not in row["EXPECTED_FUNCTIONAL_GROUP"]:
                continue
            addresses = remote_json(host, row, PXEBOOT_COMMANDS["ip_addresses"])
            local_addresses = {
                str(info.get("local", ""))
                for interface in addresses
                for info in interface.get("addr_info", [])
                if isinstance(interface, dict) and isinstance(info, dict)
            }
            owns = vip in local_addresses
            if owns:
                owners.append(row["HOSTNAME"])
            fields.append(
                (
                    f"  {row['HOSTNAME']}",
                    f"✓ {row['ADMIN_IP']} | " + ("active owner" if owns else "standby"),
                )
            )
        ok = len(owners) == 1
        fields.append(("Active owners", ", ".join(owners) or "none"))
        return runtime_result(
            ok,
            summary,
            fields,
            f"Expected one VIP owner, found {len(owners)}" if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_kubernetes_storage(host):
    """Verify NFS storage and optional PowerScale CSI runtime objects."""
    summary = "Kubernetes storage"
    try:
        _runtime, rows, control, config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        payload = remote_json(host, control, PXEBOOT_COMMANDS["kubernetes_storage"])
        items = payload.get("items", []) if isinstance(payload, dict) else []
        storage_classes = [item for item in items if item.get("kind") == "StorageClass"]
        provisioners = {str(item.get("provisioner", "")) for item in storage_classes}
        nfs_present = any("nfs" in value for value in provisioners)
        csi_enabled = bool(config.get("enable_powerscale_csi", False))
        csi_present = "csi-isilon.dellemc.com" in provisioners
        persistent_volumes = [
            item for item in items if item.get("kind") == "PersistentVolume"
        ]
        claims = [item for item in items if item.get("kind") == "PersistentVolumeClaim"]
        unhealthy = []
        for item in items:
            kind = item.get("kind")
            phase = item.get("status", {}).get("phase")
            name = item.get("metadata", {}).get("name", "unknown")
            if kind == "PersistentVolume" and phase not in {"Available", "Bound"}:
                unhealthy.append(f"PV/{name}={phase}")
            if kind == "PersistentVolumeClaim" and phase != "Bound":
                unhealthy.append(f"PVC/{name}={phase}")
        ok = nfs_present and (not csi_enabled or csi_present) and not unhealthy
        fields: list[tuple[str, object]] = [
            ("Storage classes", len(storage_classes)),
        ]
        for item in sorted(
            storage_classes,
            key=lambda entry: str(entry.get("metadata", {}).get("name", "")),
        ):
            metadata = item.get("metadata", {})
            annotations = metadata.get("annotations") or {}
            default = (
                str(
                    annotations.get(
                        "storageclass.kubernetes.io/is-default-class",
                        annotations.get(
                            "storageclass.beta.kubernetes.io/is-default-class",
                            "false",
                        ),
                    )
                ).lower()
                == "true"
            )
            fields.append(
                (
                    f"  {metadata.get('name', 'unknown')}",
                    f"✓ provisioner={item.get('provisioner', 'unknown')} | "
                    + f"default={'yes' if default else 'no'}",
                )
            )
        fields.extend(
            [
                ("PersistentVolumes", len(persistent_volumes)),
                ("PersistentVolumeClaims", len(claims)),
                ("Unhealthy volumes", ", ".join(unhealthy) or "none"),
            ]
        )
        return runtime_result(
            ok,
            summary,
            fields,
            "Required storage objects are missing or unhealthy" if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_kubernetes_local_etcd(host):
    """Verify local-disk etcd mounts only when the feature is enabled."""
    summary = "Kubernetes local-disk etcd"
    try:
        _runtime, rows, _control, config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        if not bool(config.get("etcd_on_local_disk", False)):
            return _skip(summary, "etcd_on_local_disk is disabled")
        control_rows = [
            row for row in rows if "control_plane" in row["EXPECTED_FUNCTIONAL_GROUP"]
        ]
        outcomes = {}
        for row in control_rows:
            payload = remote_json(host, row, PXEBOOT_COMMANDS["etcd_mount"])
            filesystems = (
                payload.get("filesystems", []) if isinstance(payload, dict) else []
            )
            mount = filesystems[0] if filesystems else {}
            source = str(mount.get("source", ""))
            fstype = str(mount.get("fstype", "")).lower()
            ok = bool(source) and fstype not in {"", "nfs", "nfs4", "vfat", "fat"}
            outcomes[row["HOSTNAME"]] = (
                ok,
                f"source={source or 'missing'} | fstype={fstype or 'missing'}",
            )
        failed = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failed,
            summary,
            group_fields(control_rows, outcomes),
            "Invalid etcd mounts: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
