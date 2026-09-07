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
Orchestrator — Kubernetes-Specific Variables

Kubernetes-specific constants for test automation.
"""

from typing import Dict, List

# =============================================================================
# Kubernetes Functional Group Patterns
# =============================================================================
K8S_FG_PATTERN = "^service_kube_"
K8S_CONTROL_PLANE_FIRST = "service_kube_control_plane_first"
K8S_CONTROL_PLANE = "service_kube_control_plane"
K8S_NODE = "service_kube_node"

# =============================================================================
# Kubernetes Services (on provisioned nodes)
# =============================================================================
K8S_SERVICES: List[str] = [
    "kubelet",       # Kubernetes node agent
    "containerd",    # Container runtime
]

K8S_CONTROL_PLANE_SERVICES: List[str] = [
    "kubelet",
    "containerd",
]

# =============================================================================
# Kubernetes Directories
# =============================================================================
K8S_DIRECTORIES: List[str] = [
    "/etc/kubernetes",                 # Kubernetes configuration
    "/etc/kubernetes/manifests",       # Static pod manifests
    "/etc/kubernetes/pki",             # PKI certificates
    "/var/lib/kubelet",                # Kubelet data
]

K8S_NFS_CONFIG_DIR = "/opt/omnia/kubernetes"

# =============================================================================
# Kubernetes Configuration Files
# =============================================================================
K8S_CONFIG_FILES: List[str] = [
    "/etc/kubernetes/admin.conf",      # Admin kubeconfig
    "/etc/kubernetes/kubelet.conf",    # Kubelet kubeconfig
]

# =============================================================================
# Kubernetes System Pods (kube-system namespace)
# =============================================================================
K8S_SYSTEM_PODS: List[str] = [
    "kube-apiserver",
    "kube-controller-manager",
    "kube-scheduler",
    "kube-proxy",
    "etcd",
    "coredns",
]

# =============================================================================
# Kubernetes Playbook Paths
# =============================================================================
K8S_PROVISION_PLAYBOOK = "provision/provision_kubernetes.yml"
K8S_PROVISION_WORKDIR = "src/orchestrator/playbooks"

# =============================================================================
# Kubernetes Bolt-on Roles
# =============================================================================
K8S_BOLT_ON_ROLES: List[str] = [
    "mount_config",   # NFS mount configuration
    "k8s_config",     # K8s config files on NFS share
]

# =============================================================================
# Kubernetes Test Case IDs
# =============================================================================
TEST_CASES: Dict[str, dict] = {
    "k8s_enabled": {
        "id": "TC_K8_001",
        "title": "Verify Kubernetes is enabled in catalog",
    },
    "k8s_provision": {
        "id": "TC_K8_000",
        "title": "Deploy Kubernetes cluster provision",
    },
    "k8s_nodes_ready": {
        "id": "TC_K8_002",
        "title": "Verify Kubernetes nodes are in Ready state",
    },
    "k8s_control_plane_nodes": {
        "id": "TC_K8_003",
        "title": "Verify Kubernetes control plane nodes are Ready",
    },
    "k8s_worker_nodes": {
        "id": "TC_K8_004",
        "title": "Verify Kubernetes worker nodes are Ready",
    },
    "kubelet_running": {
        "id": "TC_K8_005",
        "title": "Verify kubelet service is running on all nodes",
    },
    "containerd_running": {
        "id": "TC_K8_006",
        "title": "Verify containerd service is running on all nodes",
    },
    "k8s_system_pods_running": {
        "id": "TC_K8_007",
        "title": "Verify kube-system pods are Running",
    },
    "k8s_apiserver_responding": {
        "id": "TC_K8_008",
        "title": "Verify Kubernetes API server is responding",
    },
    "k8s_directories_exist": {
        "id": "TC_K8_009",
        "title": "Verify Kubernetes directories exist on nodes",
    },
    "k8s_config_files_exist": {
        "id": "TC_K8_010",
        "title": "Verify Kubernetes configuration files exist",
    },
    "k8s_pki_certs_exist": {
        "id": "TC_K8_011",
        "title": "Verify Kubernetes PKI certificates exist",
    },
    "k8s_etcd_healthy": {
        "id": "TC_K8_012",
        "title": "Verify etcd cluster is healthy",
    },
    "k8s_coredns_running": {
        "id": "TC_K8_013",
        "title": "Verify CoreDNS pods are Running",
    },
    "k8s_kube_proxy_running": {
        "id": "TC_K8_014",
        "title": "Verify kube-proxy pods are Running",
    },
    "k8s_nfs_config_exists": {
        "id": "TC_K8_015",
        "title": "Verify K8s NFS configuration directory exists",
    },
    # SSH Tests
    "ssh_control_plane_to_worker": {
        "id": "TC_K8_016",
        "title": "Passwordless SSH from control plane to worker nodes",
    },
    "ssh_worker_to_control_plane": {
        "id": "TC_K8_017",
        "title": "Passwordless SSH from worker to control plane nodes",
    },
    "ssh_worker_to_worker": {
        "id": "TC_K8_018",
        "title": "Passwordless SSH between worker nodes",
    },
    # Pod Operations
    "k8s_pod_create": {
        "id": "TC_K8_019",
        "title": "Verify pod creation and scheduling works",
    },
    "k8s_pod_dns_resolution": {
        "id": "TC_K8_020",
        "title": "Verify DNS resolution works inside pods",
    },
    "k8s_service_create": {
        "id": "TC_K8_021",
        "title": "Verify Kubernetes service creation works",
    },
    # Node Roles
    "k8s_node_labels": {
        "id": "TC_K8_022",
        "title": "Verify node labels match functional group roles",
    },
    "k8s_node_taints": {
        "id": "TC_K8_023",
        "title": "Verify control plane nodes have correct taints",
    },
    # SMD/Metadata
    "k8s_smd_groups_registered": {
        "id": "TC_K8_024",
        "title": "Verify K8s functional groups registered in SMD",
    },
    "k8s_metadata_configured": {
        "id": "TC_K8_025",
        "title": "Verify K8s metadata-service configuration exists",
    },
    # LDAP Integration
    "k8s_ldap_integration": {
        "id": "TC_K8_026",
        "title": "Verify OpenLDAP integration with Kubernetes",
    },
    # Enhanced control plane checks
    "k8s_apiserver_pod": {
        "id": "TC_K8_027",
        "title": "Verify kube-apiserver static pod is running",
    },
    "k8s_controller_manager_pod": {
        "id": "TC_K8_028",
        "title": "Verify kube-controller-manager static pod is running",
    },
    "k8s_scheduler_pod": {
        "id": "TC_K8_029",
        "title": "Verify kube-scheduler static pod is running",
    },
    "k8s_cluster_info": {
        "id": "TC_K8_030",
        "title": "Verify kubectl cluster-info returns valid data",
    },
}
