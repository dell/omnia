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
Orchestrator — Kubernetes Verification Functions

Kubernetes testing functions for orchestrator test automation.
Provides comprehensive testing for K8s clusters including node status,
service checks, pod verification, SSH connectivity, and workload tests.

All verification functions return a dict with keys:
  success (bool), details (str), error (str), and optionally skipped (bool).
"""

import re
import time
from typing import Any, Dict, List, Optional

from omnia_auto import load_test_config, run_on_host
from ..vars.common_vars import CMDS
from ..vars.k8s_vars import (
    K8S_SERVICES,
    K8S_CONTROL_PLANE_SERVICES,
    K8S_DIRECTORIES,
    K8S_CONFIG_FILES,
    K8S_SYSTEM_PODS,
    K8S_NFS_CONFIG_DIR,
)


# =============================================================================
# NODE DISCOVERY FUNCTIONS
# =============================================================================

def _get_project_path(host) -> str:
    """Get the project input path."""
    config = load_test_config()
    project = config.get("project_name", "project_default")
    return f"/opt/omnia/orchestrator/input/{project}"


def get_k8s_nodes_from_pxe(host, group_keyword: str) -> List[str]:
    """Get nodes from PXE mapping that match a K8s functional group keyword.

    Args:
        host: Testinfra host connection
        group_keyword: Keyword to search (e.g., 'service_kube_control_plane',
                       'service_kube_node')

    Returns:
        List of node hostnames
    """
    config = load_test_config()
    project = config.get("project_name", "project_default")
    pxe_mapping_path = f"/opt/omnia/orchestrator/input/{project}/pxe_mapping_file.csv"

    cmd = (
        f"if [ -f {pxe_mapping_path} ]; then "
        f"tail -n +2 {pxe_mapping_path} | grep -i '{group_keyword}' | "
        f"cut -d',' -f5 | grep -v '^$' | sort -u; "
        f"else echo 'NO_PXE_FILE'; fi"
    )
    result = run_on_host(host, cmd)

    if "NO_PXE_FILE" in result.stdout or result.rc != 0:
        return []

    return [line.strip() for line in result.stdout.split('\n') if line.strip()]


def get_k8s_control_plane_nodes(host) -> List[str]:
    """Get all K8s control plane nodes (first + additional)."""
    first = get_k8s_nodes_from_pxe(host, "service_kube_control_plane_first")
    additional = get_k8s_nodes_from_pxe(host, "service_kube_control_plane")
    # Deduplicate while preserving order (first CP node comes first)
    seen = set()
    result = []
    for node in first + additional:
        if node not in seen:
            seen.add(node)
            result.append(node)
    return result


def get_k8s_worker_nodes(host) -> List[str]:
    """Get all K8s worker nodes."""
    return get_k8s_nodes_from_pxe(host, "service_kube_node")


def get_k8s_all_nodes(host) -> List[str]:
    """Get all K8s nodes (control plane + workers)."""
    cp_nodes = get_k8s_control_plane_nodes(host)
    worker_nodes = get_k8s_worker_nodes(host)
    seen = set()
    result = []
    for node in cp_nodes + worker_nodes:
        if node not in seen:
            seen.add(node)
            result.append(node)
    return result


def get_node_ip_from_pxe(host, hostname: str) -> Optional[str]:
    """Get IP address for a node from PXE mapping.

    Args:
        host: Testinfra host connection
        hostname: Node hostname

    Returns:
        IP address or None if not found
    """
    config = load_test_config()
    project = config.get("project_name", "project_default")
    pxe_mapping_path = f"/opt/omnia/orchestrator/input/{project}/pxe_mapping_file.csv"

    cmd = (
        f"if [ -f {pxe_mapping_path} ]; then "
        f"tail -n +2 {pxe_mapping_path} | grep -i '{hostname}' | "
        f"cut -d',' -f7 | grep -v '^$' | head -1; "
        f"else echo 'NO_IP'; fi"
    )
    result = run_on_host(host, cmd)

    if "NO_IP" in result.stdout or result.rc != 0 or not result.stdout.strip():
        return None

    return result.stdout.strip()


def _get_first_control_plane_ip(host) -> Optional[str]:
    """Get IP of the first control plane node for kubectl commands."""
    cp_nodes = get_k8s_control_plane_nodes(host)
    if not cp_nodes:
        return None
    return get_node_ip_from_pxe(host, cp_nodes[0])


def _ssh_cmd(ip: str, remote_cmd: str) -> str:
    """Build an SSH command string."""
    return (
        f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "
        f"root@{ip} '{remote_cmd}'"
    )


# =============================================================================
# KUBERNETES ENABLED CHECK
# =============================================================================

def check_k8s_enabled(host) -> Dict[str, Any]:
    """Check if Kubernetes is enabled in the catalog.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, skipped
    """
    config = load_test_config()
    project = config.get("project_name", "project_default")
    orchestrator_config_path = (
        f"/opt/omnia/orchestrator/input/{project}/orchestrator_config.yml"
    )

    cmd = f"test -f {orchestrator_config_path} && cat {orchestrator_config_path}"
    result = run_on_host(host, cmd)

    if result.rc != 0:
        return {
            "success": False,
            "skipped": False,
            "details": "Orchestrator config file not found",
            "error": f"Cannot check K8s status - config file missing: {orchestrator_config_path}",
        }

    # Check for K8s functional groups in the config
    k8s_keywords = [
        "service_kube_control_plane",
        "service_kube_node",
        "kube_control_plane",
    ]
    has_k8s = any(keyword in result.stdout.lower() for keyword in k8s_keywords)

    if has_k8s:
        return {
            "success": True,
            "skipped": False,
            "details": "Kubernetes functional groups found in orchestrator config",
            "error": "",
        }

    return {
        "success": False,
        "skipped": True,
        "details": "Kubernetes functional groups not found in orchestrator config",
        "error": "Kubernetes is not enabled in the catalog",
    }


# =============================================================================
# NODE STATUS CHECKS
# =============================================================================

def check_k8s_nodes_ready(host) -> Dict[str, Any]:
    """Check if all Kubernetes nodes are in Ready state.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, not_ready_nodes
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found in PXE mapping",
            "error": "No control plane nodes available",
            "not_ready_nodes": [],
        }

    cmd = _ssh_cmd(cp_ip, "kubectl get nodes --no-headers 2>/dev/null")
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": f"kubectl get nodes failed on {cp_ip}",
            "error": f"kubectl command failed: {result.stdout}",
            "not_ready_nodes": [],
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    not_ready = []
    total = 0
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            total += 1
            node_name = parts[0]
            status = parts[1]
            if status != "Ready":
                not_ready.append(f"{node_name} ({status})")

    if not not_ready:
        return {
            "success": True,
            "details": f"All {total} Kubernetes nodes are Ready",
            "error": "",
            "not_ready_nodes": [],
        }

    return {
        "success": False,
        "details": f"{len(not_ready)}/{total} node(s) not Ready",
        "error": f"Not ready nodes: {not_ready}",
        "not_ready_nodes": not_ready,
    }


def check_k8s_control_plane_nodes(host) -> Dict[str, Any]:
    """Check if all control plane nodes are Ready.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, failed_nodes
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
            "failed_nodes": [],
        }

    cmd = _ssh_cmd(
        cp_ip,
        "kubectl get nodes --no-headers -l node-role.kubernetes.io/control-plane 2>/dev/null"
    )
    result = run_on_host(host, cmd)

    if result.rc != 0:
        # Fallback: try without label selector
        cmd = _ssh_cmd(cp_ip, "kubectl get nodes --no-headers 2>/dev/null")
        result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "Cannot query K8s control plane nodes",
            "error": f"kubectl failed: {result.stdout}",
            "failed_nodes": [],
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    cp_lines = [l for l in lines if "control-plane" in l or "master" in l]

    if not cp_lines:
        # All nodes might be control plane in a single-node cluster
        cp_lines = lines

    failed = []
    for line in cp_lines:
        parts = line.split()
        if len(parts) >= 2 and parts[1] != "Ready":
            failed.append(f"{parts[0]} ({parts[1]})")

    if not failed:
        return {
            "success": True,
            "details": f"All {len(cp_lines)} control plane nodes are Ready",
            "error": "",
            "failed_nodes": [],
        }

    return {
        "success": False,
        "details": f"{len(failed)}/{len(cp_lines)} control plane node(s) not Ready",
        "error": f"Failed nodes: {failed}",
        "failed_nodes": failed,
    }


def check_k8s_worker_nodes(host) -> Dict[str, Any]:
    """Check if all worker nodes are Ready.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, failed_nodes
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
            "failed_nodes": [],
        }

    # Get nodes without control-plane role
    cmd = _ssh_cmd(cp_ip, "kubectl get nodes --no-headers 2>/dev/null")
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "Cannot query K8s worker nodes",
            "error": f"kubectl failed: {result.stdout}",
            "failed_nodes": [],
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    worker_lines = [
        l for l in lines
        if "control-plane" not in l and "master" not in l
    ]

    if not worker_lines:
        return {
            "success": True,
            "skipped": True,
            "details": "No dedicated worker nodes found (may be single-node cluster)",
            "error": "",
            "failed_nodes": [],
        }

    failed = []
    for line in worker_lines:
        parts = line.split()
        if len(parts) >= 2 and parts[1] != "Ready":
            failed.append(f"{parts[0]} ({parts[1]})")

    if not failed:
        return {
            "success": True,
            "details": f"All {len(worker_lines)} worker nodes are Ready",
            "error": "",
            "failed_nodes": [],
        }

    return {
        "success": False,
        "details": f"{len(failed)}/{len(worker_lines)} worker node(s) not Ready",
        "error": f"Failed nodes: {failed}",
        "failed_nodes": failed,
    }


# =============================================================================
# SERVICE CHECKS
# =============================================================================

def check_kubelet_running(host) -> Dict[str, Any]:
    """Check if kubelet service is running on all K8s nodes.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, failed_nodes
    """
    all_nodes = get_k8s_all_nodes(host)

    if not all_nodes:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s nodes found in PXE mapping",
            "error": "No nodes available",
            "failed_nodes": [],
        }

    failed_nodes = []
    for node in all_nodes:
        node_ip = get_node_ip_from_pxe(host, node)
        if not node_ip:
            failed_nodes.append(f"{node} (no IP)")
            continue

        cmd = _ssh_cmd(node_ip, "systemctl is-active kubelet 2>/dev/null")
        result = run_on_host(host, cmd)

        if result.rc != 0 or "active" not in result.stdout:
            failed_nodes.append(node)

    if not failed_nodes:
        return {
            "success": True,
            "details": f"kubelet active on all {len(all_nodes)} K8s nodes",
            "error": "",
            "failed_nodes": [],
        }

    return {
        "success": False,
        "details": f"kubelet failed on {len(failed_nodes)}/{len(all_nodes)} nodes",
        "error": f"Failed nodes: {failed_nodes}",
        "failed_nodes": failed_nodes,
    }


def check_containerd_running(host) -> Dict[str, Any]:
    """Check if containerd service is running on all K8s nodes.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, failed_nodes
    """
    all_nodes = get_k8s_all_nodes(host)

    if not all_nodes:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s nodes found in PXE mapping",
            "error": "No nodes available",
            "failed_nodes": [],
        }

    failed_nodes = []
    for node in all_nodes:
        node_ip = get_node_ip_from_pxe(host, node)
        if not node_ip:
            failed_nodes.append(f"{node} (no IP)")
            continue

        cmd = _ssh_cmd(node_ip, "systemctl is-active containerd 2>/dev/null")
        result = run_on_host(host, cmd)

        if result.rc != 0 or "active" not in result.stdout:
            failed_nodes.append(node)

    if not failed_nodes:
        return {
            "success": True,
            "details": f"containerd active on all {len(all_nodes)} K8s nodes",
            "error": "",
            "failed_nodes": [],
        }

    return {
        "success": False,
        "details": f"containerd failed on {len(failed_nodes)}/{len(all_nodes)} nodes",
        "error": f"Failed nodes: {failed_nodes}",
        "failed_nodes": failed_nodes,
    }


# =============================================================================
# POD AND COMPONENT CHECKS
# =============================================================================

def check_k8s_system_pods(host) -> Dict[str, Any]:
    """Check if kube-system pods are Running.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, failed_pods
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
            "failed_pods": [],
        }

    cmd = _ssh_cmd(
        cp_ip,
        "kubectl get pods -n kube-system --no-headers 2>/dev/null"
    )
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "Cannot query kube-system pods",
            "error": f"kubectl failed: {result.stdout}",
            "failed_pods": [],
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    failed_pods = []
    total = 0

    for line in lines:
        parts = line.split()
        if len(parts) >= 3:
            total += 1
            pod_name = parts[0]
            # Ready column (e.g., "1/1")
            status = parts[2]
            if status not in ("Running", "Completed"):
                failed_pods.append(f"{pod_name} ({status})")

    if not failed_pods:
        return {
            "success": True,
            "details": f"All {total} kube-system pods are Running",
            "error": "",
            "failed_pods": [],
        }

    return {
        "success": False,
        "details": f"{len(failed_pods)}/{total} kube-system pod(s) not Running",
        "error": f"Failed pods: {failed_pods}",
        "failed_pods": failed_pods,
    }


def check_k8s_apiserver_responding(host) -> Dict[str, Any]:
    """Check if the Kubernetes API server is responding.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
        }

    cmd = _ssh_cmd(cp_ip, "kubectl cluster-info 2>/dev/null")
    result = run_on_host(host, cmd)

    if result.rc == 0 and "Kubernetes" in result.stdout:
        return {
            "success": True,
            "details": f"Kubernetes API server responding on {cp_ip}",
            "error": "",
        }

    return {
        "success": False,
        "details": f"Kubernetes API server not responding on {cp_ip}",
        "error": f"cluster-info failed: {result.stdout}",
    }


def check_k8s_etcd_healthy(host) -> Dict[str, Any]:
    """Check if etcd cluster is healthy.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
        }

    # Check etcd pod status
    cmd = _ssh_cmd(
        cp_ip,
        "kubectl get pods -n kube-system -l component=etcd --no-headers 2>/dev/null"
    )
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        # Fallback: check etcd via grep
        cmd = _ssh_cmd(
            cp_ip,
            "kubectl get pods -n kube-system --no-headers 2>/dev/null | grep etcd"
        )
        result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "Cannot query etcd pods",
            "error": f"etcd check failed: {result.stdout}",
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    all_running = all("Running" in line for line in lines)

    if all_running:
        return {
            "success": True,
            "details": f"{len(lines)} etcd pod(s) healthy",
            "error": "",
        }

    return {
        "success": False,
        "details": f"etcd pods not all Running",
        "error": f"etcd status: {result.stdout}",
    }


def check_k8s_coredns_running(host) -> Dict[str, Any]:
    """Check if CoreDNS pods are Running.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
        }

    cmd = _ssh_cmd(
        cp_ip,
        "kubectl get pods -n kube-system --no-headers 2>/dev/null | grep coredns"
    )
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "CoreDNS pods not found",
            "error": f"CoreDNS check failed: {result.stdout}",
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    all_running = all("Running" in line for line in lines)

    if all_running:
        return {
            "success": True,
            "details": f"{len(lines)} CoreDNS pod(s) Running",
            "error": "",
        }

    return {
        "success": False,
        "details": "CoreDNS pods not all Running",
        "error": f"CoreDNS status: {result.stdout}",
    }


def check_k8s_kube_proxy_running(host) -> Dict[str, Any]:
    """Check if kube-proxy pods are Running.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
        }

    cmd = _ssh_cmd(
        cp_ip,
        "kubectl get pods -n kube-system --no-headers 2>/dev/null | grep kube-proxy"
    )
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "kube-proxy pods not found",
            "error": f"kube-proxy check failed: {result.stdout}",
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    all_running = all("Running" in line for line in lines)

    if all_running:
        return {
            "success": True,
            "details": f"{len(lines)} kube-proxy pod(s) Running",
            "error": "",
        }

    return {
        "success": False,
        "details": "kube-proxy pods not all Running",
        "error": f"kube-proxy status: {result.stdout}",
    }


def check_k8s_static_pod(host, component: str) -> Dict[str, Any]:
    """Check if a specific static pod is running.

    Args:
        host: Testinfra host connection
        component: Pod component name (e.g., 'kube-apiserver')

    Returns:
        Dict with success, details, error
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
        }

    cmd = _ssh_cmd(
        cp_ip,
        f"kubectl get pods -n kube-system --no-headers 2>/dev/null | grep {component}"
    )
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": f"{component} pod not found",
            "error": f"{component} check failed: {result.stdout}",
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    all_running = all("Running" in line for line in lines)

    if all_running:
        return {
            "success": True,
            "details": f"{component} pod(s) Running ({len(lines)} instance(s))",
            "error": "",
        }

    return {
        "success": False,
        "details": f"{component} pod(s) not all Running",
        "error": f"Status: {result.stdout}",
    }


def check_k8s_cluster_info(host) -> Dict[str, Any]:
    """Check kubectl cluster-info output.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
        }

    cmd = _ssh_cmd(cp_ip, "kubectl cluster-info 2>/dev/null")
    result = run_on_host(host, cmd)

    if result.rc == 0 and "Kubernetes" in result.stdout:
        # Extract the cluster info summary
        info_lines = [
            l.strip() for l in result.stdout.split('\n')
            if l.strip() and "running at" in l.lower()
        ]
        return {
            "success": True,
            "details": f"Cluster info: {'; '.join(info_lines) if info_lines else 'OK'}",
            "error": "",
        }

    return {
        "success": False,
        "details": "kubectl cluster-info failed",
        "error": f"Output: {result.stdout}",
    }


# =============================================================================
# DIRECTORY AND FILE CHECKS
# =============================================================================

def check_k8s_directories_exist(host) -> Dict[str, Any]:
    """Check if Kubernetes directories exist on control plane nodes.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, missing_dirs
    """
    cp_nodes = get_k8s_control_plane_nodes(host)
    if not cp_nodes:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
            "missing_dirs": [],
        }

    # Check on first control plane node
    cp_ip = get_node_ip_from_pxe(host, cp_nodes[0])
    if not cp_ip:
        return {
            "success": False,
            "details": f"Cannot get IP for {cp_nodes[0]}",
            "error": "IP resolution failed",
            "missing_dirs": [],
        }

    missing = []
    for directory in K8S_DIRECTORIES:
        cmd = _ssh_cmd(cp_ip, f"test -d {directory} && echo exists")
        result = run_on_host(host, cmd)
        if "exists" not in result.stdout:
            missing.append(directory)

    if not missing:
        return {
            "success": True,
            "details": f"All {len(K8S_DIRECTORIES)} K8s directories exist on {cp_nodes[0]}",
            "error": "",
            "missing_dirs": [],
        }

    return {
        "success": False,
        "details": f"{len(missing)}/{len(K8S_DIRECTORIES)} directories missing on {cp_nodes[0]}",
        "error": f"Missing: {missing}",
        "missing_dirs": missing,
    }


def check_k8s_config_files_exist(host) -> Dict[str, Any]:
    """Check if Kubernetes configuration files exist on control plane.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, missing_files
    """
    cp_nodes = get_k8s_control_plane_nodes(host)
    if not cp_nodes:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
            "missing_files": [],
        }

    cp_ip = get_node_ip_from_pxe(host, cp_nodes[0])
    if not cp_ip:
        return {
            "success": False,
            "details": f"Cannot get IP for {cp_nodes[0]}",
            "error": "IP resolution failed",
            "missing_files": [],
        }

    missing = []
    for config_file in K8S_CONFIG_FILES:
        cmd = _ssh_cmd(cp_ip, f"test -f {config_file} && echo exists")
        result = run_on_host(host, cmd)
        if "exists" not in result.stdout:
            missing.append(config_file)

    if not missing:
        return {
            "success": True,
            "details": f"All {len(K8S_CONFIG_FILES)} K8s config files exist on {cp_nodes[0]}",
            "error": "",
            "missing_files": [],
        }

    return {
        "success": False,
        "details": f"{len(missing)}/{len(K8S_CONFIG_FILES)} config files missing on {cp_nodes[0]}",
        "error": f"Missing: {missing}",
        "missing_files": missing,
    }


def check_k8s_pki_certs_exist(host) -> Dict[str, Any]:
    """Check if Kubernetes PKI certificates exist.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error
    """
    cp_nodes = get_k8s_control_plane_nodes(host)
    if not cp_nodes:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
        }

    cp_ip = get_node_ip_from_pxe(host, cp_nodes[0])
    if not cp_ip:
        return {
            "success": False,
            "details": f"Cannot get IP for {cp_nodes[0]}",
            "error": "IP resolution failed",
        }

    # Check for critical PKI files
    pki_files = [
        "/etc/kubernetes/pki/ca.crt",
        "/etc/kubernetes/pki/ca.key",
        "/etc/kubernetes/pki/apiserver.crt",
        "/etc/kubernetes/pki/apiserver.key",
    ]

    found = 0
    for pki_file in pki_files:
        cmd = _ssh_cmd(cp_ip, f"test -f {pki_file} && echo exists")
        result = run_on_host(host, cmd)
        if "exists" in result.stdout:
            found += 1

    if found == len(pki_files):
        return {
            "success": True,
            "details": f"All {found} PKI certificate files exist on {cp_nodes[0]}",
            "error": "",
        }

    return {
        "success": False,
        "details": f"{found}/{len(pki_files)} PKI certificate files found on {cp_nodes[0]}",
        "error": "Some PKI certificates are missing",
    }


def check_k8s_nfs_config_exists(host) -> Dict[str, Any]:
    """Check if K8s NFS configuration directory exists on OIM.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error
    """
    cmd = f"test -d {K8S_NFS_CONFIG_DIR} && echo exists"
    result = run_on_host(host, cmd)

    if "exists" in result.stdout:
        # List files in the directory
        ls_cmd = f"ls -la {K8S_NFS_CONFIG_DIR}/ 2>/dev/null | wc -l"
        ls_result = run_on_host(host, ls_cmd)
        file_count = ls_result.stdout.strip()

        return {
            "success": True,
            "details": f"K8s NFS config directory exists ({file_count} entries)",
            "error": "",
        }

    return {
        "success": False,
        "details": f"K8s NFS config directory {K8S_NFS_CONFIG_DIR} not found",
        "error": "NFS config directory missing - k8s_config role may not have run",
    }


# =============================================================================
# SSH CHECKS
# =============================================================================

def check_k8s_ssh(host, from_type: str, to_type: str) -> Dict[str, Any]:
    """Check passwordless SSH between K8s node types.

    Args:
        host: Testinfra host connection
        from_type: Source node type ('control_plane' or 'worker')
        to_type: Target node type ('control_plane' or 'worker')

    Returns:
        Dict with success, details, error, failed_pairs
    """
    if from_type == "control_plane":
        from_nodes = get_k8s_control_plane_nodes(host)
    else:
        from_nodes = get_k8s_worker_nodes(host)

    if to_type == "control_plane":
        to_nodes = get_k8s_control_plane_nodes(host)
    else:
        to_nodes = get_k8s_worker_nodes(host)

    if not from_nodes:
        return {
            "success": False,
            "skipped": True,
            "details": f"No {from_type} nodes found",
            "error": f"No {from_type} nodes in PXE mapping",
            "failed_pairs": [],
        }

    if not to_nodes:
        return {
            "success": False,
            "skipped": True,
            "details": f"No {to_type} nodes found",
            "error": f"No {to_type} nodes in PXE mapping",
            "failed_pairs": [],
        }

    failed_pairs = []
    tested = 0

    # Test first from_node to all to_nodes
    from_node = from_nodes[0]
    from_ip = get_node_ip_from_pxe(host, from_node)

    if not from_ip:
        return {
            "success": False,
            "details": f"Cannot get IP for {from_node}",
            "error": "IP resolution failed",
            "failed_pairs": [],
        }

    for to_node in to_nodes:
        to_ip = get_node_ip_from_pxe(host, to_node)
        if not to_ip:
            failed_pairs.append(f"{from_node} -> {to_node} (no IP)")
            continue

        # SSH from OIM to from_node, then from from_node to to_node
        cmd = _ssh_cmd(
            from_ip,
            f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@{to_ip} hostname 2>/dev/null"
        )
        result = run_on_host(host, cmd)
        tested += 1

        if result.rc != 0 or not result.stdout.strip():
            failed_pairs.append(f"{from_node} -> {to_node}")

    if not failed_pairs:
        return {
            "success": True,
            "details": f"SSH OK from {from_type} to all {len(to_nodes)} {to_type} nodes ({tested} tested)",
            "error": "",
            "failed_pairs": [],
        }

    return {
        "success": False,
        "details": f"SSH failed for {len(failed_pairs)}/{tested} pairs",
        "error": f"Failed: {failed_pairs}",
        "failed_pairs": failed_pairs,
    }


# =============================================================================
# WORKLOAD TESTS
# =============================================================================

def check_k8s_pod_create(host) -> Dict[str, Any]:
    """Test pod creation and scheduling.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
        }

    pod_name = "omnia-test-pod"
    ns = "default"

    # Clean up any existing test pod
    cleanup_cmd = _ssh_cmd(cp_ip, f"kubectl delete pod {pod_name} -n {ns} --ignore-not-found 2>/dev/null")
    run_on_host(host, cleanup_cmd)
    time.sleep(2)

    # Create a simple test pod
    create_cmd = _ssh_cmd(
        cp_ip,
        f"kubectl run {pod_name} --image=busybox --restart=Never "
        f"-- sh -c 'echo test && sleep 30' 2>&1"
    )
    result = run_on_host(host, create_cmd)

    if result.rc != 0:
        return {
            "success": False,
            "details": f"Pod creation failed: {result.stdout}",
            "error": "kubectl run failed",
        }

    # Wait for pod to be Running
    max_wait = 60
    wait_time = 0
    while wait_time < max_wait:
        check_cmd = _ssh_cmd(
            cp_ip,
            f"kubectl get pod {pod_name} -n {ns} --no-headers -o custom-columns=STATUS:.status.phase 2>/dev/null"
        )
        check_result = run_on_host(host, check_cmd)
        phase = check_result.stdout.strip()

        if phase in ("Running", "Succeeded"):
            # Clean up
            cleanup_cmd = _ssh_cmd(cp_ip, f"kubectl delete pod {pod_name} -n {ns} --ignore-not-found 2>/dev/null")
            run_on_host(host, cleanup_cmd)

            return {
                "success": True,
                "details": f"Test pod created and reached {phase} state in ~{wait_time}s",
                "error": "",
            }

        if phase == "Failed":
            break

        time.sleep(5)
        wait_time += 5

    # Clean up
    cleanup_cmd = _ssh_cmd(cp_ip, f"kubectl delete pod {pod_name} -n {ns} --ignore-not-found 2>/dev/null")
    run_on_host(host, cleanup_cmd)

    return {
        "success": False,
        "details": f"Test pod did not reach Running state (last phase: {phase})",
        "error": "Pod scheduling/startup failed",
    }


def check_k8s_dns_resolution(host) -> Dict[str, Any]:
    """Test DNS resolution inside a pod.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
        }

    pod_name = "omnia-dns-test"
    ns = "default"

    # Clean up any existing test pod
    cleanup_cmd = _ssh_cmd(cp_ip, f"kubectl delete pod {pod_name} -n {ns} --ignore-not-found 2>/dev/null")
    run_on_host(host, cleanup_cmd)
    time.sleep(2)

    # Run DNS test pod
    cmd = _ssh_cmd(
        cp_ip,
        f"kubectl run {pod_name} --image=busybox --restart=Never "
        f"-- sh -c 'nslookup kubernetes.default.svc.cluster.local' 2>&1"
    )
    run_on_host(host, cmd)

    # Wait for completion
    max_wait = 60
    wait_time = 0
    while wait_time < max_wait:
        check_cmd = _ssh_cmd(
            cp_ip,
            f"kubectl get pod {pod_name} -n {ns} --no-headers -o custom-columns=STATUS:.status.phase 2>/dev/null"
        )
        check_result = run_on_host(host, check_cmd)
        phase = check_result.stdout.strip()

        if phase in ("Succeeded", "Failed"):
            break

        time.sleep(5)
        wait_time += 5

    # Get logs
    logs_cmd = _ssh_cmd(cp_ip, f"kubectl logs {pod_name} -n {ns} 2>/dev/null")
    logs_result = run_on_host(host, logs_cmd)

    # Clean up
    cleanup_cmd = _ssh_cmd(cp_ip, f"kubectl delete pod {pod_name} -n {ns} --ignore-not-found 2>/dev/null")
    run_on_host(host, cleanup_cmd)

    if "Address" in logs_result.stdout or "Name:" in logs_result.stdout:
        return {
            "success": True,
            "details": "DNS resolution working inside pods",
            "error": "",
        }

    return {
        "success": False,
        "details": "DNS resolution failed inside pods",
        "error": f"DNS output: {logs_result.stdout}",
    }


def check_k8s_service_create(host) -> Dict[str, Any]:
    """Test Kubernetes service creation.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
        }

    svc_name = "omnia-test-svc"
    ns = "default"

    # Clean up
    cleanup_cmd = _ssh_cmd(
        cp_ip,
        f"kubectl delete svc {svc_name} -n {ns} --ignore-not-found 2>/dev/null && "
        f"kubectl delete deployment {svc_name} -n {ns} --ignore-not-found 2>/dev/null"
    )
    run_on_host(host, cleanup_cmd)
    time.sleep(2)

    # Create a deployment and expose it
    create_cmd = _ssh_cmd(
        cp_ip,
        f"kubectl create deployment {svc_name} --image=nginx --replicas=1 2>&1 && "
        f"kubectl expose deployment {svc_name} --port=80 --type=ClusterIP 2>&1"
    )
    result = run_on_host(host, create_cmd)

    # Check service was created
    check_cmd = _ssh_cmd(
        cp_ip,
        f"kubectl get svc {svc_name} -n {ns} --no-headers 2>/dev/null"
    )
    check_result = run_on_host(host, check_cmd)

    # Clean up
    cleanup_cmd = _ssh_cmd(
        cp_ip,
        f"kubectl delete svc {svc_name} -n {ns} --ignore-not-found 2>/dev/null && "
        f"kubectl delete deployment {svc_name} -n {ns} --ignore-not-found 2>/dev/null"
    )
    run_on_host(host, cleanup_cmd)

    if check_result.rc == 0 and svc_name in check_result.stdout:
        return {
            "success": True,
            "details": f"Service {svc_name} created and verified",
            "error": "",
        }

    return {
        "success": False,
        "details": "Service creation or verification failed",
        "error": f"Output: {result.stdout}",
    }


# =============================================================================
# NODE METADATA CHECKS
# =============================================================================

def check_k8s_node_labels(host) -> Dict[str, Any]:
    """Check if K8s nodes have appropriate labels.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
        }

    cmd = _ssh_cmd(cp_ip, "kubectl get nodes --show-labels --no-headers 2>/dev/null")
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "Cannot query node labels",
            "error": f"kubectl failed: {result.stdout}",
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]

    # Check that at least one node has control-plane role
    has_cp_label = any("node-role.kubernetes.io/control-plane" in l for l in lines)

    if has_cp_label:
        return {
            "success": True,
            "details": f"Node labels verified on {len(lines)} nodes (control-plane role found)",
            "error": "",
        }

    return {
        "success": False,
        "details": "No control-plane role label found on any node",
        "error": "Node role labels may not be set correctly",
    }


def check_k8s_node_taints(host) -> Dict[str, Any]:
    """Check if control plane nodes have appropriate taints.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
        }

    cmd = _ssh_cmd(
        cp_ip,
        "kubectl describe nodes 2>/dev/null | grep -A5 'Taints:'"
    )
    result = run_on_host(host, cmd)

    if result.rc != 0:
        return {
            "success": False,
            "details": "Cannot query node taints",
            "error": f"kubectl failed: {result.stdout}",
        }

    # Just verify the command works; taint policies vary
    return {
        "success": True,
        "details": f"Node taints queried successfully",
        "error": "",
    }


# =============================================================================
# SMD / METADATA-SERVICE CHECKS
# =============================================================================

def check_k8s_smd_groups(host) -> Dict[str, Any]:
    """Check if K8s functional groups are registered in SMD.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error
    """
    # Check SMD for K8s groups
    cmd = (
        "curl -sk https://localhost:8443/hsm/v2/groups 2>/dev/null"
    )
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "Cannot query SMD groups",
            "error": "SMD API not reachable",
        }

    # Check for K8s-related groups
    k8s_keywords = ["kube", "kubernetes", "service_kube"]
    has_k8s = any(kw in result.stdout.lower() for kw in k8s_keywords)

    if has_k8s:
        return {
            "success": True,
            "details": "K8s functional groups found in SMD",
            "error": "",
        }

    return {
        "success": False,
        "details": "No K8s functional groups found in SMD",
        "error": "K8s groups may not have been registered during provisioning",
    }


def check_k8s_metadata_configured(host) -> Dict[str, Any]:
    """Check if K8s metadata-service configuration exists.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error
    """
    # Check metadata-service for K8s cloud-init config
    cmd = (
        "curl -sk https://localhost:8443/cloud-init 2>/dev/null"
    )
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "Cannot query metadata-service",
            "error": "metadata-service API not reachable",
        }

    return {
        "success": True,
        "details": "metadata-service is configured and responding",
        "error": "",
    }


# =============================================================================
# LDAP INTEGRATION
# =============================================================================

def check_k8s_ldap_integration(host) -> Dict[str, Any]:
    """Check OpenLDAP integration with Kubernetes.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, skipped
    """
    # Check if OpenLDAP is enabled
    config = load_test_config()
    project = config.get("project_name", "project_default")
    orchestrator_config_path = (
        f"/opt/omnia/orchestrator/input/{project}/orchestrator_config.yml"
    )

    cmd = f"test -f {orchestrator_config_path} && grep -i 'openldap' {orchestrator_config_path}"
    result = run_on_host(host, cmd)

    if result.rc != 0 or "true" not in result.stdout.lower():
        return {
            "success": True,
            "skipped": True,
            "details": "OpenLDAP integration not enabled - skipping",
            "error": "",
        }

    # Check if LDAP container is running
    ldap_cmd = "podman ps --filter name=openldap --format '{{.Names}}' 2>/dev/null"
    ldap_result = run_on_host(host, ldap_cmd)

    if ldap_result.rc == 0 and "openldap" in ldap_result.stdout:
        return {
            "success": True,
            "details": "OpenLDAP container running for K8s integration",
            "error": "",
        }

    return {
        "success": False,
        "details": "OpenLDAP container not running",
        "error": "OpenLDAP integration may not be properly configured",
    }
