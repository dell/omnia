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
Telemetry — K8s Verification Functions.

Functions for verifying K8s cluster health and telemetry resources
via SSH to kube_vip.
"""

from omnia_auto import run_on_host

from library.vars.common_vars import CMDS, TELEMETRY_NAMESPACE


def verify_kubectl_available(host):
    """Check kubectl is available on the kube_vip host.

    Args:
        host: testinfra host connection to kube_vip.

    Returns:
        dict with keys: success (bool), version (str), error (str|None)
    """
    result = run_on_host(host, CMDS["kubectl_available"])
    if result.rc == 0 and result.stdout.strip():
        return {
            "success": True,
            "version": result.stdout.strip().split("\n")[0],
            "error": None,
        }
    return {
        "success": False,
        "version": "",
        "error": result.stderr.strip() if result.stderr else "kubectl not found",
    }


def verify_control_plane_ready(host):
    """Verify all K8s control plane nodes are in Ready state.

    Args:
        host: testinfra host connection to kube_vip.

    Returns:
        dict with keys: success, total, ready, not_ready, nodes (list)
    """
    result = run_on_host(host, CMDS["kubectl_get_control_plane"])
    if result.rc != 0:
        return {
            "success": False,
            "total": 0,
            "ready": 0,
            "not_ready": 0,
            "nodes": [],
            "error": result.stderr.strip() if result.stderr else "Failed to get nodes",
        }

    nodes = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2:
            node_name = parts[0]
            ready_status = parts[1]
            nodes.append({
                "name": node_name,
                "ready": ready_status == "True",
            })

    total = len(nodes)
    ready = sum(1 for n in nodes if n["ready"])
    not_ready = total - ready

    return {
        "success": not_ready == 0,
        "total": total,
        "ready": ready,
        "not_ready": not_ready,
        "nodes": nodes,
        "error": None,
    }


def verify_worker_nodes_ready(host):
    """Verify worker nodes meet minimum readiness threshold.

    Threshold logic (matches precheck.yml):
        1 worker  -> 1 Ready required
        2 workers -> 2 Ready required
        3+ workers -> at least 2 Ready required

    Args:
        host: testinfra host connection to kube_vip.

    Returns:
        dict with keys: success, total, ready, not_ready, minimum, nodes
    """
    result = run_on_host(host, CMDS["kubectl_get_workers"])
    if result.rc != 0:
        return {
            "success": False,
            "total": 0,
            "ready": 0,
            "not_ready": 0,
            "minimum": 0,
            "nodes": [],
            "error": result.stderr.strip() if result.stderr else "Failed to get workers",
        }

    nodes = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2:
            nodes.append({
                "name": parts[0],
                "ready": parts[1] == "True",
            })

    total = len(nodes)
    ready = sum(1 for n in nodes if n["ready"])
    not_ready = total - ready

    # Minimum threshold
    if total <= 2:
        minimum = total
    else:
        minimum = 2

    return {
        "success": ready >= minimum,
        "total": total,
        "ready": ready,
        "not_ready": not_ready,
        "minimum": minimum,
        "nodes": nodes,
        "error": None,
    }


def verify_pods_healthy(host, exclude_namespace=None):
    """Verify all pods (outside excluded namespace) are Running or Succeeded.

    Args:
        host: testinfra host connection to kube_vip.
        exclude_namespace: namespace to exclude (default: telemetry).

    Returns:
        dict with keys: success, total, healthy, unhealthy, unhealthy_pods
    """
    ns = exclude_namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_all_pods_status"].format(namespace=ns)
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {
            "success": False,
            "total": 0,
            "healthy": 0,
            "unhealthy": 0,
            "unhealthy_pods": [],
            "error": result.stderr.strip() if result.stderr else "Failed to get pods",
        }

    healthy_states = {"Running", "Succeeded"}
    pods = []
    unhealthy_pods = []

    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 3:
            pod_ns = parts[0]
            pod_name = parts[1]
            pod_status = parts[2]
            pod = {
                "namespace": pod_ns,
                "name": pod_name,
                "status": pod_status,
            }
            pods.append(pod)
            if pod_status not in healthy_states:
                unhealthy_pods.append(pod)

    total = len(pods)
    unhealthy = len(unhealthy_pods)

    return {
        "success": unhealthy == 0,
        "total": total,
        "healthy": total - unhealthy,
        "unhealthy": unhealthy,
        "unhealthy_pods": unhealthy_pods,
        "error": None,
    }


def verify_kube_vip_reachable(host, kube_vip):
    """Verify kube_vip is reachable via ping and SSH.

    Args:
        host: testinfra host connection (localhost or remote).
        kube_vip: IP address of the K8s control plane VIP.

    Returns:
        dict with keys: success, ping_ok, ssh_ok, error
    """
    # Ping check
    ping_cmd = CMDS["ping"].format(host=kube_vip)
    ping_result = run_on_host(host, ping_cmd)
    ping_ok = ping_result.rc == 0

    # SSH check
    ssh_cmd = CMDS["ssh_check"].format(user="root", host=kube_vip)
    ssh_result = run_on_host(host, ssh_cmd)
    ssh_ok = ssh_result.rc == 0

    return {
        "success": ping_ok and ssh_ok,
        "ping_ok": ping_ok,
        "ssh_ok": ssh_ok,
        "error": None if (ping_ok and ssh_ok) else (
            f"Ping: {'OK' if ping_ok else 'FAILED'}, "
            f"SSH: {'OK' if ssh_ok else 'FAILED'}"
        ),
    }


def get_pods_by_prefix(host, prefix, namespace=None):
    """Get pods matching a name prefix.

    Args:
        host: testinfra host connection to kube_vip.
        prefix: Pod name prefix to filter.
        namespace: K8s namespace (default: telemetry).

    Returns:
        list of dicts with keys: name, status, running
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_pods_by_prefix"].format(
        namespace=ns, prefix=prefix,
    )
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return []

    pods = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2:
            pods.append({
                "name": parts[0],
                "status": parts[1],
                "running": parts[1] == "Running",
            })
    return pods


def get_pod_count(host, prefix, namespace=None):
    """Get count of pods matching a name prefix.

    Args:
        host: testinfra host connection to kube_vip.
        prefix: Pod name prefix to filter.
        namespace: K8s namespace (default: telemetry).

    Returns:
        int: Number of matching pods.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_pod_count"].format(
        namespace=ns, prefix=prefix,
    )
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return 0
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def verify_secret_exists(host, secret_name, namespace=None):
    """Check if a K8s secret exists.

    Args:
        host: testinfra host connection to kube_vip.
        secret_name: Name of the secret.
        namespace: K8s namespace (default: telemetry).

    Returns:
        bool: True if secret exists.
    """
    ns = namespace or TELEMETRY_NAMESPACE
    cmd = CMDS["kubectl_get_secret"].format(
        secret_name=secret_name, namespace=ns,
    )
    result = run_on_host(host, cmd)
    return result.rc == 0 and "exists" in result.stdout
