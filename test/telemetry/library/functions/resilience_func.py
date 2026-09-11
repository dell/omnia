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
Telemetry -- NFT Resilience Verification Functions.

Functions for testing Kubernetes pod resilience, recovery after
deletion, PVC persistence, service availability, data continuity,
and node reboot recovery.

All kubectl commands run on kube_vip via SSH from the OIM.
"""

import json
import time

from .telemetry_func import run_on_kube_vip, get_vmselect_endpoint, query_vm_instant
from ..vars.common_vars import TELEMETRY_NAMESPACE


# -------------------------------------------------------------------------
# Pod Deletion & Recovery
# -------------------------------------------------------------------------

def delete_pods_by_prefix(host, prefix, namespace=None):
    """Delete all pods matching a name prefix.

    Args:
        host: Testinfra host (OIM).
        prefix: Pod name prefix (e.g. 'kafka-broker').
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success, deleted_pods, count, error.
    """
    ns = namespace or TELEMETRY_NAMESPACE

    # Get pods matching prefix
    list_cmd = (
        f"kubectl get pods -n {ns} --no-headers "
        f"-o custom-columns=':metadata.name' 2>/dev/null "
        f"| grep '^{prefix}'"
    )
    result = run_on_kube_vip(host, list_cmd)
    pods = [
        p.strip() for p in result.stdout.strip().split("\n")
        if p.strip()
    ] if result.rc == 0 and result.stdout.strip() else []

    if not pods:
        return {
            "success": False,
            "deleted_pods": [],
            "count": 0,
            "error": f"No pods found matching prefix '{prefix}'",
        }

    # Delete each pod
    deleted = []
    for pod in pods:
        del_cmd = f"kubectl delete pod {pod} -n {ns} --grace-period=0 --force 2>&1"
        del_result = run_on_kube_vip(host, del_cmd)
        if del_result.rc == 0 or "deleted" in del_result.stdout.lower():
            deleted.append(pod)

    return {
        "success": len(deleted) > 0,
        "deleted_pods": deleted,
        "count": len(deleted),
        "error": "",
    }


def wait_pods_ready_by_prefix(host, prefix, expected=1, timeout=300,
                              poll_interval=10, namespace=None):
    """Wait until pods matching prefix reach Running+Ready state.

    Args:
        host: Testinfra host (OIM).
        prefix: Pod name prefix.
        expected: Minimum number of ready pods required.
        timeout: Maximum seconds to wait.
        poll_interval: Seconds between checks.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success, ready_count, expected, elapsed,
        pods, error.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    start = time.time()

    while True:
        elapsed = time.time() - start
        cmd = (
            f"kubectl get pods -n {ns} --no-headers "
            f"-o custom-columns=':metadata.name,:status.phase' 2>/dev/null "
            f"| grep '^{prefix}'"
        )
        result = run_on_kube_vip(host, cmd)
        pods = []
        ready_count = 0

        if result.rc == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 2:
                    name, phase = parts[0], parts[1]
                    is_running = phase == "Running"
                    pods.append({"name": name, "status": phase})
                    if is_running:
                        ready_count += 1

        if ready_count >= expected:
            return {
                "success": True,
                "ready_count": ready_count,
                "expected": expected,
                "elapsed": round(elapsed, 1),
                "pods": pods,
                "error": "",
            }

        if elapsed >= timeout:
            return {
                "success": False,
                "ready_count": ready_count,
                "expected": expected,
                "elapsed": round(elapsed, 1),
                "pods": pods,
                "error": (
                    f"Timeout after {timeout}s: {ready_count}/{expected} "
                    f"pods ready for prefix '{prefix}'"
                ),
            }

        time.sleep(poll_interval)


def verify_pod_recreation(host, prefix, expected=1, timeout=300,
                          namespace=None):
    """Delete pods matching prefix and verify they are recreated.

    This is the primary resilience test: force-delete pods and confirm
    Kubernetes controllers (Deployment/StatefulSet) recreate them.

    Args:
        host: Testinfra host (OIM).
        prefix: Pod name prefix.
        expected: Minimum pods expected after recreation.
        timeout: Max seconds to wait for recovery.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success, deleted, recovery, details, error.
    """
    # Step 1: Delete pods
    delete_result = delete_pods_by_prefix(host, prefix, namespace)
    if not delete_result["success"]:
        return {
            "success": False,
            "deleted": delete_result,
            "recovery": {},
            "details": f"No pods to delete for prefix '{prefix}'",
            "error": delete_result["error"],
        }

    # Step 2: Brief pause to let controller detect deletion
    time.sleep(5)

    # Step 3: Wait for pods to be recreated
    recovery = wait_pods_ready_by_prefix(
        host, prefix, expected=expected, timeout=timeout, namespace=namespace,
    )

    details = (
        f"Deleted {delete_result['count']} pod(s): "
        f"{', '.join(delete_result['deleted_pods'])}. "
        f"Recovery: {recovery['ready_count']}/{recovery['expected']} ready "
        f"in {recovery['elapsed']}s"
    )

    return {
        "success": recovery["success"],
        "deleted": delete_result,
        "recovery": recovery,
        "details": details,
        "error": recovery.get("error", ""),
    }


# -------------------------------------------------------------------------
# PVC Persistence
# -------------------------------------------------------------------------

def verify_all_pvcs_bound(host, namespace=None):
    """Verify all PVCs in namespace are in Bound state.

    Args:
        host: Testinfra host (OIM).
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success, total, bound, not_bound, pvcs, details.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = (
        f"kubectl get pvc -n {ns} -o json 2>/dev/null"
    )
    result = run_on_kube_vip(host, cmd)

    pvcs = []
    bound = []
    not_bound = []

    if result.rc == 0 and result.stdout.strip():
        try:
            data = json.loads(result.stdout)
            for item in data.get("items", []):
                name = item["metadata"]["name"]
                phase = item["status"].get("phase", "Unknown")
                capacity = (
                    item.get("status", {})
                    .get("capacity", {})
                    .get("storage", "N/A")
                )
                pvcs.append({
                    "name": name,
                    "phase": phase,
                    "capacity": capacity,
                })
                if phase == "Bound":
                    bound.append(name)
                else:
                    not_bound.append(name)
        except (json.JSONDecodeError, KeyError):
            return {
                "success": False,
                "total": 0,
                "bound": 0,
                "not_bound": 0,
                "not_bound_names": [],
                "pvcs": [],
                "details": "Failed to parse PVC JSON",
            }

    total = len(pvcs)
    details = (
        f"{len(bound)}/{total} PVCs Bound"
        + (f". Not bound: {', '.join(not_bound)}" if not_bound else "")
    )

    return {
        "success": len(not_bound) == 0 and total > 0,
        "total": total,
        "bound": len(bound),
        "not_bound": len(not_bound),
        "not_bound_names": not_bound,
        "pvcs": pvcs,
        "details": details,
    }


# -------------------------------------------------------------------------
# Service Endpoint Availability
# -------------------------------------------------------------------------

def verify_service_endpoints_available(host, service_names, namespace=None):
    """Verify K8s services have active endpoints (not just exist).

    Args:
        host: Testinfra host (OIM).
        service_names: List of service names.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success, available, unavailable, details.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    available = []
    unavailable = []

    for svc in service_names:
        cmd = (
            f"kubectl get endpoints {svc} -n {ns} "
            f"-o jsonpath='{{.subsets}}' 2>/dev/null"
        )
        result = run_on_kube_vip(host, cmd)
        has_endpoints = (
            result.rc == 0
            and result.stdout.strip()
            and result.stdout.strip() != "[]"
            and result.stdout.strip() != ""
        )
        if has_endpoints:
            available.append(svc)
        else:
            unavailable.append(svc)

    details = (
        f"{len(available)}/{len(service_names)} services have endpoints"
        + (f". Missing endpoints: {', '.join(unavailable)}" if unavailable else "")
    )

    return {
        "success": len(unavailable) == 0,
        "available": available,
        "unavailable": unavailable,
        "details": details,
    }


# -------------------------------------------------------------------------
# Data Continuity (VictoriaMetrics)
# -------------------------------------------------------------------------

def verify_data_queryable_after_restart(host, query="up", min_results=1):
    """Verify VictoriaMetrics still returns data after a pod restart.

    Args:
        host: Testinfra host (OIM).
        query: PromQL query (default: 'up').
        min_results: Minimum expected result count.

    Returns:
        dict with keys: success, result_count, query, details, error.
    """
    ip, port = get_vmselect_endpoint(host)
    if not ip or not port:
        return {
            "success": False,
            "result_count": 0,
            "query": query,
            "details": "",
            "error": "vmselect endpoint not found",
        }

    results = query_vm_instant(host, query)
    count = len(results)

    return {
        "success": count >= min_results,
        "result_count": count,
        "query": query,
        "details": f"Query '{query}' returned {count} result(s)",
        "error": "" if count >= min_results else (
            f"Expected >= {min_results} results, got {count}"
        ),
    }


# -------------------------------------------------------------------------
# Node Reboot Recovery
# -------------------------------------------------------------------------

def reboot_node_and_wait(host, node_ip, wait_timeout=600, poll_interval=15):
    """Reboot a K8s node via SSH and wait for it to come back.

    Args:
        host: Testinfra host (OIM).
        node_ip: IP of the node to reboot.
        wait_timeout: Max seconds to wait for node to return.
        poll_interval: Seconds between connectivity checks.

    Returns:
        dict with keys: success, elapsed, error.
    """
    from omnia_auto import run_on_host

    # Trigger reboot (async, returns immediately)
    reboot_cmd = (
        f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "
        f"root@{node_ip} 'nohup reboot &>/dev/null &' 2>&1 || true"
    )
    run_on_host(host, reboot_cmd)

    # Wait for node to go down
    time.sleep(30)

    # Wait for node to come back
    start = time.time()
    while True:
        elapsed = time.time() - start
        ping_cmd = (
            f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "
            f"-o BatchMode=yes root@{node_ip} 'echo ok' 2>/dev/null"
        )
        result = run_on_host(host, ping_cmd)
        if result.rc == 0 and "ok" in result.stdout:
            return {
                "success": True,
                "elapsed": round(elapsed, 1),
                "error": "",
            }

        if elapsed >= wait_timeout:
            return {
                "success": False,
                "elapsed": round(elapsed, 1),
                "error": f"Node {node_ip} did not come back after {wait_timeout}s",
            }

        time.sleep(poll_interval)


def verify_pods_after_reboot(host, timeout=600, poll_interval=15,
                             namespace=None):
    """Verify all telemetry pods return to Running after node reboot.

    Waits for all pods to reach Running/Ready state.

    Args:
        host: Testinfra host (OIM).
        timeout: Max seconds to wait for pods.
        poll_interval: Seconds between checks.
        namespace: K8s namespace (default: telemetry).

    Returns:
        dict with keys: success, total_pods, running_count,
        not_running_count, elapsed, details.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    start = time.time()

    while True:
        elapsed = time.time() - start
        cmd = (
            f"kubectl get pods -n {ns} --no-headers "
            f"-o custom-columns=':metadata.name,:status.phase' 2>/dev/null"
        )
        result = run_on_kube_vip(host, cmd)
        running = 0
        not_running = 0
        total = 0
        not_running_pods = []

        if result.rc == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 2:
                    total += 1
                    if parts[1] in ("Running", "Completed", "Succeeded"):
                        running += 1
                    else:
                        not_running += 1
                        not_running_pods.append(f"{parts[0]}={parts[1]}")

        if total > 0 and not_running == 0:
            return {
                "success": True,
                "total_pods": total,
                "running_count": running,
                "not_running_count": 0,
                "elapsed": round(elapsed, 1),
                "details": f"All {total} pods Running after {elapsed:.0f}s",
            }

        if elapsed >= timeout:
            return {
                "success": False,
                "total_pods": total,
                "running_count": running,
                "not_running_count": not_running,
                "elapsed": round(elapsed, 1),
                "details": (
                    f"Timeout: {running}/{total} pods Running. "
                    f"Not ready: {', '.join(not_running_pods[:10])}"
                ),
            }

        time.sleep(poll_interval)


# -------------------------------------------------------------------------
# Operator Recovery
# -------------------------------------------------------------------------

def verify_operator_recovery(host, operator_prefix, cr_type, cr_name, jsonpath,
                             timeout=300, namespace=None,
                             cr_healthy_values=None):
    """Delete an operator pod and verify its CRs are still reconciled.

    Args:
        host: Testinfra host (OIM).
        operator_prefix: Pod prefix for the operator (e.g. 'victoria-metrics-operator').
        cr_type: Custom resource type (e.g., vmcluster, kafka).
        cr_name: Custom resource name.
        jsonpath: JSONPath expression to extract status.
        timeout: Max seconds to wait for operator recovery.
        namespace: K8s namespace (default: telemetry).
        cr_healthy_values: List of acceptable CR status values
            (e.g. ['operational', 'expanding']). If None, any non-empty
            output is treated as healthy.

    Returns:
        dict with keys: success, deleted, recovery, cr_healthy, details.
    """
    from .k8s_func import get_cr_status

    # Delete operator pod
    delete_result = delete_pods_by_prefix(host, operator_prefix, namespace)
    if not delete_result["success"]:
        return {
            "success": False,
            "deleted": delete_result,
            "recovery": {},
            "cr_healthy": False,
            "details": f"No operator pod found for '{operator_prefix}'",
        }

    time.sleep(5)

    # Wait for operator to come back
    recovery = wait_pods_ready_by_prefix(
        host, operator_prefix, expected=1, timeout=timeout, namespace=namespace,
    )

    if not recovery["success"]:
        return {
            "success": False,
            "deleted": delete_result,
            "recovery": recovery,
            "cr_healthy": False,
            "details": f"Operator '{operator_prefix}' did not recover",
        }

    # Give operator time to reconcile
    time.sleep(15)

    # Check if CRs are healthy using library function
    cr_result = get_cr_status(host, cr_type, cr_name, jsonpath, namespace)
    cr_output = cr_result["value"] if cr_result["success"] else ""

    if cr_healthy_values:
        cr_healthy = cr_output in cr_healthy_values
    else:
        cr_healthy = bool(cr_output)

    cr_status_str = cr_output if cr_output else "<empty>"
    details = (
        f"Operator '{operator_prefix}' recovered in {recovery['elapsed']}s. "
        f"CR status: {cr_status_str} "
        f"({'healthy' if cr_healthy else 'unhealthy'})"
    )

    return {
        "success": recovery["success"] and cr_healthy,
        "deleted": delete_result,
        "recovery": recovery,
        "cr_healthy": cr_healthy,
        "details": details,
    }
