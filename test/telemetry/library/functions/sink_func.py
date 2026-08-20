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
Telemetry — Sink Verification Functions.

Functions for verifying VictoriaMetrics, VictoriaLogs, and Kafka
deployment status via SSH to kube_vip.
"""

from omnia_auto import run_on_host

from library.vars.common_vars import (
    CMDS,
    KAFKA_CR_NAME,
    KAFKA_POD_PREFIXES,
    TELEMETRY_NAMESPACE,
    VMAGENT_POD_PREFIX,
    VLAGENT_POD_PREFIX,
    VM_OPERATOR_DEPLOY,
    VM_POD_PREFIXES,
    VM_SERVICES,
    VL_POD_PREFIXES,
    VL_SERVICES,
)
from library.functions.k8s_func import get_pods_by_prefix, verify_secret_exists


# =============================================================================
# VictoriaMetrics Verification
# =============================================================================

def verify_vm_cluster_pods(host, namespace=None):
    """Verify VictoriaMetrics cluster pods (vmstorage, vminsert, vmselect).

    Returns:
        dict with keys: success, components (dict per component), total_running
    """
    ns = namespace or TELEMETRY_NAMESPACE
    components = {}
    all_running = True

    for component, prefix in VM_POD_PREFIXES.items():
        pods = get_pods_by_prefix(host, prefix, ns)
        running = [p for p in pods if p["running"]]
        components[component] = {
            "pods": pods,
            "running_count": len(running),
            "total_count": len(pods),
            "all_running": len(running) == len(pods) and len(pods) > 0,
        }
        if not components[component]["all_running"]:
            all_running = False

    return {
        "success": all_running and len(components) > 0,
        "components": components,
        "total_running": sum(c["running_count"] for c in components.values()),
    }


def verify_vmagent_pods(host, namespace=None):
    """Verify vmagent pods are running.

    Returns:
        dict with keys: success, running_count, total_count, pods
    """
    ns = namespace or TELEMETRY_NAMESPACE
    pods = get_pods_by_prefix(host, VMAGENT_POD_PREFIX, ns)
    running = [p for p in pods if p["running"]]
    return {
        "success": len(running) > 0 and len(running) == len(pods),
        "running_count": len(running),
        "total_count": len(pods),
        "pods": pods,
    }


def verify_vm_services(host, namespace=None):
    """Verify VictoriaMetrics services exist and have cluster IPs.

    Returns:
        dict with keys: success, services (list), missing (list)
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_svc"].format(namespace=ns)
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {"success": False, "services": [], "missing": list(VM_SERVICES.values())}

    found_services = result.stdout.strip()
    missing = []
    found = []
    for component, svc_name in VM_SERVICES.items():
        if svc_name in found_services:
            found.append(svc_name)
        else:
            missing.append(svc_name)

    return {
        "success": len(missing) == 0,
        "services": found,
        "missing": missing,
    }


def verify_vm_pvc_sizes(host, namespace=None):
    """Verify VictoriaMetrics PVC sizes.

    Returns:
        dict with keys: success, pvcs (list of dicts with name, capacity)
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_pvc"].format(namespace=ns)
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {"success": False, "pvcs": [], "error": "Failed to get PVCs"}

    pvcs = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2 and "vmstorage" in parts[0].lower():
            pvcs.append({"name": parts[0], "capacity": parts[1]})

    return {
        "success": len(pvcs) > 0,
        "pvcs": pvcs,
    }


def verify_vm_operator(host, namespace=None):
    """Verify VM operator deployment is ready.

    Returns:
        dict with keys: success, ready_replicas
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_deploy_ready"].format(
        name=VM_OPERATOR_DEPLOY, namespace=ns,
    )
    result = run_on_host(host, cmd)
    ready = 0
    if result.rc == 0 and result.stdout.strip():
        try:
            ready = int(result.stdout.strip())
        except ValueError:
            pass
    return {"success": ready > 0, "ready_replicas": ready}


# =============================================================================
# VictoriaLogs Verification
# =============================================================================

def verify_vl_cluster_pods(host, namespace=None):
    """Verify VictoriaLogs cluster pods (vlstorage, vlinsert, vlselect).

    Returns:
        dict with keys: success, components (dict per component), total_running
    """
    ns = namespace or TELEMETRY_NAMESPACE
    components = {}
    all_running = True

    for component, prefix in VL_POD_PREFIXES.items():
        pods = get_pods_by_prefix(host, prefix, ns)
        running = [p for p in pods if p["running"]]
        components[component] = {
            "pods": pods,
            "running_count": len(running),
            "total_count": len(pods),
            "all_running": len(running) == len(pods) and len(pods) > 0,
        }
        if not components[component]["all_running"]:
            all_running = False

    return {
        "success": all_running and len(components) > 0,
        "components": components,
        "total_running": sum(c["running_count"] for c in components.values()),
    }


def verify_vlagent_pods(host, namespace=None):
    """Verify vlagent pods are running.

    Returns:
        dict with keys: success, running_count, total_count, pods
    """
    ns = namespace or TELEMETRY_NAMESPACE
    pods = get_pods_by_prefix(host, VLAGENT_POD_PREFIX, ns)
    running = [p for p in pods if p["running"]]
    return {
        "success": len(running) > 0 and len(running) == len(pods),
        "running_count": len(running),
        "total_count": len(pods),
        "pods": pods,
    }


# =============================================================================
# Kafka Verification
# =============================================================================

def verify_kafka_pods(host, namespace=None):
    """Verify Kafka broker and controller pods are running.

    Returns:
        dict with keys: success, components (broker, controller), total_running
    """
    ns = namespace or TELEMETRY_NAMESPACE
    components = {}
    all_running = True

    for role, prefix in KAFKA_POD_PREFIXES.items():
        pods = get_pods_by_prefix(host, prefix, ns)
        running = [p for p in pods if p["running"]]
        components[role] = {
            "pods": pods,
            "running_count": len(running),
            "total_count": len(pods),
            "all_running": len(running) == len(pods) and len(pods) > 0,
        }
        if not components[role]["all_running"]:
            all_running = False

    return {
        "success": all_running and len(components) > 0,
        "components": components,
        "total_running": sum(c["running_count"] for c in components.values()),
    }


def verify_kafka_ready(host, namespace=None):
    """Verify Kafka CR reports Ready condition.

    Returns:
        dict with keys: success, status
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kafka_wait_ready"].format(
        kafka_cr=KAFKA_CR_NAME, namespace=ns,
    )
    result = run_on_host(host, cmd)
    ready = result.rc == 0 and "ready" in result.stdout.lower()
    return {"success": ready, "status": result.stdout.strip()}


def verify_kafka_topics(host, expected_topics, namespace=None):
    """Verify expected Kafka topics exist.

    Args:
        host: testinfra host connection.
        expected_topics: list of topic names to check.
        namespace: K8s namespace.

    Returns:
        dict with keys: success, found, missing, all_topics
    """
    ns = namespace or TELEMETRY_NAMESPACE
    # First get a broker pod name
    broker_prefix = KAFKA_POD_PREFIXES["broker"]
    pods = get_pods_by_prefix(host, broker_prefix, ns)
    if not pods:
        return {
            "success": False,
            "found": [],
            "missing": expected_topics,
            "all_topics": [],
            "error": "No Kafka broker pods found",
        }

    broker_pod = pods[0]["name"]
    cmd = CMDS["kafka_topics"].format(namespace=ns, broker_pod=broker_pod)
    result = run_on_host(host, cmd)
    if result.rc != 0:
        # Fallback: try KafkaTopic CRs
        cmd = CMDS["kafka_get_topics_cr"].format(namespace=ns)
        result = run_on_host(host, cmd)

    all_topics = [
        t.strip() for t in result.stdout.strip().split("\n")
        if t.strip() and not t.startswith("__")
    ]

    found = [t for t in expected_topics if t in all_topics]
    missing = [t for t in expected_topics if t not in all_topics]

    return {
        "success": len(missing) == 0,
        "found": found,
        "missing": missing,
        "all_topics": all_topics,
    }


def verify_kafka_bridge(host, namespace=None):
    """Verify Kafka bridge deployment is running (if deployed).

    Returns:
        dict with keys: success, running_count, pods
    """
    ns = namespace or TELEMETRY_NAMESPACE
    from library.vars.common_vars import KAFKA_BRIDGE_PREFIX
    pods = get_pods_by_prefix(host, KAFKA_BRIDGE_PREFIX, ns)
    running = [p for p in pods if p["running"]]
    # Bridge is optional; success if either no bridge pods OR all running
    if not pods:
        return {"success": True, "running_count": 0, "pods": [], "deployed": False}
    return {
        "success": len(running) == len(pods),
        "running_count": len(running),
        "pods": pods,
        "deployed": True,
    }


def verify_kafka_persistence(host, namespace=None):
    """Verify Kafka PVCs exist.

    Returns:
        dict with keys: success, pvcs (list)
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_pvc"].format(namespace=ns)
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {"success": False, "pvcs": [], "error": "Failed to get PVCs"}

    pvcs = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2 and "kafka" in parts[0].lower():
            pvcs.append({"name": parts[0], "capacity": parts[1]})

    return {
        "success": len(pvcs) > 0,
        "pvcs": pvcs,
    }
