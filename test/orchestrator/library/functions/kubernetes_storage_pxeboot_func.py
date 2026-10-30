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

"""Kubernetes storage and isolated workload verification after PXE."""

import base64
import json
import re
import secrets
import shlex
from collections.abc import Mapping
from typing import Any

from ..vars.pxeboot_vars import (
    KUBERNETES_CSI_SNAPSHOT_POD_PREFIXES,
    KUBERNETES_TEST_IMAGE_DEFAULT,
    KUBERNETES_WAIT_TIMEOUT_SECONDS,
    PXEBOOT_COMMANDS,
)
from ._kubernetes_helpers import pod_ready
from ._pxeboot_helpers import (
    group_fields,
    marker_is_authorized,
    remote_command,
    remote_json,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import kubernetes_context as _context
from ._workload_helpers import optional_skip as _skip


def _kubernetes_nfs_storage(context, config) -> dict[str, str]:
    """Resolve the NFS storage selected by the deployed Kubernetes cluster."""
    storage_name = str(config.get("nfs_storage_name") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", storage_name):
        raise ValueError("service_k8s_cluster.nfs_storage_name is missing or invalid")
    mounts = context.get("storage_config", {}).get("mounts", [])
    if not isinstance(mounts, list):
        raise TypeError("storage_config.mounts must be a list")
    matches = [
        item
        for item in mounts
        if isinstance(item, Mapping) and item.get("name") == storage_name
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Storage '{storage_name}' must resolve to exactly one mount entry"
        )
    source = str(matches[0].get("source") or "").strip()
    mount_point = str(matches[0].get("mount_point") or "").rstrip("/")
    source_match = re.fullmatch(r"([A-Za-z0-9_.-]+):(/[A-Za-z0-9_./-]+)", source)
    if source_match is None:
        raise ValueError(f"Storage '{storage_name}' must use an NFS source")
    if not re.fullmatch(r"/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", mount_point):
        raise ValueError(f"Storage '{storage_name}' has an invalid mount point")
    return {
        "name": storage_name,
        "source": source,
        "server": source_match.group(1),
        "export": source_match.group(2),
        "mount_point": mount_point,
    }


def check_kubernetes_default_storage_class(host):
    """Verify exactly one product-selected default StorageClass."""
    summary = "Kubernetes default StorageClass"
    try:
        _runtime, rows, control, config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        payload = remote_json(
            host,
            control,
            PXEBOOT_COMMANDS["kubernetes_storage_classes"],
        )
        items = payload.get("items", []) if isinstance(payload, dict) else []
        defaults = []
        for item in items:
            metadata = item.get("metadata", {}) if isinstance(item, dict) else {}
            annotations = metadata.get("annotations") or {}
            if (
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
            ):
                defaults.append(str(metadata.get("name", "")))
        expected = (
            "ps01" if bool(config.get("enable_powerscale_csi", False)) else "nfs-client"
        )
        ok = defaults == [expected]
        return runtime_result(
            ok,
            summary,
            [
                ("Expected default", expected),
                ("Observed defaults", ", ".join(defaults) or "none"),
            ],
            (
                "The default StorageClass does not match the deployment contract"
                if not ok
                else ""
            ),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_kubernetes_snapshot_controller(host):
    """Verify snapshot-controller and PowerScale CSI pods when CSI is enabled."""
    summary = "Kubernetes PowerScale snapshot components"
    try:
        _runtime, rows, control, config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        if not bool(config.get("enable_powerscale_csi", False)):
            return _skip(summary, "PowerScale CSI is disabled")
        payload = remote_json(host, control, PXEBOOT_COMMANDS["kubernetes_pods"])
        items = payload.get("items", []) if isinstance(payload, dict) else []
        fields = []
        failures = []
        for prefix in KUBERNETES_CSI_SNAPSHOT_POD_PREFIXES:
            matches = [
                item
                for item in items
                if str(item.get("metadata", {}).get("name", "")).startswith(prefix)
            ]
            ready = sum(pod_ready(item) for item in matches)
            fields.append((prefix, f"{ready}/{len(matches)} ready"))
            if not matches or ready != len(matches):
                failures.append(prefix)
        return runtime_result(
            not failures,
            summary,
            fields,
            (
                "Missing or unhealthy CSI components: " + ", ".join(failures)
                if failures
                else ""
            ),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_kubernetes_nfs_provisioner_contract(host):
    """Verify the NFS provisioner and selected backend configuration."""
    summary = "Kubernetes NFS provisioner and backend contract"
    try:
        context, rows, control, config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        storage = _kubernetes_nfs_storage(context, config)
        storage_payload = remote_json(
            host,
            control,
            PXEBOOT_COMMANDS["kubernetes_storage_classes"],
        )
        storage_classes = [
            item
            for item in storage_payload.get("items", [])
            if isinstance(item, Mapping)
            and item.get("metadata", {}).get("name") == "nfs-client"
        ]
        if len(storage_classes) != 1:
            raise ValueError("Exactly one nfs-client StorageClass is required")
        storage_class = storage_classes[0]
        provisioner = str(storage_class.get("provisioner") or "")
        reclaim_policy = str(storage_class.get("reclaimPolicy") or "Delete")
        binding_mode = str(storage_class.get("volumeBindingMode") or "Immediate")
        storage_class_ok = (
            "nfs" in provisioner.lower()
            and provisioner != "kubernetes.io/no-provisioner"
            and reclaim_policy == "Retain"
            and binding_mode == "Immediate"
        )

        deployments_payload = remote_json(
            host,
            control,
            PXEBOOT_COMMANDS["kubernetes_deployments"],
        )
        provisioner_containers = []
        for deployment in deployments_payload.get("items", []):
            if not isinstance(deployment, Mapping):
                continue
            for container in (
                deployment.get("spec", {})
                .get("template", {})
                .get("spec", {})
                .get("containers", [])
            ):
                if not isinstance(container, Mapping):
                    continue
                identity = " ".join(
                    (
                        str(container.get("name") or ""),
                        str(container.get("image") or ""),
                    )
                ).lower()
                if "nfs-subdir-external-provisioner" in identity:
                    provisioner_containers.append(container)
        if len(provisioner_containers) != 1:
            raise ValueError(
                "Exactly one NFS subdirectory provisioner container is required"
            )
        environment = {
            str(entry.get("name") or ""): str(entry.get("value") or "")
            for entry in provisioner_containers[0].get("env", [])
            if isinstance(entry, Mapping)
        }
        backend_ok = (
            environment.get("NFS_SERVER") == storage["server"]
            and environment.get("NFS_PATH") == storage["export"]
        )

        mount_outcomes = {}
        for row in rows:
            mount_payload = remote_json(
                host,
                row,
                PXEBOOT_COMMANDS["mount_contract"]
                % shlex.quote(storage["mount_point"]),
            )
            filesystems = (
                mount_payload.get("filesystems", [])
                if isinstance(mount_payload, Mapping)
                else []
            )
            source = (
                str(filesystems[0].get("source") or "")
                if len(filesystems) == 1 and isinstance(filesystems[0], Mapping)
                else ""
            )
            mount_outcomes[row["HOSTNAME"]] = (
                source == storage["source"],
                f"source={source or 'missing'}",
            )
        mount_failures = [
            name for name, outcome in mount_outcomes.items() if not outcome[0]
        ]
        fields: list[tuple[str, object]] = [
            ("Storage name", storage["name"]),
            ("Configured NFS source", storage["source"]),
            (
                "StorageClass provisioner",
                f"{'✓' if 'nfs' in provisioner.lower() else '✗'} "
                + (provisioner or "missing"),
            ),
            (
                "Reclaim policy",
                f"{'✓' if reclaim_policy == 'Retain' else '✗'} {reclaim_policy}",
            ),
            (
                "Volume binding mode",
                f"{'✓' if binding_mode == 'Immediate' else '✗'} {binding_mode}",
            ),
            (
                "Provisioner backend",
                f"{'✓' if backend_ok else '✗'} "
                + f"{environment.get('NFS_SERVER', 'missing')}:"
                + f"{environment.get('NFS_PATH', 'missing')}",
            ),
        ]
        fields.extend(group_fields(rows, mount_outcomes))
        ok = storage_class_ok and backend_ok and not mount_failures
        error_parts = []
        if not storage_class_ok:
            sc_problems = []
            if "nfs" not in provisioner.lower():
                sc_problems.append(f"provisioner={provisioner or 'missing'}")
            if reclaim_policy != "Retain":
                sc_problems.append(f"reclaimPolicy={reclaim_policy}")
            if binding_mode != "Immediate":
                sc_problems.append(f"bindingMode={binding_mode}")
            error_parts.append(
                "StorageClass mismatch: " + ", ".join(sc_problems)
            )
        if not backend_ok:
            error_parts.append(
                f"provisioner backend mismatch: "
                f"NFS_SERVER={environment.get('NFS_SERVER', 'missing')} "
                f"NFS_PATH={environment.get('NFS_PATH', 'missing')}"
            )
        if mount_failures:
            error_parts.append(
                "NFS mount source mismatch on: " + ", ".join(mount_failures)
            )
        return runtime_result(
            ok,
            summary,
            fields,
            "; ".join(error_parts),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def _test_namespace() -> str:
    return f"omnia-fvt-{secrets.token_hex(4)}"


def _encoded_manifest(document: Mapping[str, Any]) -> str:
    payload = json.dumps(document, separators=(",", ":"), sort_keys=True)
    return base64.b64encode(payload.encode("utf-8")).decode("ascii")


def _test_image() -> str:
    return KUBERNETES_TEST_IMAGE_DEFAULT


def _functional_manifest(namespace: str, storage_class: str = "") -> dict[str, Any]:
    pod: dict[str, Any] = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "workload", "namespace": namespace},
        "spec": {
            "restartPolicy": "Never",
            "containers": [
                {
                    "name": "workload",
                    "image": _test_image(),
                    "command": ["sh", "-c", "echo omnia-fvt > /data/probe; sleep 30"],
                    "volumeMounts": [{"name": "data", "mountPath": "/data"}],
                }
            ],
            "volumes": [{"name": "data", "emptyDir": {}}],
        },
    }
    items: list[dict[str, Any]] = [pod]
    if storage_class:
        claim = {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {"name": "data", "namespace": namespace},
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "storageClassName": storage_class,
                "resources": {"requests": {"storage": "1Gi"}},
            },
        }
        pod["spec"]["volumes"] = [
            {"name": "data", "persistentVolumeClaim": {"claimName": "data"}}
        ]
        items.insert(0, claim)
    return {"apiVersion": "v1", "kind": "List", "items": items}


def _run_functional_manifest(host, control, storage_class: str = ""):
    namespace = _test_namespace()
    fields: list[tuple[str, object]] = [
        ("Test image", _test_image()),
        ("StorageClass", storage_class or "emptyDir"),
    ]
    created = False
    error = ""
    success = False
    cleanup_ok = True
    volume_name = ""
    delete_policy_ok = True
    try:
        create = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["kubernetes_namespace_create"] % namespace,
        )
        if create.rc != 0:
            error = "Could not create the isolated validation namespace"
        else:
            created = True
            encoded = _encoded_manifest(_functional_manifest(namespace, storage_class))
            apply_result = remote_command(
                host,
                control,
                PXEBOOT_COMMANDS["kubernetes_apply_base64"] % encoded,
            )
            if apply_result.rc != 0:
                error = "Could not apply the isolated validation workload"
            else:
                wait = remote_command(
                    host,
                    control,
                    PXEBOOT_COMMANDS["kubernetes_wait_pods"]
                    % (namespace, KUBERNETES_WAIT_TIMEOUT_SECONDS),
                )
                payload = remote_json(
                    host,
                    control,
                    PXEBOOT_COMMANDS["kubernetes_get_namespace"] % namespace,
                )
                items = payload.get("items", []) if isinstance(payload, dict) else []
                pods = [item for item in items if item.get("kind") == "Pod"]
                claims = [
                    item
                    for item in items
                    if item.get("kind") == "PersistentVolumeClaim"
                ]
                pod_ok = wait.rc == 0 and len(pods) == 1 and pod_ready(pods[0])
                claim_ok = not storage_class or (
                    len(claims) == 1
                    and claims[0].get("status", {}).get("phase") == "Bound"
                )
                if storage_class and len(claims) == 1:
                    volume_name = str(claims[0].get("spec", {}).get("volumeName") or "")
                    claim_ok = claim_ok and bool(volume_name)
                    if not re.fullmatch(
                        r"[a-z0-9](?:[-a-z0-9.]{0,251}[a-z0-9])?",
                        volume_name,
                    ):
                        raise ValueError(
                            "The validation claim returned an invalid PV name"
                        )
                    delete_policy = remote_command(
                        host,
                        control,
                        PXEBOOT_COMMANDS["kubernetes_set_test_pv_delete_policy"]
                        % volume_name,
                    )
                    delete_policy_ok = delete_policy.rc == 0
                scheduled_node = (
                    str(pods[0].get("spec", {}).get("nodeName") or "")
                    if len(pods) == 1
                    else ""
                )
                read_probe = remote_command(
                    host,
                    control,
                    PXEBOOT_COMMANDS["kubernetes_read_probe"] % namespace,
                )
                data_ok = (
                    read_probe.rc == 0 and read_probe.stdout.strip() == "omnia-fvt"
                )
                success = pod_ok and claim_ok and data_ok and delete_policy_ok
                fields.extend(
                    [
                        (
                            "Pod scheduling",
                            f"{'✓' if pod_ok else '✗'} "
                            + f"{scheduled_node or 'not scheduled'}",
                        ),
                        (
                            "PersistentVolumeClaim",
                            (
                                f"{'✓ Bound' if claim_ok else '✗ not Bound'}"
                                if storage_class
                                else "not applicable"
                            ),
                        ),
                        (
                            "Data write and read",
                            "✓ verified" if data_ok else "✗ failed",
                        ),
                    ]
                )
                error = (
                    "Validation workload, storage claim, or data probe failed"
                    if not success
                    else ""
                )
    finally:
        if created:
            cleanup = remote_command(
                host,
                control,
                PXEBOOT_COMMANDS["kubernetes_namespace_delete"] % namespace,
            )
            cleanup_ok = cleanup.rc == 0
            if volume_name:
                pv_cleanup = remote_command(
                    host,
                    control,
                    PXEBOOT_COMMANDS["kubernetes_delete_test_pv"] % volume_name,
                )
                cleanup_ok = cleanup_ok and pv_cleanup.rc == 0
            fields.append(("Cleanup", "passed" if cleanup_ok else "FAILED"))
            if not cleanup_ok:
                cleanup_error = (
                    "cleanup: namespace/PV removal failed "
                    f"(ns rc={cleanup.rc}"
                    + (f", pv rc={pv_cleanup.rc}" if volume_name else "")
                    + ")"
                )
                if not success:
                    error = f"{error}; {cleanup_error}"
                else:
                    success = False
                    error = cleanup_error
    return success, fields, error


def _functional_check(
    host,
    summary: str,
    storage_class: str = "",
):
    try:
        if not marker_is_authorized("functional"):
            return _skip(
                summary,
                "Select the functional marker to authorize temporary workloads",
            )
        _runtime, rows, control, config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        if storage_class == "ps01" and not bool(
            config.get("enable_powerscale_csi", False)
        ):
            return _skip(summary, "PowerScale CSI is disabled")
        success, fields, error = _run_functional_manifest(
            host,
            control,
            storage_class,
        )
        return runtime_result(success, summary, fields, error)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_kubernetes_workload_scheduling(host):
    """Create, verify, and remove one isolated schedulable workload."""
    return _functional_check(
        host,
        "Kubernetes workload scheduling",
    )


def check_kubernetes_nfs_dynamic_provisioning(host):
    """Create, bind, use, and remove one NFS-backed claim."""
    return _functional_check(
        host,
        "Kubernetes NFS dynamic provisioning",
        "nfs-client",
    )


def check_kubernetes_csi_dynamic_provisioning(host):
    """Create, bind, use, and remove one PowerScale-backed claim."""
    return _functional_check(
        host,
        "Kubernetes PowerScale dynamic provisioning",
        "ps01",
    )
