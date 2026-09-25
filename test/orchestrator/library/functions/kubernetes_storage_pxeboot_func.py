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
    marker_is_authorized,
    remote_command,
    remote_json,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import kubernetes_context as _context
from ._workload_helpers import optional_skip as _skip


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
            "The default StorageClass does not match the deployment contract"
            if not ok
            else "",
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
            "Missing or unhealthy CSI components: " + ", ".join(failures)
            if failures
            else "",
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
            fields.append(("Cleanup", "passed" if cleanup_ok else "failed"))
            if not cleanup_ok:
                success = False
                error = "The isolated validation namespace was not removed"
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
