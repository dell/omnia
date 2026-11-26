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

"""TopoLVM and Kafka StorageClass post-boot verification functions.

Covers ER-ORCH-011 Story 4 (ER-ORCH-011-topolvm-kafka-storageclass):
  - TC-FVT-012: TopoLVM installed only when a Kafka disk is declared, and
    capacity reported for the declared volume group (FR-3.1, AC-001, AC-007)
  - TC-FVT-013: Kafka StorageClass properties; default StorageClass unchanged
    (FR-3.2, AC-001, AC-002)

The temporary-claim check (bind, write, read, remove) lives with the other
dynamic-provisioning checks in kubernetes_storage_pxeboot_func.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Dict, List

from ..vars.pxeboot_vars import (
    KAFKA_STORAGE_LABEL_KEY,
    PXEBOOT_COMMANDS,
    TOPOLVM_CAPACITY_ANNOTATION_PREFIX,
    TOPOLVM_KAFKA_FSTYPE,
    TOPOLVM_KAFKA_STORAGECLASS,
    TOPOLVM_NAMESPACE,
    TOPOLVM_PROVISIONER,
)
from ._kubernetes_helpers import pod_ready
from ._pxeboot_helpers import (
    remote_json,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import kafka_declared
from ._workload_helpers import kubernetes_context as _context
from ._workload_helpers import optional_skip as _skip

_REQUIRED_SC_VOLUME_BINDING = "WaitForFirstConsumer"
_REQUIRED_SC_RECLAIM_POLICY = "Retain"
_DEFAULT_SC_ANNOTATION = "storageclass.kubernetes.io/is-default-class"
_DEFAULT_SC_ANNOTATION_BETA = "storageclass.beta.kubernetes.io/is-default-class"
_NFS_DEFAULT_SC = "nfs-client"
_POWERSCALE_DEFAULT_SC = "ps01"


def _sc_is_default(sc: Dict[str, Any]) -> bool:
    """Return True when the StorageClass carries a true default annotation."""
    annotations: Dict[str, str] = sc.get("metadata", {}).get("annotations") or {}
    for key in (_DEFAULT_SC_ANNOTATION, _DEFAULT_SC_ANNOTATION_BETA):
        if str(annotations.get(key, "false")).lower() == "true":
            return True
    return False


def _sc_name(sc: Dict[str, Any]) -> str:
    return str(sc.get("metadata", {}).get("name", "unknown"))


def _pod_name(pod: Dict[str, Any]) -> str:
    return str(pod.get("metadata", {}).get("name", "unknown"))


def _items(payload: Any) -> List[Dict[str, Any]]:
    """Return the items list of a kubectl JSON payload, or an empty list."""
    if isinstance(payload, Mapping):
        items = payload.get("items", [])
        return [item for item in items if isinstance(item, Mapping)]
    return []


def _declared_kafka_entry(runtime: Any) -> Dict[str, Any]:
    """Return the first purpose: kafka local_storage entry from the runtime context."""
    entries = runtime.get("storage_config", {}).get("local_storage", [])
    for entry in entries if isinstance(entries, list) else []:
        if isinstance(entry, Mapping) and entry.get("purpose") == "kafka":
            return dict(entry)
    return {}


def _declared_mount_options(entry: Mapping[str, Any]) -> List[str]:
    """Return the declared comma-separated mount_options as a list (FR-3.2)."""
    raw = str(entry.get("mount_options") or "")
    return [option.strip() for option in raw.split(",") if option.strip()]


# ---------------------------------------------------------------------------
# TC-FVT-012: TopoLVM installed only when a Kafka disk is declared
# ---------------------------------------------------------------------------

def check_topolvm_installed_when_kafka_declared(host) -> Dict[str, Any]:  # pylint: disable=too-many-locals
    """TC-FVT-012 (scenarios 1 and 3): TopoLVM present only when purpose: kafka is declared.

    Kafka declared: the Helm release is deployed, every pod in the TopoLVM
    namespace is Ready, and the Kafka StorageClass exists.
    Kafka not declared (AC-007): no release, no pods, and no Kafka StorageClass.
    """
    summary = "TopoLVM installed only when Kafka disk declared"
    try:
        runtime, rows, control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")

        kafka_present = kafka_declared(runtime)

        helm_out = remote_json(host, control, PXEBOOT_COMMANDS["topolvm_helm_status"])
        helm_deployed = (
            isinstance(helm_out, Mapping)
            and str(helm_out.get("info", {}).get("status", "")).lower() == "deployed"
        )

        pods = _items(remote_json(host, control, PXEBOOT_COMMANDS["topolvm_pods"]))
        not_ready = [_pod_name(p) for p in pods if not pod_ready(p)]

        sc_items = _items(remote_json(host, control, PXEBOOT_COMMANDS["topolvm_storageclasses"]))
        kafka_sc_present = any(_sc_name(sc) == TOPOLVM_KAFKA_STORAGECLASS for sc in sc_items)

        fields: list[tuple[str, object]] = [
            ("Kafka entry declared", kafka_present),
            ("Helm release status", "deployed" if helm_deployed else "absent/failed"),
            (f"Pods in {TOPOLVM_NAMESPACE}", len(pods)),
            ("Pods not Ready", ", ".join(not_ready) or "none"),
            (
                f"StorageClass {TOPOLVM_KAFKA_STORAGECLASS}",
                "present" if kafka_sc_present else "absent",
            ),
        ]

        error = ""
        if kafka_present:
            ok = helm_deployed and bool(pods) and not not_ready and kafka_sc_present
            if not helm_deployed:
                error = "TopoLVM Helm release is not deployed"
            elif not pods:
                error = f"No TopoLVM pods found in {TOPOLVM_NAMESPACE}"
            elif not_ready:
                error = f"TopoLVM pods not Ready: {', '.join(not_ready)}"
            elif not kafka_sc_present:
                error = f"StorageClass {TOPOLVM_KAFKA_STORAGECLASS} is absent"
        else:
            ok = not helm_deployed and not pods and not kafka_sc_present
            if helm_deployed:
                error = "TopoLVM Helm release is deployed but no Kafka disk was declared"
            elif pods:
                error = f"Found {len(pods)} pods in {TOPOLVM_NAMESPACE} but no Kafka disk was declared"
            elif kafka_sc_present:
                error = (
                    f"StorageClass {TOPOLVM_KAFKA_STORAGECLASS} exists but no Kafka disk was declared"
                )

        return runtime_result(ok, summary, fields, error)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_topolvm_capacity_per_node(host) -> Dict[str, Any]:
    """TC-FVT-012 (scenario 1): TopoLVM reports declared-VG capacity on every Kafka-labelled node.

    Skipped when no Kafka disk is declared or no node carries the Kafka label yet.
    """
    summary = "TopoLVM VG capacity reported per Kafka-labelled node"
    try:
        runtime, rows, control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        if not kafka_declared(runtime):
            return _skip(summary, "No Kafka local_storage entry declared")

        volume_group = str(_declared_kafka_entry(runtime).get("volume_group") or "")
        if not volume_group:
            return runtime_result(
                False, summary, [("Declared volume_group", "missing")],
                "The purpose: kafka entry declares no volume_group",
            )
        capacity_key = f"{TOPOLVM_CAPACITY_ANNOTATION_PREFIX}{volume_group}"

        nodes = _items(remote_json(host, control, PXEBOOT_COMMANDS["topolvm_node_capacity"]))
        labelled = [
            n for n in nodes
            if n.get("metadata", {}).get("labels", {}).get(KAFKA_STORAGE_LABEL_KEY) == "true"
        ]
        if not labelled:
            return _skip(summary, f"No nodes carry the {KAFKA_STORAGE_LABEL_KEY}=true label yet")

        outcomes: dict[str, tuple[bool, str]] = {}
        for node in labelled:
            name = str(node.get("metadata", {}).get("name", "unknown"))
            annotations = node.get("metadata", {}).get("annotations") or {}
            raw = annotations.get(capacity_key, "")
            try:
                capacity = int(raw)
                outcomes[name] = (capacity > 0, f"{capacity_key}={capacity} bytes")
            except (TypeError, ValueError):
                outcomes[name] = (False, f"{capacity_key}='{raw}' (expected integer bytes)")

        failed = [name for name, (ok, _) in outcomes.items() if not ok]
        return runtime_result(
            not failed,
            summary,
            [(name, detail) for name, (_, detail) in outcomes.items()],
            "Missing or zero TopoLVM capacity on: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-FVT-013: Kafka StorageClass properties; default StorageClass unchanged
# ---------------------------------------------------------------------------

def check_kafka_storageclass_properties(host) -> Dict[str, Any]:  # pylint: disable=too-many-locals
    """TC-FVT-013 (scenario 1): the Kafka StorageClass has every FR-3.2 property.

    Provisioner topolvm.io, WaitForFirstConsumer, Retain, allowVolumeExpansion,
    ext4, the declared volume group as device class, the declared mount options,
    and no default-class annotation. Skipped when no Kafka disk is declared.
    """
    summary = "Kafka StorageClass required properties"
    try:
        runtime, rows, control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        if not kafka_declared(runtime):
            return _skip(summary, "No Kafka local_storage entry declared")

        entry = _declared_kafka_entry(runtime)
        sc_items = _items(remote_json(host, control, PXEBOOT_COMMANDS["topolvm_storageclasses"]))
        kafka_scs = [sc for sc in sc_items if _sc_name(sc) == TOPOLVM_KAFKA_STORAGECLASS]
        if not kafka_scs:
            return runtime_result(
                False,
                summary,
                [("StorageClass", f"{TOPOLVM_KAFKA_STORAGECLASS} not found")],
                f"StorageClass {TOPOLVM_KAFKA_STORAGECLASS} does not exist",
            )

        sc = kafka_scs[0]
        parameters = sc.get("parameters") or {}
        expected_mounts = _declared_mount_options(entry)
        actual_mounts = [str(option) for option in sc.get("mountOptions") or []]
        checks = [
            ("provisioner", str(sc.get("provisioner", "")), TOPOLVM_PROVISIONER),
            ("volumeBindingMode", str(sc.get("volumeBindingMode", "")), _REQUIRED_SC_VOLUME_BINDING),
            ("reclaimPolicy", str(sc.get("reclaimPolicy", "")), _REQUIRED_SC_RECLAIM_POLICY),
            ("allowVolumeExpansion", sc.get("allowVolumeExpansion") is True, True),
            ("fstype", str(parameters.get("csi.storage.k8s.io/fstype", "")), TOPOLVM_KAFKA_FSTYPE),
            (
                "device-class",
                str(parameters.get("topolvm.io/device-class", "")),
                str(entry.get("volume_group") or ""),
            ),
            ("mountOptions", actual_mounts, expected_mounts),
            ("is-default-class annotation", _sc_is_default(sc), False),
        ]

        fields: list[tuple[str, object]] = [
            (attr, f"{'OK' if got == want else 'FAIL'}: got={got!r} want={want!r}")
            for attr, got, want in checks
        ]
        failures = [attr for attr, got, want in checks if got != want]
        return runtime_result(
            not failures,
            summary,
            fields,
            f"StorageClass property failures: {', '.join(failures)}" if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_default_storageclass_unchanged(host) -> Dict[str, Any]:
    """TC-FVT-013 (scenarios 1 and 2): the cluster default StorageClass is unchanged.

    Exactly one StorageClass is default, it is the expected one (nfs-client, or
    ps01 when PowerScale CSI is enabled), and it is never the Kafka StorageClass.
    """
    summary = "Default StorageClass unchanged after TopoLVM install"
    try:
        _runtime, rows, control, config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")

        expected = (
            _POWERSCALE_DEFAULT_SC
            if bool(config.get("enable_powerscale_csi", False))
            else _NFS_DEFAULT_SC
        )
        sc_items = _items(remote_json(host, control, PXEBOOT_COMMANDS["topolvm_storageclasses"]))
        default_names = [_sc_name(sc) for sc in sc_items if _sc_is_default(sc)]

        fields: list[tuple[str, object]] = [
            ("Expected default", expected),
            ("Default StorageClasses", ", ".join(default_names) or "none"),
            ("Kafka SC is default", TOPOLVM_KAFKA_STORAGECLASS in default_names),
        ]
        fields.extend(
            (
                f"  sc/{_sc_name(sc)}",
                f"default={'yes' if _sc_is_default(sc) else 'no'} "
                f"provisioner={sc.get('provisioner', 'unknown')}",
            )
            for sc in sc_items
        )

        error = ""
        if TOPOLVM_KAFKA_STORAGECLASS in default_names:
            error = f"{TOPOLVM_KAFKA_STORAGECLASS} must not be the default StorageClass (FR-3.2)"
        elif not default_names:
            error = "No default StorageClass found"
        elif len(default_names) > 1:
            error = f"Multiple default StorageClasses: {', '.join(default_names)}"
        elif default_names[0] != expected:
            error = f"Default StorageClass is {default_names[0]}, expected {expected}"
        return runtime_result(not error, summary, fields, error)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
