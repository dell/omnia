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
# Source: cloud-init templates start crio.service + kubelet on all K8s nodes.
# chronyd runs on control plane for time synchronization.
K8S_SERVICES: List[str] = [
    "kubelet",       # Kubernetes node agent
    "crio",          # CRI-O container runtime (source: systemctl start crio.service)
]

K8S_CONTROL_PLANE_SERVICES: List[str] = [
    "kubelet",
    "crio",
    "chronyd",
]

# Systemd targets managed on K8s nodes
K8S_SYSTEMD_TARGETS: List[str] = [
    "nfs-client.target",   # NFS client mounts for K8s shared storage
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

# Source: storage_config.yml mounts[name=nfs_k8s].mount_point
K8S_NFS_CONFIG_DIR = "/opt/omnia/k8s_mount"

# =============================================================================
# Kubernetes HA Configuration (resolved at runtime via INPUT_PATH_TEMPLATE)
# =============================================================================
# Note: K8S_HA_CONFIG_FILE is NOT used directly; k8s_func.py resolves the path
# dynamically from load_test_config().project_name + INPUT_PATH_TEMPLATE.

# =============================================================================
# Kubernetes Firewall Ports (from cloud-init templates)
# =============================================================================
# Source: ms-group-service_kube_control_plane_first_x86_64.yaml.j2 (lines 393-434)
K8S_FIREWALL_PORTS_CONTROL_PLANE: List[str] = [
    "6443/tcp",           # Kubernetes API server
    "2379-2380/tcp",      # etcd client/peer
    "10250/tcp",          # Kubelet API
    "10251/tcp",          # kube-scheduler (deprecated)
    "10252/tcp",          # kube-controller-manager (deprecated)
    "10257/tcp",          # kube-controller-manager (secure)
    "10259/tcp",          # kube-scheduler (secure)
    "30000-32767/tcp",    # NodePort Services
    "179/tcp",            # BGP (Calico)
    "4789/udp",           # VXLAN
    "5473/tcp",           # Calico Typha
    "51820/udp",          # WireGuard IPv4
    "51821/udp",          # WireGuard IPv6
    "9100/tcp",           # Node Exporter
    "7472/tcp",           # MetalLB (memberlist TCP)
    "7472/udp",           # MetalLB (memberlist UDP)
    "7946/tcp",           # MetalLB (gossip TCP)
    "7946/udp",           # MetalLB (gossip UDP)
    "9090/tcp",           # Prometheus
    "8080/tcp",           # Generic HTTP
]

# Source: ms-group-service_kube_node_x86_64.yaml.j2 (lines 194-227)
K8S_FIREWALL_PORTS_WORKER: List[str] = [
    "10250/tcp",          # Kubelet API
    "30000-32767/tcp",    # NodePort Services
    "179/tcp",            # BGP (Calico)
    "4789/udp",           # VXLAN
    "5473/tcp",           # Calico Typha
    "51820/udp",          # WireGuard IPv4
    "51821/udp",          # WireGuard IPv6
    "9100/tcp",           # Node Exporter
    "7472/tcp",           # MetalLB (memberlist TCP)
    "7472/udp",           # MetalLB (memberlist UDP)
    "7946/tcp",           # MetalLB (gossip TCP)
    "7946/udp",           # MetalLB (gossip UDP)
    "9090/tcp",           # Prometheus
    "8080/tcp",           # Generic HTTP
]

# =============================================================================
# etcd Configuration
# =============================================================================
K8S_ETCD_NAMESPACE = "kube-system"
K8S_ETCD_PKI_CACERT = "/etc/kubernetes/pki/etcd/ca.crt"
K8S_ETCD_PKI_CERT = "/etc/kubernetes/pki/etcd/server.crt"
K8S_ETCD_PKI_KEY = "/etc/kubernetes/pki/etcd/server.key"

# =============================================================================
# NFS Provisioner Constants
# =============================================================================
K8S_NFS_PROVISIONER_POD_PREFIX = "nfs-client-nfs-subdir-external-provisioner"
K8S_DEFAULT_STORAGE_CLASS_CSI = "ps01"
K8S_DEFAULT_STORAGE_CLASS_NFS = "nfs-client"

# =============================================================================
# Container Runtime
# =============================================================================
K8S_EXPECTED_CONTAINER_RUNTIME = "cri-o"

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
        "title": "Verify container runtime (CRI-O) is running on all nodes",
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
    # CRI-O / Container Runtime Tests
    "k8s_crio_running": {
        "id": "TC_K8_031",
        "title": "Verify CRI-O service is running on all nodes",
    },
    "k8s_chronyd_running": {
        "id": "TC_K8_032",
        "title": "Verify chronyd service is active on control plane nodes",
    },
    "k8s_kubectl_version": {
        "id": "TC_K8_033",
        "title": "Verify kubectl version matches software config",
    },
    "k8s_kubeadm_crio_version_match": {
        "id": "TC_K8_034",
        "title": "Verify kubeadm version matches CRI-O version",
    },
    "k8s_container_runtime": {
        "id": "TC_K8_035",
        "title": "Verify all nodes use expected container runtime",
    },
    "k8s_component_status": {
        "id": "TC_K8_036",
        "title": "Verify K8s component status (controller, scheduler, etcd)",
    },
    # etcd Detailed Tests
    "k8s_etcd_health_detailed": {
        "id": "TC_K8_037",
        "title": "Verify etcd cluster endpoint health via etcdctl",
    },
    "k8s_etcd_member_list": {
        "id": "TC_K8_038",
        "title": "Verify etcd member list matches control plane count",
    },
    "k8s_etcd_leader_consistency": {
        "id": "TC_K8_039",
        "title": "Verify etcd leader identification and RAFT consistency",
    },
    # HA / VIP Tests
    "k8s_virtual_ip": {
        "id": "TC_K8_040",
        "title": "Verify VIP is configured on exactly one control plane",
    },
    # Network Pod Tests
    "k8s_kube_vip_pods": {
        "id": "TC_K8_041",
        "title": "Verify kube-vip pods are running",
    },
    "k8s_calico_pods": {
        "id": "TC_K8_042",
        "title": "Verify Calico network pods are running",
    },
    "k8s_metallb_pods": {
        "id": "TC_K8_043",
        "title": "Verify MetalLB system pods are running",
    },
    # Storage Tests
    "k8s_nfs_provisioner_pod": {
        "id": "TC_K8_044",
        "title": "Verify NFS client provisioner pod is running",
    },
    "k8s_snapshot_controller_pods": {
        "id": "TC_K8_045",
        "title": "Verify snapshot-controller pods are running",
    },
    "k8s_isilon_csi_pods": {
        "id": "TC_K8_046",
        "title": "Verify Isilon CSI driver pods are running",
    },
    "k8s_default_storage_class": {
        "id": "TC_K8_047",
        "title": "Verify default storage class is set correctly",
    },
    "k8s_persistent_volumes": {
        "id": "TC_K8_048",
        "title": "Verify Persistent Volumes are Bound with correct storage class",
    },
    "k8s_nfs_storage_class": {
        "id": "TC_K8_049",
        "title": "Verify NFS StorageClass is dynamic and properly configured",
    },
    "k8s_telemetry_pvcs": {
        "id": "TC_K8_050",
        "title": "Verify telemetry PVCs are Bound with correct PV and size",
    },
    # Workload Test
    "k8s_busybox_pod": {
        "id": "TC_K8_051",
        "title": "Deploy and verify basic BusyBox pod",
    },
    # Firewall Tests
    "k8s_firewall_ports_control_plane": {
        "id": "TC_K8_052",
        "title": "Verify firewall ports on control plane nodes match cloud-init",
    },
    "k8s_firewall_ports_workers": {
        "id": "TC_K8_053",
        "title": "Verify firewall ports on worker nodes match cloud-init",
    },
    # Systemd Target Tests
    "k8s_nfs_client_target": {
        "id": "TC_K8_054",
        "title": "Verify nfs-client.target is active on all K8s nodes",
    },
}
