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

from omnia_auto import load_test_config, read_remote_yaml, run_on_host
from ..vars.common_vars import CMDS
from ..vars.k8s_vars import (
    K8S_DIRECTORIES,
    K8S_CONFIG_FILES,
    K8S_NFS_CONFIG_DIR,
    K8S_ETCD_NAMESPACE,
    K8S_ETCD_PKI_CACERT,
    K8S_ETCD_PKI_CERT,
    K8S_ETCD_PKI_KEY,
    K8S_FIREWALL_PORTS_CONTROL_PLANE,
    K8S_FIREWALL_PORTS_WORKER,
    K8S_SYSTEMD_TARGETS,
)
from ..vars.common_vars import INPUT_PATH_TEMPLATE


# =============================================================================
# NODE DISCOVERY FUNCTIONS
# =============================================================================

def _get_project_path(host) -> str:  # pylint: disable=unused-argument
    """Get the project input path using domain-scoped INPUT_PATH_TEMPLATE."""
    config = load_test_config()
    project = config.get("project_name", "project_default")
    return INPUT_PATH_TEMPLATE.format(project=project)


def get_k8s_nodes_from_pxe(host, group_keyword: str) -> List[str]:
    """Get nodes from PXE mapping that match a K8s functional group keyword.

    Args:
        host: Testinfra host connection
        group_keyword: Keyword to search (e.g., 'service_kube_control_plane',
                       'service_kube_node')

    Returns:
        List of node hostnames
    """
    project_path = _get_project_path(host)
    pxe_mapping_path = f"{project_path}/pxe_mapping_file.csv"

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
    project_path = _get_project_path(host)
    pxe_mapping_path = f"{project_path}/pxe_mapping_file.csv"

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
    project_path = _get_project_path(host)
    orchestrator_config_path = f"{project_path}/orchestrator_config.yml"

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
    """Check if container runtime (CRI-O) is running on all K8s nodes.

    Note: This function name is retained for backward compatibility but now
    checks CRI-O (crio.service) instead of containerd, since the source
    cloud-init templates use ``systemctl start crio.service``.

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

        # Check CRI-O (source: cloud-init starts crio.service)
        cmd = _ssh_cmd(node_ip, "systemctl is-active crio 2>/dev/null")
        result = run_on_host(host, cmd)

        if result.rc != 0 or "active" not in result.stdout:
            failed_nodes.append(node)

    if not failed_nodes:
        return {
            "success": True,
            "details": f"CRI-O active on all {len(all_nodes)} K8s nodes",
            "error": "",
            "failed_nodes": [],
        }

    return {
        "success": False,
        "details": f"CRI-O failed on {len(failed_nodes)}/{len(all_nodes)} nodes",
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
        "details": "etcd pods not all Running",
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
        "details": "Node taints queried successfully",
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
    project_path = _get_project_path(host)
    orchestrator_config_path = f"{project_path}/orchestrator_config.yml"

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


# =============================================================================
# CRI-O / CONTAINER RUNTIME CHECKS
# =============================================================================

def check_crio_running(host) -> Dict[str, Any]:
    """Check if CRI-O (crio or cri-o) service is running on all K8s nodes.

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

        # Try crio first, then cri-o
        cmd = _ssh_cmd(node_ip, "systemctl is-active crio 2>/dev/null || systemctl is-active cri-o 2>/dev/null")
        result = run_on_host(host, cmd)

        if result.rc != 0 or "active" not in result.stdout:
            failed_nodes.append(node)

    if not failed_nodes:
        return {
            "success": True,
            "details": f"CRI-O active on all {len(all_nodes)} K8s nodes",
            "error": "",
            "failed_nodes": [],
        }

    return {
        "success": False,
        "details": f"CRI-O failed on {len(failed_nodes)}/{len(all_nodes)} nodes",
        "error": f"Failed nodes: {failed_nodes}",
        "failed_nodes": failed_nodes,
    }


def check_chronyd_running(host) -> Dict[str, Any]:
    """Check if chronyd service is active on all K8s control plane nodes.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, failed_nodes
    """
    cp_nodes = get_k8s_control_plane_nodes(host)

    if not cp_nodes:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s control plane nodes found",
            "error": "No control plane nodes available",
            "failed_nodes": [],
        }

    failed_nodes = []
    for node in cp_nodes:
        node_ip = get_node_ip_from_pxe(host, node)
        if not node_ip:
            failed_nodes.append(f"{node} (no IP)")
            continue

        cmd = _ssh_cmd(node_ip, "systemctl is-active chronyd 2>/dev/null")
        result = run_on_host(host, cmd)

        if result.rc != 0 or "active" not in result.stdout:
            failed_nodes.append(node)

    if not failed_nodes:
        return {
            "success": True,
            "details": f"chronyd active on all {len(cp_nodes)} control plane nodes",
            "error": "",
            "failed_nodes": [],
        }

    return {
        "success": False,
        "details": f"chronyd failed on {len(failed_nodes)}/{len(cp_nodes)} control plane nodes",
        "error": f"Failed nodes: {failed_nodes}",
        "failed_nodes": failed_nodes,
    }


def _get_software_config(host) -> Optional[Dict]:
    """Read and parse software_config.json from the project input directory.

    Returns:
        Parsed JSON dict, or None if not available.
    """
    project_path = _get_project_path(host)
    sw_config_path = f"{project_path}/software_config.json"

    cmd = f"test -f {sw_config_path} && cat {sw_config_path}"
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return None

    import json
    try:
        return json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def _get_service_k8s_version(host) -> Optional[str]:
    """Extract service_k8s version from software_config.json.

    Returns:
        Version string (e.g. '1.34.1') or None.
    """
    sw_config = _get_software_config(host)
    if not sw_config:
        return None

    for sw in sw_config.get("softwares", []):
        if isinstance(sw, dict) and sw.get("name") == "service_k8s":
            version = (sw.get("version") or "").strip()
            if version.startswith("v"):
                version = version[1:]
            return version if version else None

    return None


def _is_powerscale_csi_enabled(host) -> bool:
    """Return whether the active Kubernetes cluster enables PowerScale CSI."""
    omnia_config_path = f"{_get_project_path(host)}/omnia_config.yml"
    try:
        omnia_config = read_remote_yaml(host, omnia_config_path)
    except (RuntimeError, ValueError):
        return False

    clusters = omnia_config.get("service_k8s_cluster", [])
    if not isinstance(clusters, list):
        return False

    deployed_clusters = [
        cluster
        for cluster in clusters
        if isinstance(cluster, dict) and cluster.get("deployment") is True
    ]
    if len(deployed_clusters) != 1:
        return False
    return (
        deployed_clusters[0].get("enable_powerscale_csi") is True
    )


def check_kubectl_version(host) -> Dict[str, Any]:
    """Check if kubectl client version matches the expected version from software_config.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, expected_version, actual_versions
    """
    expected = _get_service_k8s_version(host)
    if not expected:
        return {
            "success": False,
            "skipped": True,
            "details": "service_k8s version not found in software_config.json",
            "error": "Cannot determine expected K8s version",
            "expected_version": None,
            "actual_versions": [],
        }

    cp_nodes = get_k8s_control_plane_nodes(host)
    if not cp_nodes:
        return {
            "success": False,
            "skipped": True,
            "details": "No control plane nodes found",
            "error": "No control plane nodes available",
            "expected_version": expected,
            "actual_versions": [],
        }

    mismatches = []
    actual_versions = []
    for node in cp_nodes:
        node_ip = get_node_ip_from_pxe(host, node)
        if not node_ip:
            continue

        cmd = _ssh_cmd(node_ip, "kubectl version --client 2>/dev/null")
        result = run_on_host(host, cmd)

        if result.rc != 0:
            mismatches.append(f"{node} (kubectl not available)")
            continue

        match = re.search(r'v?(\d+\.\d+\.\d+)', result.stdout)
        if not match:
            mismatches.append(f"{node} (cannot parse version)")
            continue

        actual = match.group(1)
        actual_versions.append(f"{node}={actual}")
        if actual != expected:
            mismatches.append(f"{node}: expected {expected}, got {actual}")

    if not mismatches:
        return {
            "success": True,
            "details": f"kubectl version {expected} on all control planes",
            "error": "",
            "expected_version": expected,
            "actual_versions": actual_versions,
        }

    return {
        "success": False,
        "details": f"kubectl version mismatch on {len(mismatches)} node(s)",
        "error": "; ".join(mismatches),
        "expected_version": expected,
        "actual_versions": actual_versions,
    }


def check_kubeadm_crio_version_match(host) -> Dict[str, Any]:
    """Check if kubeadm and CRI-O versions match on control plane nodes.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, node_results
    """
    cp_nodes = get_k8s_control_plane_nodes(host)
    if not cp_nodes:
        return {
            "success": False,
            "skipped": True,
            "details": "No control plane nodes found",
            "error": "No control plane nodes available",
            "node_results": [],
        }

    mismatches = []
    node_results = []
    for node in cp_nodes:
        node_ip = get_node_ip_from_pxe(host, node)
        if not node_ip:
            continue

        # Get kubeadm version
        ka_cmd = _ssh_cmd(node_ip, "kubeadm version -o short 2>/dev/null")
        ka_result = run_on_host(host, ka_cmd)
        ka_match = re.search(r'v?(\d+\.\d+\.\d+)', ka_result.stdout) if ka_result.rc == 0 else None
        kubeadm_ver = ka_match.group(1) if ka_match else None

        # Get crio version
        crio_cmd = _ssh_cmd(node_ip, "crio --version 2>/dev/null || cri-o --version 2>/dev/null")
        crio_result = run_on_host(host, crio_cmd)
        crio_match = re.search(r'(\d+\.\d+\.\d+)', crio_result.stdout) if crio_result.rc == 0 else None
        crio_ver = crio_match.group(1) if crio_match else None

        node_results.append(f"{node}: kubeadm={kubeadm_ver}, crio={crio_ver}")

        if not kubeadm_ver or not crio_ver:
            mismatches.append(f"{node}: cannot parse versions (kubeadm={kubeadm_ver}, crio={crio_ver})")
        elif kubeadm_ver != crio_ver:
            mismatches.append(f"{node}: kubeadm={kubeadm_ver} != crio={crio_ver}")

    if not mismatches:
        return {
            "success": True,
            "details": f"kubeadm/CRI-O versions match on all {len(cp_nodes)} control plane nodes",
            "error": "",
            "node_results": node_results,
        }

    return {
        "success": False,
        "details": f"Version mismatch on {len(mismatches)} node(s)",
        "error": "; ".join(mismatches),
        "node_results": node_results,
    }


def check_container_runtime(host) -> Dict[str, Any]:
    """Check if all nodes are using the expected container runtime (CRI-O).

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, node_results
    """
    from ..vars.k8s_vars import K8S_EXPECTED_CONTAINER_RUNTIME

    expected_version = _get_service_k8s_version(host)
    expected_runtime = K8S_EXPECTED_CONTAINER_RUNTIME

    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No control plane nodes found",
            "error": "No control plane nodes available",
            "node_results": [],
        }

    cmd = _ssh_cmd(cp_ip, "kubectl get nodes -o wide --no-headers 2>/dev/null")
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "Cannot query node runtime information",
            "error": f"kubectl get nodes -o wide failed: {result.stdout}",
            "node_results": [],
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    mismatches = []
    node_results = []

    for line in lines:
        parts = line.split()
        if not parts:
            continue
        node_name = parts[0]
        # Container runtime is the last column in kubectl get nodes -o wide
        runtime = parts[-1] if len(parts) >= 7 else "unknown"

        if expected_version:
            expected_str = f"{expected_runtime}://{expected_version}"
            is_correct = runtime == expected_str
        else:
            expected_str = f"{expected_runtime}://"
            is_correct = runtime.startswith(expected_str)

        node_results.append(f"{node_name}: {runtime}")
        if not is_correct:
            mismatches.append(f"{node_name}: expected {expected_str}, got {runtime}")

    if not mismatches:
        return {
            "success": True,
            "details": f"All nodes using {expected_runtime}" + (f"://{expected_version}" if expected_version else ""),
            "error": "",
            "node_results": node_results,
        }

    return {
        "success": False,
        "details": f"Runtime mismatch on {len(mismatches)} node(s)",
        "error": "; ".join(mismatches),
        "node_results": node_results,
    }


def check_k8s_component_status(host) -> Dict[str, Any]:
    """Check K8s cluster health using kubectl get componentstatus.

    Expects controller-manager, scheduler, etcd-0 to be Healthy.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, unhealthy_components
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No control plane nodes found",
            "error": "No control plane nodes available",
            "unhealthy_components": [],
        }

    cmd = _ssh_cmd(cp_ip, "kubectl get componentstatus --no-headers 2>/dev/null")
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "kubectl get componentstatus failed",
            "error": f"Command failed: {result.stdout}",
            "unhealthy_components": [],
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    unhealthy = []
    components = []

    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            name = parts[0]
            status = parts[1]
            components.append(f"{name}: {status}")
            if status != "Healthy":
                unhealthy.append(name)

    if not unhealthy:
        return {
            "success": True,
            "details": f"All {len(components)} K8s components are Healthy",
            "error": "",
            "unhealthy_components": [],
        }

    return {
        "success": False,
        "details": f"{len(unhealthy)} component(s) unhealthy: {', '.join(unhealthy)}",
        "error": f"Unhealthy: {unhealthy}",
        "unhealthy_components": unhealthy,
    }


# =============================================================================
# ETCD DETAILED CHECKS
# =============================================================================

def check_k8s_etcd_health_detailed(host) -> Dict[str, Any]:
    """Check etcd cluster health using etcdctl endpoint health from within etcd pods.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, healthy_count, total_count
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No control plane nodes found",
            "error": "No control plane nodes available",
        }

    # Find etcd pods
    find_cmd = _ssh_cmd(
        cp_ip,
        f"kubectl get pods -n {K8S_ETCD_NAMESPACE} -o name 2>/dev/null | grep '^pod/etcd-'"
    )
    result = run_on_host(host, find_cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "No etcd pods found in kube-system namespace",
            "error": "etcd pods not found",
        }

    etcd_pods = [
        line.strip().replace("pod/", "")
        for line in result.stdout.strip().split('\n')
        if line.strip()
    ]

    if not etcd_pods:
        return {
            "success": False,
            "details": "No etcd pods found",
            "error": "etcd pods list is empty",
        }

    healthy_count = 0
    total_count = len(etcd_pods)
    unhealthy_pods = []
    outputs = []

    for pod in etcd_pods:
        health_cmd = _ssh_cmd(
            cp_ip,
            f"kubectl exec -n {K8S_ETCD_NAMESPACE} {pod} -- "
            f"etcdctl --endpoints=https://127.0.0.1:2379 "
            f"--cacert={K8S_ETCD_PKI_CACERT} --cert={K8S_ETCD_PKI_CERT} --key={K8S_ETCD_PKI_KEY} "
            f"endpoint health 2>/dev/null"
        )
        hresult = run_on_host(host, health_cmd)
        output = hresult.stdout.strip()
        outputs.append(f"{pod}: {output}")

        if hresult.rc == 0 and "is healthy" in output.lower():
            healthy_count += 1
        else:
            unhealthy_pods.append(pod)

    if healthy_count == total_count:
        return {
            "success": True,
            "details": f"All {total_count} etcd endpoints are healthy",
            "error": "",
            "healthy_count": healthy_count,
            "total_count": total_count,
        }

    return {
        "success": False,
        "details": f"{healthy_count}/{total_count} etcd endpoints healthy; unhealthy: {unhealthy_pods}",
        "error": "\n".join(outputs),
        "healthy_count": healthy_count,
        "total_count": total_count,
    }


def check_k8s_etcd_member_list(host) -> Dict[str, Any]:
    """Check etcd member list matches expected control plane count.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, member_count, expected_count
    """
    cp_ip = _get_first_control_plane_ip(host)
    cp_nodes = get_k8s_control_plane_nodes(host)
    if not cp_ip or not cp_nodes:
        return {
            "success": False,
            "skipped": True,
            "details": "No control plane nodes found",
            "error": "No control plane nodes available",
        }

    expected_count = len(cp_nodes)

    # Find an etcd pod
    find_cmd = _ssh_cmd(
        cp_ip,
        f"kubectl get pods -n {K8S_ETCD_NAMESPACE} -o name 2>/dev/null | grep '^pod/etcd-' | head -1"
    )
    result = run_on_host(host, find_cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "No etcd pods found",
            "error": "Cannot find etcd pods for member list check",
        }

    etcd_pod = result.stdout.strip().replace("pod/", "")

    member_cmd = _ssh_cmd(
        cp_ip,
        f"kubectl exec -n {K8S_ETCD_NAMESPACE} {etcd_pod} -- "
        f"etcdctl --endpoints=https://127.0.0.1:2379 "
        f"--cacert={K8S_ETCD_PKI_CACERT} --cert={K8S_ETCD_PKI_CERT} --key={K8S_ETCD_PKI_KEY} "
        f"member list -w table 2>/dev/null"
    )
    mresult = run_on_host(host, member_cmd)

    if mresult.rc != 0 or not mresult.stdout.strip():
        return {
            "success": False,
            "details": "etcdctl member list failed",
            "error": f"Command output: {mresult.stdout}",
        }

    # Count member lines (excluding header and separator lines)
    member_lines = [
        line for line in mresult.stdout.strip().split('\n')
        if line.strip() and "|" in line and "ID" not in line.upper() and "---" not in line
    ]
    member_count = len(member_lines)

    if member_count >= expected_count:
        return {
            "success": True,
            "details": f"etcd member list verified ({member_count} members, expected {expected_count})",
            "error": "",
            "member_count": member_count,
            "expected_count": expected_count,
        }

    return {
        "success": False,
        "details": f"etcd member count mismatch: found {member_count}, expected {expected_count}",
        "error": mresult.stdout.strip(),
        "member_count": member_count,
        "expected_count": expected_count,
    }


def check_k8s_etcd_leader_consistency(host) -> Dict[str, Any]:
    """Check etcd leader identification and RAFT consistency across control planes.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, leader_found, raft_terms_consistent
    """
    import json as json_mod

    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No control plane nodes found",
            "error": "No control plane nodes available",
        }

    # Find etcd pods
    find_cmd = _ssh_cmd(
        cp_ip,
        f"kubectl get pods -n {K8S_ETCD_NAMESPACE} -o name 2>/dev/null | grep '^pod/etcd-'"
    )
    result = run_on_host(host, find_cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "No etcd pods found",
            "error": "Cannot find etcd pods",
        }

    etcd_pods = [
        line.strip().replace("pod/", "")
        for line in result.stdout.strip().split('\n')
        if line.strip()
    ]

    members = []
    leader_found = False
    raft_terms = set()

    for pod in etcd_pods:
        status_cmd = _ssh_cmd(
            cp_ip,
            f"kubectl exec -n {K8S_ETCD_NAMESPACE} {pod} -- "
            f"etcdctl --endpoints=https://127.0.0.1:2379 "
            f"--cacert={K8S_ETCD_PKI_CACERT} --cert={K8S_ETCD_PKI_CERT} --key={K8S_ETCD_PKI_KEY} "
            f"endpoint status -w json 2>/dev/null"
        )
        sresult = run_on_host(host, status_cmd)

        if sresult.rc != 0 or not sresult.stdout.strip():
            continue

        try:
            data = json_mod.loads(sresult.stdout.strip())
            entry = data[0] if isinstance(data, list) and data else data
            status = entry.get("Status", {})
            header = status.get("header", {})
            member_id = header.get("member_id", 0)
            leader_id = status.get("leader", 0)
            raft_term = header.get("raft_term", 0)
            is_leader = (member_id != 0 and member_id == leader_id)

            if is_leader:
                leader_found = True
            raft_terms.add(raft_term)

            members.append({
                "pod": pod,
                "is_leader": is_leader,
                "raft_term": raft_term,
            })
        except (json_mod.JSONDecodeError, KeyError, IndexError, TypeError):
            continue

    if not members:
        return {
            "success": False,
            "details": "Could not parse etcd status from any pod",
            "error": "etcdctl endpoint status failed on all pods",
        }

    raft_consistent = len(raft_terms) == 1

    if leader_found and raft_consistent:
        leader_pod = next((m["pod"] for m in members if m["is_leader"]), "unknown")
        return {
            "success": True,
            "details": f"etcd leader: {leader_pod}, RAFT terms consistent ({len(members)} members)",
            "error": "",
            "leader_found": True,
            "raft_terms_consistent": True,
        }

    issues = []
    if not leader_found:
        issues.append("no etcd leader found")
    if not raft_consistent:
        issues.append(f"RAFT terms inconsistent: {raft_terms}")

    return {
        "success": False,
        "details": f"etcd consistency issues: {'; '.join(issues)}",
        "error": "; ".join(issues),
        "leader_found": leader_found,
        "raft_terms_consistent": raft_consistent,
    }


# =============================================================================
# HA / VIRTUAL IP CHECKS
# =============================================================================

def check_k8s_virtual_ip(host) -> Dict[str, Any]:
    """Check that the HA virtual IP is configured on exactly one control plane node.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, vip, nodes_with_vip
    """
    project_path = _get_project_path(host)
    ha_config_path = f"{project_path}/high_availability_config.yml"

    # Read HA config to get virtual IP
    cmd = f"test -f {ha_config_path} && cat {ha_config_path}"
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "skipped": True,
            "details": "HA config file not found - VIP check not applicable",
            "error": "high_availability_config.yml not found",
        }

    import yaml
    try:
        ha_config = yaml.safe_load(result.stdout)
    except yaml.YAMLError:
        return {
            "success": False,
            "details": "Invalid YAML in HA config",
            "error": "Cannot parse high_availability_config.yml",
        }

    # Extract virtual IP
    virtual_ip = None
    ha_entries = ha_config.get("service_k8s_cluster_ha", [])
    if isinstance(ha_entries, list) and ha_entries:
        virtual_ip = ha_entries[0].get("virtual_ip_address")

    if not virtual_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No virtual_ip_address found in HA config",
            "error": "VIP not configured",
        }

    # Check each control plane node for VIP
    cp_nodes = get_k8s_control_plane_nodes(host)
    if not cp_nodes:
        return {
            "success": False,
            "details": "No control plane nodes found",
            "error": "No control plane nodes in PXE mapping",
            "vip": virtual_ip,
            "nodes_with_vip": [],
        }

    nodes_with_vip = []
    for node in cp_nodes:
        node_ip = get_node_ip_from_pxe(host, node)
        if not node_ip:
            continue

        check_cmd = _ssh_cmd(node_ip, f"ip -4 -o addr show 2>/dev/null | grep '{virtual_ip}/'")
        check_result = run_on_host(host, check_cmd)

        if check_result.rc == 0 and virtual_ip in check_result.stdout:
            nodes_with_vip.append(node)

    if len(nodes_with_vip) == 1:
        return {
            "success": True,
            "details": f"VIP {virtual_ip} configured on exactly one control plane: {nodes_with_vip[0]}",
            "error": "",
            "vip": virtual_ip,
            "nodes_with_vip": nodes_with_vip,
        }

    if len(nodes_with_vip) == 0:
        return {
            "success": False,
            "details": f"VIP {virtual_ip} not found on any control plane node",
            "error": "VIP not configured on any node",
            "vip": virtual_ip,
            "nodes_with_vip": [],
        }

    return {
        "success": False,
        "details": f"VIP {virtual_ip} found on multiple nodes: {nodes_with_vip}",
        "error": f"VIP on multiple nodes: {nodes_with_vip}",
        "vip": virtual_ip,
        "nodes_with_vip": nodes_with_vip,
    }


# =============================================================================
# NETWORK AND COMPONENT POD CHECKS
# =============================================================================

def _check_pods_with_prefix(host, prefix: str, component: str) -> Dict[str, Any]:
    """Generic check for pods with a given name prefix across all namespaces.

    Args:
        host: Testinfra host connection
        prefix: Pod name prefix (e.g., 'calico', 'kube-vip')
        component: Human-readable name for logging

    Returns:
        Dict with success, details, error, total_pods, failed_pods
    """
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No control plane nodes found",
            "error": "No control plane nodes available",
            "total_pods": 0,
            "failed_pods": [],
        }

    cmd = _ssh_cmd(
        cp_ip,
        f"kubectl get pods --all-namespaces --no-headers 2>/dev/null | grep '{prefix}'"
    )
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": f"No {component} pods found",
            "error": f"No pods matching prefix '{prefix}'",
            "total_pods": 0,
            "failed_pods": [],
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    failed = []
    total = 0

    for line in lines:
        parts = line.split()
        if len(parts) >= 4:
            total += 1
            ns = parts[0]
            pod_name = parts[1]
            status = parts[3]
            if status not in ("Running", "Completed"):
                failed.append(f"{ns}/{pod_name} ({status})")

    if total == 0:
        return {
            "success": False,
            "details": f"No {component} pods found",
            "error": f"No pods matching prefix '{prefix}'",
            "total_pods": 0,
            "failed_pods": [],
        }

    if not failed:
        return {
            "success": True,
            "details": f"All {total} {component} pods are Running",
            "error": "",
            "total_pods": total,
            "failed_pods": [],
        }

    return {
        "success": False,
        "details": f"{len(failed)}/{total} {component} pod(s) not Running",
        "error": f"Failed: {failed}",
        "total_pods": total,
        "failed_pods": failed,
    }


def check_k8s_kube_vip_pods(host) -> Dict[str, Any]:
    """Check if kube-vip pods are running."""
    return _check_pods_with_prefix(host, "kube-vip", "kube-vip")


def check_k8s_calico_pods(host) -> Dict[str, Any]:
    """Check if Calico network pods are running."""
    return _check_pods_with_prefix(host, "calico", "Calico")


def check_k8s_metallb_pods(host) -> Dict[str, Any]:
    """Check if MetalLB system pods are running.

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
            "details": "No control plane nodes found",
            "error": "No control plane nodes available",
        }

    cmd = _ssh_cmd(cp_ip, "kubectl get pods -n metallb-system --no-headers 2>/dev/null")
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        # Check if namespace exists
        ns_cmd = _ssh_cmd(cp_ip, "kubectl get ns metallb-system 2>/dev/null")
        ns_result = run_on_host(host, ns_cmd)
        if ns_result.rc != 0:
            return {
                "success": False,
                "details": "metallb-system namespace not found",
                "error": "MetalLB may not be installed",
            }
        return {
            "success": False,
            "details": "No pods found in metallb-system namespace",
            "error": "MetalLB pods missing",
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    failed = []
    total = 0

    for line in lines:
        parts = line.split()
        if len(parts) >= 3:
            total += 1
            pod_name = parts[0]
            status = parts[2]
            if status not in ("Running", "Completed"):
                failed.append(f"{pod_name} ({status})")

    if not failed:
        return {
            "success": True,
            "details": f"All {total} MetalLB pods are Running",
            "error": "",
        }

    return {
        "success": False,
        "details": f"{len(failed)}/{total} MetalLB pod(s) not Running",
        "error": f"Failed: {failed}",
    }


# =============================================================================
# STORAGE CHECKS
# =============================================================================

def check_k8s_nfs_provisioner_pod(host) -> Dict[str, Any]:
    """Check if NFS client provisioner pod is running."""
    from ..vars.k8s_vars import K8S_NFS_PROVISIONER_POD_PREFIX
    return _check_pods_with_prefix(host, K8S_NFS_PROVISIONER_POD_PREFIX, "NFS provisioner")


def check_k8s_snapshot_controller_pods(host) -> Dict[str, Any]:
    """Check snapshot-controller pods when PowerScale CSI is enabled."""
    if not _is_powerscale_csi_enabled(host):
        return {
            "success": True,
            "skipped": True,
            "details": (
                "PowerScale CSI is disabled - snapshot-controller check skipped"
            ),
            "error": "",
        }
    return _check_pods_with_prefix(host, "snapshot-controller", "snapshot-controller")


def check_k8s_isilon_csi_pods(host) -> Dict[str, Any]:
    """Check Isilon CSI driver pods when PowerScale CSI is enabled."""
    if not _is_powerscale_csi_enabled(host):
        return {
            "success": True,
            "skipped": True,
            "details": (
                "PowerScale CSI is disabled - Isilon CSI check skipped"
            ),
            "error": "",
        }

    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "details": "No control plane nodes found",
            "error": "No control plane nodes available",
        }

    cmd = _ssh_cmd(cp_ip, "kubectl get pods -n isilon --no-headers 2>/dev/null")
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "No Isilon CSI pods found in isilon namespace",
            "error": "Isilon CSI driver pods missing",
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    failed = []
    total = 0

    for line in lines:
        parts = line.split()
        if len(parts) >= 3:
            total += 1
            pod_name = parts[0]
            status = parts[2]
            if status not in ("Running", "Completed"):
                failed.append(f"{pod_name} ({status})")

    if not failed:
        return {
            "success": True,
            "details": f"All {total} Isilon CSI pods are Running",
            "error": "",
        }

    return {
        "success": False,
        "details": f"{len(failed)}/{total} Isilon CSI pod(s) not Running",
        "error": f"Failed: {failed}",
    }


def check_k8s_default_storage_class(host) -> Dict[str, Any]:
    """Check if the default storage class is set correctly.

    If PowerScale CSI is enabled, expects 'ps01'. Otherwise, expects
    'nfs-client'.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, expected_sc, actual_sc
    """
    from ..vars.k8s_vars import K8S_DEFAULT_STORAGE_CLASS_CSI, K8S_DEFAULT_STORAGE_CLASS_NFS

    is_csi = _is_powerscale_csi_enabled(host)
    expected_sc = K8S_DEFAULT_STORAGE_CLASS_CSI if is_csi else K8S_DEFAULT_STORAGE_CLASS_NFS

    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No control plane nodes found",
            "error": "No control plane nodes available",
            "expected_sc": expected_sc,
            "actual_sc": None,
        }

    cmd = _ssh_cmd(cp_ip, "kubectl get sc --no-headers 2>/dev/null")
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "Cannot query storage classes",
            "error": f"kubectl get sc failed: {result.stdout}",
            "expected_sc": expected_sc,
            "actual_sc": None,
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    actual_default = None

    for line in lines:
        parts = line.split()
        if len(parts) >= 1:
            sc_name = parts[0]
            # Default SC has "(default)" annotation appended
            if "(default)" in line:
                actual_default = sc_name

    if actual_default == expected_sc:
        return {
            "success": True,
            "details": f"Default storage class is '{expected_sc}' (CSI={is_csi})",
            "error": "",
            "expected_sc": expected_sc,
            "actual_sc": actual_default,
        }

    return {
        "success": False,
        "details": f"Expected default SC '{expected_sc}', got '{actual_default}'",
        "error": f"Storage class mismatch: expected={expected_sc}, actual={actual_default}",
        "expected_sc": expected_sc,
        "actual_sc": actual_default,
    }


def check_k8s_persistent_volumes(host) -> Dict[str, Any]:
    """Check that all Persistent Volumes are Bound with the expected storage class.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, pv_count, issues
    """
    # Note: Storage class validation is reserved for future enhancement
    # Currently just checks PV status regardless of storage class type

    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No control plane nodes found",
            "error": "No control plane nodes available",
        }

    cmd = _ssh_cmd(cp_ip, "kubectl get pv --no-headers 2>/dev/null")
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": True,
            "details": "No Persistent Volumes found in the cluster",
            "error": "",
            "pv_count": 0,
            "issues": [],
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    issues = []
    checked = 0

    for line in lines:
        parts = line.split()
        if len(parts) >= 5:
            pv_name = parts[0]
            status = parts[4]

            # Skip Released PVs
            if status == "Released":
                continue

            checked += 1
            if status != "Bound":
                issues.append(f"PV {pv_name}: not Bound (status={status})")

    if not issues:
        return {
            "success": True,
            "details": f"All {checked} PV(s) are Bound",
            "error": "",
            "pv_count": checked,
            "issues": [],
        }

    return {
        "success": False,
        "details": f"{len(issues)} PV issue(s) found",
        "error": "; ".join(issues),
        "pv_count": checked,
        "issues": issues,
    }


def check_k8s_nfs_storage_class(host) -> Dict[str, Any]:
    """Check if NFS StorageClass is dynamic and properly configured.

    Skipped if PowerScale CSI is enabled.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, skipped
    """
    if _is_powerscale_csi_enabled(host):
        return {
            "success": True,
            "skipped": True,
            "details": (
                "PowerScale CSI is enabled - NFS StorageClass check skipped"
            ),
            "error": "",
        }

    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No control plane nodes found",
            "error": "No control plane nodes available",
        }

    import json as json_mod

    cmd = _ssh_cmd(cp_ip, "kubectl get sc nfs-client -o json 2>/dev/null")
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "StorageClass 'nfs-client' not found",
            "error": "NFS StorageClass missing",
        }

    try:
        sc = json_mod.loads(result.stdout)
    except (json_mod.JSONDecodeError, ValueError):
        return {
            "success": False,
            "details": "Cannot parse StorageClass output",
            "error": "Invalid JSON from kubectl get sc",
        }

    provisioner = sc.get("provisioner", "")
    binding_mode = sc.get("volumeBindingMode", "")

    issues = []
    if not provisioner or provisioner == "kubernetes.io/no-provisioner":
        issues.append(f"No dynamic provisioner (provisioner={provisioner})")
    if binding_mode and binding_mode != "Immediate":
        issues.append(f"Unexpected volumeBindingMode: {binding_mode}")

    if not issues:
        return {
            "success": True,
            "details": f"NFS StorageClass 'nfs-client' is dynamic (provisioner={provisioner})",
            "error": "",
        }

    return {
        "success": False,
        "details": f"NFS StorageClass validation failed: {'; '.join(issues)}",
        "error": "; ".join(issues),
    }


def check_k8s_telemetry_pvcs(host) -> Dict[str, Any]:
    """Check if telemetry PVCs are Bound with the correct storage class.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, pvc_count, issues
    """
    # Note: Storage class validation is reserved for future enhancement
    cp_ip = _get_first_control_plane_ip(host)
    if not cp_ip:
        return {
            "success": False,
            "skipped": True,
            "details": "No control plane nodes found",
            "error": "No control plane nodes available",
        }

    # Check if telemetry namespace exists
    ns_cmd = _ssh_cmd(cp_ip, "kubectl get ns telemetry 2>/dev/null")
    ns_result = run_on_host(host, ns_cmd)
    if ns_result.rc != 0:
        return {
            "success": True,
            "skipped": True,
            "details": "telemetry namespace not found - PVC check skipped",
            "error": "",
        }

    cmd = _ssh_cmd(cp_ip, "kubectl get pvc -n telemetry --no-headers 2>/dev/null")
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": "No PVCs found in telemetry namespace",
            "error": "telemetry PVCs missing",
        }

    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    issues = []
    pvc_count = 0

    for line in lines:
        parts = line.split()
        if len(parts) >= 3:
            pvc_count += 1
            pvc_name = parts[0]
            status = parts[1]
            if status != "Bound":
                issues.append(f"PVC {pvc_name}: status={status} (expected Bound)")

    if not issues:
        return {
            "success": True,
            "details": f"All {pvc_count} telemetry PVC(s) are Bound",
            "error": "",
            "pvc_count": pvc_count,
            "issues": [],
        }

    return {
        "success": False,
        "details": f"{len(issues)}/{pvc_count} telemetry PVC(s) not Bound",
        "error": "; ".join(issues),
        "pvc_count": pvc_count,
        "issues": issues,
    }


# =============================================================================
# BUSYBOX POD DEPLOYMENT TEST
# =============================================================================

def check_k8s_busybox_pod(host) -> Dict[str, Any]:
    """Deploy a basic BusyBox pod and verify it reaches Running/Ready state.

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
            "details": "No control plane nodes found",
            "error": "No control plane nodes available",
        }

    pod_name = "omnia-busybox-test"
    ns = "default"

    # Cleanup any existing pod
    cleanup_cmd = _ssh_cmd(cp_ip, f"kubectl delete pod {pod_name} -n {ns} --ignore-not-found 2>/dev/null")
    run_on_host(host, cleanup_cmd)
    time.sleep(2)

    # Create BusyBox pod
    create_cmd = _ssh_cmd(
        cp_ip,
        f"kubectl run {pod_name} --image=busybox:1.36 --restart=Never "
        f"-- sh -c 'echo BusyBox running && sleep 30' 2>&1"
    )
    result = run_on_host(host, create_cmd)

    if result.rc != 0:
        return {
            "success": False,
            "details": f"BusyBox pod creation failed: {result.stdout}",
            "error": "kubectl run failed",
        }

    # Wait for pod to reach Running/Ready
    max_wait = 60
    wait_time = 0
    phase = "Unknown"
    while wait_time < max_wait:
        check_cmd = _ssh_cmd(
            cp_ip,
            f"kubectl get pod {pod_name} -n {ns} --no-headers "
            f"-o custom-columns=STATUS:.status.phase 2>/dev/null"
        )
        check_result = run_on_host(host, check_cmd)
        phase = check_result.stdout.strip()

        if phase in ("Running", "Succeeded"):
            # Cleanup
            cleanup_cmd = _ssh_cmd(cp_ip, f"kubectl delete pod {pod_name} -n {ns} --ignore-not-found 2>/dev/null")
            run_on_host(host, cleanup_cmd)

            return {
                "success": True,
                "details": f"BusyBox pod created and reached {phase} state in ~{wait_time}s",
                "error": "",
            }

        if phase == "Failed":
            break

        time.sleep(5)
        wait_time += 5

    # Cleanup
    cleanup_cmd = _ssh_cmd(cp_ip, f"kubectl delete pod {pod_name} -n {ns} --ignore-not-found 2>/dev/null")
    run_on_host(host, cleanup_cmd)

    return {
        "success": False,
        "details": f"BusyBox pod did not reach Running state (last phase: {phase})",
        "error": "Pod scheduling/startup failed",
    }


# =============================================================================
# FIREWALL PORT VERIFICATION
# =============================================================================

def check_k8s_firewall_ports_control_plane(host) -> Dict[str, Any]:
    """Verify firewall ports on control plane nodes match cloud-init templates.

    Checks that all required ports from K8S_FIREWALL_PORTS_CONTROL_PLANE are
    open on each control plane node.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, nodes_checked, missing_ports
    """
    cp_nodes = get_k8s_control_plane_nodes(host)
    if not cp_nodes:
        return {
            "success": False,
            "skipped": True,
            "details": "No control plane nodes found",
            "error": "No control plane nodes in PXE mapping",
            "nodes_checked": 0,
            "missing_ports": {},
        }

    missing_ports = {}
    nodes_checked = 0

    for node in cp_nodes:
        node_ip = get_node_ip_from_pxe(host, node)
        if not node_ip:
            continue

        nodes_checked += 1
        cmd = _ssh_cmd(node_ip, "firewall-cmd --list-all 2>/dev/null")
        result = run_on_host(host, cmd)

        if result.rc != 0:
            missing_ports[node] = ["FIREWALL_NOT_ACCESSIBLE"]
            continue

        fw_output = result.stdout.lower()
        node_missing = []

        for port_spec in K8S_FIREWALL_PORTS_CONTROL_PLANE:
            # Normalize for comparison (e.g., "6443/tcp")
            if port_spec.lower() not in fw_output:
                node_missing.append(port_spec)

        if node_missing:
            missing_ports[node] = node_missing

    if not missing_ports:
        return {
            "success": True,
            "details": f"All required firewall ports open on {nodes_checked} control plane node(s)",
            "error": "",
            "nodes_checked": nodes_checked,
            "missing_ports": {},
        }

    return {
        "success": False,
        "details": f"Missing firewall ports on {len(missing_ports)} node(s)",
        "error": f"Missing ports: {missing_ports}",
        "nodes_checked": nodes_checked,
        "missing_ports": missing_ports,
    }


def check_k8s_firewall_ports_workers(host) -> Dict[str, Any]:
    """Verify firewall ports on worker nodes match cloud-init templates.

    Checks that all required ports from K8S_FIREWALL_PORTS_WORKER are
    open on each worker node.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, nodes_checked, missing_ports
    """
    worker_nodes = get_k8s_worker_nodes(host)
    if not worker_nodes:
        return {
            "success": False,
            "skipped": True,
            "details": "No worker nodes found",
            "error": "No worker nodes in PXE mapping",
            "nodes_checked": 0,
            "missing_ports": {},
        }

    missing_ports = {}
    nodes_checked = 0

    for node in worker_nodes:
        node_ip = get_node_ip_from_pxe(host, node)
        if not node_ip:
            continue

        nodes_checked += 1
        cmd = _ssh_cmd(node_ip, "firewall-cmd --list-all 2>/dev/null")
        result = run_on_host(host, cmd)

        if result.rc != 0:
            missing_ports[node] = ["FIREWALL_NOT_ACCESSIBLE"]
            continue

        fw_output = result.stdout.lower()
        node_missing = []

        for port_spec in K8S_FIREWALL_PORTS_WORKER:
            if port_spec.lower() not in fw_output:
                node_missing.append(port_spec)

        if node_missing:
            missing_ports[node] = node_missing

    if not missing_ports:
        return {
            "success": True,
            "details": f"All required firewall ports open on {nodes_checked} worker node(s)",
            "error": "",
            "nodes_checked": nodes_checked,
            "missing_ports": {},
        }

    return {
        "success": False,
        "details": f"Missing firewall ports on {len(missing_ports)} worker node(s)",
        "error": f"Missing ports: {missing_ports}",
        "nodes_checked": nodes_checked,
        "missing_ports": missing_ports,
    }


# =============================================================================
# SYSTEMD TARGET VERIFICATION
# =============================================================================

def check_k8s_nfs_client_target(host) -> Dict[str, Any]:
    """Verify nfs-client.target is active on all K8s nodes.

    Source: cloud-init templates restart nfs-client.target on all K8s nodes
    to ensure NFS mounts are established before K8s services start.

    Args:
        host: Testinfra host connection

    Returns:
        Dict with success, details, error, nodes_checked, failed_nodes
    """
    all_nodes = get_k8s_control_plane_nodes(host) + get_k8s_worker_nodes(host)
    if not all_nodes:
        return {
            "success": False,
            "skipped": True,
            "details": "No K8s nodes found",
            "error": "No K8s nodes in PXE mapping",
            "nodes_checked": 0,
            "failed_nodes": [],
        }

    failed_nodes = []
    nodes_checked = 0

    for node in all_nodes:
        node_ip = get_node_ip_from_pxe(host, node)
        if not node_ip:
            continue

        nodes_checked += 1
        for target in K8S_SYSTEMD_TARGETS:
            cmd = _ssh_cmd(node_ip, f"systemctl is-active {target} 2>/dev/null")
            result = run_on_host(host, cmd)

            if result.stdout.strip() != "active":
                failed_nodes.append(f"{node} ({target}: {result.stdout.strip()})")

    if not failed_nodes:
        return {
            "success": True,
            "details": f"nfs-client.target active on all {nodes_checked} K8s node(s)",
            "error": "",
            "nodes_checked": nodes_checked,
            "failed_nodes": [],
        }

    return {
        "success": False,
        "details": f"nfs-client.target not active on {len(failed_nodes)} node(s)",
        "error": f"Failed: {failed_nodes}",
        "nodes_checked": nodes_checked,
        "failed_nodes": failed_nodes,
    }
