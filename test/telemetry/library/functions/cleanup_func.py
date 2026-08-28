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
Telemetry — Cleanup Verification Functions.

Functions for verifying that telemetry cleanup has properly removed
K8s resources (pods, PVCs, services, deployments, statefulsets)
from the telemetry namespace.
"""

from typing import Dict, Any, List

from omnia_auto import run_on_host

from library.vars.common_vars import (
    CMDS,
    TELEMETRY_NAMESPACE,
    IDRAC_POD_PREFIX,
    IDRAC_STS_NAME,
    LDMS_AGG_STS_NAME,
    LDMS_STORE_NAME,
    VECTOR_LDMS_APP_NAME,
    VECTOR_OME_APP_NAME,
    VM_POD_PREFIXES,
    VMAGENT_POD_PREFIX,
    VL_POD_PREFIXES,
    VLAGENT_POD_PREFIX,
    KAFKA_POD_PREFIXES,
    KAFKA_BRIDGE_PREFIX,
)


# =============================================================================
# HELPER — get pod count by prefix
# =============================================================================

def _get_pod_count_by_prefix(host, prefix, namespace=None):
    """Return count of pods matching a prefix in the namespace.

    Args:
        host: testinfra host connected to kube_vip.
        prefix: pod name prefix to search for.
        namespace: K8s namespace (default: telemetry).

    Returns:
        int: number of matching pods.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_pod_count"].format(namespace=ns, prefix=prefix)
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return 0
    try:
        return int(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0


def _get_resource_count(host, resource_type, namespace=None):
    """Return count of a K8s resource type in the namespace.

    Args:
        host: testinfra host connected to kube_vip.
        resource_type: K8s resource type (pods, pvc, svc, etc.).
        namespace: K8s namespace (default: telemetry).

    Returns:
        int: number of resources found.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_count_resources"].format(
        resource=resource_type, namespace=ns,
    )
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return 0
    try:
        return int(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0


# =============================================================================
# SOURCE CLEANUP VERIFICATION
# =============================================================================

def verify_idrac_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify iDRAC telemetry resources have been removed.

    Checks that no iDRAC pods (statefulset or standalone) remain.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    pod_count = _get_pod_count_by_prefix(host, IDRAC_POD_PREFIX, ns)
    if pod_count == 0:
        return {
            "success": True,
            "details": f"No iDRAC pods found in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Found {pod_count} iDRAC pod(s) still running",
        "error": f"{pod_count} iDRAC pod(s) remain in namespace '{ns}'",
    }


def verify_ldms_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify LDMS resources (aggregator + store + Vector-LDMS) removed.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    remaining = []
    for prefix, label in [
        (LDMS_AGG_STS_NAME, "LDMS aggregator"),
        (LDMS_STORE_NAME, "LDMS store"),
        (VECTOR_LDMS_APP_NAME, "Vector-LDMS bridge"),
    ]:
        count = _get_pod_count_by_prefix(host, prefix, ns)
        if count > 0:
            remaining.append(f"{label} ({count} pods)")

    if not remaining:
        return {
            "success": True,
            "details": f"No LDMS/Vector-LDMS pods in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Remaining: {', '.join(remaining)}",
        "error": f"LDMS resources still present: {', '.join(remaining)}",
    }


def verify_ome_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify OME resources (Vector-OME bridge) removed.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    count = _get_pod_count_by_prefix(host, VECTOR_OME_APP_NAME, ns)
    if count == 0:
        return {
            "success": True,
            "details": f"No Vector-OME pods in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Found {count} Vector-OME pod(s) still running",
        "error": f"{count} Vector-OME pod(s) remain in namespace '{ns}'",
    }


def verify_ufm_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify UFM telemetry resources removed.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    count = _get_pod_count_by_prefix(host, "ufm-external", ns)
    if count == 0:
        return {
            "success": True,
            "details": f"No UFM pods in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Found {count} UFM pod(s) still running",
        "error": f"{count} UFM pod(s) remain in namespace '{ns}'",
    }


def verify_vast_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify VAST telemetry resources removed.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    count = _get_pod_count_by_prefix(host, "vast-external", ns)
    if count == 0:
        return {
            "success": True,
            "details": f"No VAST pods in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Found {count} VAST pod(s) still running",
        "error": f"{count} VAST pod(s) remain in namespace '{ns}'",
    }


def verify_sfm_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify SFM telemetry resources removed.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    count = _get_pod_count_by_prefix(host, "sfm-telemetry", ns)
    if count == 0:
        return {
            "success": True,
            "details": f"No SFM pods in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Found {count} SFM pod(s) still running",
        "error": f"{count} SFM pod(s) remain in namespace '{ns}'",
    }


# =============================================================================
# SINK CLEANUP VERIFICATION
# =============================================================================

def verify_kafka_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify Kafka resources (cluster + bridge + operator) removed.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    remaining = []
    for prefix, label in [
        (KAFKA_POD_PREFIXES["broker"], "Kafka brokers"),
        (KAFKA_POD_PREFIXES["controller"], "Kafka controllers"),
        (KAFKA_BRIDGE_PREFIX, "Kafka bridge"),
        ("strimzi", "Strimzi operator"),
    ]:
        count = _get_pod_count_by_prefix(host, prefix, ns)
        if count > 0:
            remaining.append(f"{label} ({count} pods)")

    if not remaining:
        return {
            "success": True,
            "details": f"No Kafka pods in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Remaining: {', '.join(remaining)}",
        "error": f"Kafka resources still present: {', '.join(remaining)}",
    }


def verify_victoria_metrics_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify VictoriaMetrics resources removed.

    Checks vmstorage, vminsert, vmselect, vmagent, and operator pods.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    remaining = []
    for prefix, label in [
        (VM_POD_PREFIXES["vmstorage"], "vmstorage"),
        (VM_POD_PREFIXES["vminsert"], "vminsert"),
        (VM_POD_PREFIXES["vmselect"], "vmselect"),
        (VMAGENT_POD_PREFIX, "vmagent"),
        ("victoria-metrics-operator", "VM operator"),
    ]:
        count = _get_pod_count_by_prefix(host, prefix, ns)
        if count > 0:
            remaining.append(f"{label} ({count} pods)")

    if not remaining:
        return {
            "success": True,
            "details": f"No VictoriaMetrics pods in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Remaining: {', '.join(remaining)}",
        "error": (
            f"VictoriaMetrics resources still present: "
            f"{', '.join(remaining)}"
        ),
    }


def verify_victoria_logs_cleaned(host, namespace=None) -> Dict[str, Any]:
    """Verify VictoriaLogs resources removed.

    Checks vlstorage, vlinsert, vlselect, and vlagent pods.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    remaining = []
    for prefix, label in [
        (VL_POD_PREFIXES["vlstorage"], "vlstorage"),
        (VL_POD_PREFIXES["vlinsert"], "vlinsert"),
        (VL_POD_PREFIXES["vlselect"], "vlselect"),
        (VLAGENT_POD_PREFIX, "vlagent"),
    ]:
        count = _get_pod_count_by_prefix(host, prefix, ns)
        if count > 0:
            remaining.append(f"{label} ({count} pods)")

    if not remaining:
        return {
            "success": True,
            "details": f"No VictoriaLogs pods in namespace '{ns}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Remaining: {', '.join(remaining)}",
        "error": (
            f"VictoriaLogs resources still present: "
            f"{', '.join(remaining)}"
        ),
    }


# =============================================================================
# FINAL STATE VERIFICATION
# =============================================================================

def verify_no_pods_remaining(host, namespace=None) -> Dict[str, Any]:
    """Verify no pods remain in the telemetry namespace.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str),
                        count (int).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    count = _get_resource_count(host, "pods", ns)
    if count == 0:
        return {
            "success": True,
            "details": f"No pods in namespace '{ns}'",
            "error": "",
            "count": 0,
        }
    return {
        "success": False,
        "details": f"{count} pod(s) still present in namespace '{ns}'",
        "error": f"{count} pod(s) remain after full cleanup",
        "count": count,
    }


def verify_no_pvcs_remaining(host, namespace=None) -> Dict[str, Any]:
    """Verify no PVCs remain in the telemetry namespace.

    Args:
        host: testinfra host connected to kube_vip.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success (bool), details (str), error (str),
                        count (int).
    """
    ns = namespace or TELEMETRY_NAMESPACE
    count = _get_resource_count(host, "pvc", ns)
    if count == 0:
        return {
            "success": True,
            "details": f"No PVCs in namespace '{ns}'",
            "error": "",
            "count": 0,
        }
    return {
        "success": False,
        "details": f"{count} PVC(s) still present in namespace '{ns}'",
        "error": f"{count} PVC(s) remain after full cleanup",
        "count": count,
    }
